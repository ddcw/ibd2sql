#@ddcw
#解析innodb数据返回SQL的

import struct
import innodb_type

PAGE_SIZE = 16384
FIL_PAGE_DATA_END = 8
PAGE_NEW_SUPREMUM = 112
def page_directory(bdata):
	page_directorys = []
	for x in range(int(PAGE_SIZE/2)): #PAGE_N_DIR_SLOTS slot的数量,
		tdata = struct.unpack('>H',bdata[-(2+FIL_PAGE_DATA_END+x*2):-(FIL_PAGE_DATA_END+x*2)])[0]
		page_directorys.append(tdata)
		if tdata == PAGE_NEW_SUPREMUM:
			break
	return page_directorys



#storage/innobase/rem/rec.h
REC_INFO_MIN_REC_FLAG = 0x10
REC_INFO_DELETED_FLAG = 0x20
REC_N_OWNED_MASK = 0xF
REC_HEAP_NO_MASK = 0xFFF8
REC_NEXT_MASK = 0xFFFF
#REC_STATUS_ORDINARY 0
#REC_STATUS_NODE_PTR 1
#REC_STATUS_INFIMUM 2
#REC_STATUS_SUPREMUM 3
class record_header(object):
	def __init__(self,bdata):
		if len(bdata) != 5:
			#print(len(bdata))
			return None
		fb = struct.unpack('>B',bdata[:1])[0]
		self.deleted = True if fb&REC_INFO_DELETED_FLAG else False  #是否被删除
		self.min_rec = True if fb&REC_INFO_MIN_REC_FLAG else False #if and only if the record is the first user record on a non-leaf
		self.owned = fb&REC_N_OWNED_MASK # 大于0表示这个rec是这组的第一个, 就是地址被记录在page_directory里面
		self.heap_no = struct.unpack('>H',bdata[1:3])[0]&REC_HEAP_NO_MASK #heap number, 0 min, 1 max other:rec
		self.record_type = struct.unpack('>H',bdata[1:3])[0]&((1<<3)-1) #0:rec 1:no-leaf 2:min 3:max
		self.next_record = struct.unpack('>h',bdata[3:5])[0] #有符号....
	def __str__(self):
		return f'deleted:{self.deleted}  min_rec:{self.min_rec}  owned:{self.owned}  heap_no:{self.heap_no}  record_type:{self.record_type}  next_record:{self.next_record}'

def read_col(col,data_offset,var_offset,bdata):
	if col['isvar'] or col['dtype'] == 'char':
		#print(bdata[var_offset-1:var_offset],len(bdata[var_offset-1:var_offset]),len(bdata),var_offset)
		colsize = struct.unpack('>B',bdata[var_offset-1:var_offset])[0]
		#if col['dtype'] == 'varchar':
		#	print('varchar: ',colsize,bdata[var_offset-2:var_offset+1],col)
		if colsize > REC_N_FIELDS_ONE_BYTE_MAX:
		#if colsize > 255:
			colsize = struct.unpack('<H',bdata[var_offset-2:var_offset])[0] - 2**15
			#if col['dtype'] == 'varchar':
			#	print('varchar colsize: ',bdata[var_offset-2:var_offset])
			#print(bdata[var_offset-2:var_offset])
			#print('F2: colsize:',colsize)
			var_offset -= 1 #一字节不够,就两字节
		var_offset -= 1
		#print('var 1:',bdata[var_offset-1:var_offset])
	else:
		colsize = col['size']
	#if int.from_bytes(bdata[data_offset:data_offset+1],'little') > 0x7F and col['dtype'] == 'char':
	#	colsize *= col['charsize']
	new_data_offset = data_offset + colsize
	#print('bdata:',len(bdata[data_offset:data_offset+colsize]),bdata[data_offset:data_offset+50])
	return new_data_offset,var_offset,bdata[data_offset:data_offset+colsize]

def read_row(columns,key,bdata,offset):
	len_column = len(columns)
	tdata = [ None for x in range(len_column) ]
	null_bitmask_size = int((len_column+7)/8)
	null_bitmask = int.from_bytes(bdata[offset-5-null_bitmask_size:offset-5],'big')
	var_offset = offset - 5 - null_bitmask_size #可变长字段偏移量
	data_offset = offset
	var_offset += 1 if null_bitmask > 0 else 0
	#读索引数据
	for x in key:
		col = columns[x]
		data_offset,var_offset,coldata = read_col(col,data_offset,var_offset,bdata)
		tdata[x] = coldata
	if len(key) == 0:
		data_offset += 6
	data_offset += 6 + 7 #去掉TRX和UNDO
	#print('INDEX:',tdata,key)
	
	bitmaskvar = 0
	#读普通字段
	for x in range(len_column):
		col = columns[x]
		bitmaskvar += 1 if col['isvar'] else 0
		if tdata[x] is not None or null_bitmask&(1<<bitmaskvar): #暂时懒得去判断null_bitmask了...
			#print(columns[x],null_bitmask,x)
			#print('SKIP:',x)
			continue #这个字段是主键 或者为空就跳过
		data_offset,var_offset,coldata = read_col(col,data_offset,var_offset,bdata)
		tdata[x] = coldata
		#print('read_row:',x,len(coldata))
		#print('coldata:',len(tdata[x]))
	#print(tdata)
	#for x in range(len_column):
	#	print('OLD SIZE:',len(tdata[x]),len(tdata))
	return [ innodb_type.transdata(columns[x]['dtype'],tdata[x],columns[x]['is_unsigned'],columns[x]['extra']) if tdata[x] is not None else '' for x in range(len_column)] #数据类型转换
		

PAGE_NEW_INFIMUM = 99
REC_N_FIELDS_ONE_BYTE_MAX = 0x7F #超过(>)这个值, 就使用2字节 (就是第 1 bit位 标记是否使用2字节)
#得按照slot访问,  不然会丢数据(组的最后一个可能记录的next_record可能不准确,没来得及更新, optimize table 之后就是顺序的了,)
#按照slot访问, 数据会重复 加个页列表吧....
def index(bdata,pk,columns):
	"""
	bdata: index_page(完整的页)
	pk: 主键信息 [column_opx,column_opx,)] column_opx对应column的ordinal_position (不含rowid)
	columns: 字段信息, [{name:xx,column_type_utf8:xx},{name:xx}  ] #按照ordinal_position排好序的 (不含rowid,trx,undo)
	"""
	#print(columns,pk)

	next_offset = struct.unpack('>H',bdata[PAGE_NEW_INFIMUM-2:PAGE_NEW_INFIMUM])[0] + PAGE_NEW_INFIMUM
	data_list = []
	len_column = len(columns)

	directory_list = page_directory(bdata)
	#directory_list = []

	offset = 99
	offset += record_header(bdata[offset-5:offset]).next_record
	while offset != 112:
		header = record_header(bdata[offset-5:offset])
		data_list.append(read_row(columns,pk,bdata,offset))
		offset += header.next_record
	return data_list

def index_deleted(bdata,pk,columns):
	data_list = []
	page_free = struct.unpack('>H',bdata[38:38+56][6:8])[0]
	if page_free == 0:
		return data_list
	offset = page_free
	while offset != 112:
		header = record_header(bdata[offset-5:offset])
		if not header.deleted :
			break
		data_list.append(read_row(columns,pk,bdata,offset))
		if header.next_record == 0:
			break
		offset += header.next_record
	return data_list
		

#非叶子节点结构
#var filed length(1-2 per var) | null bitmask(主键没得,因为主键不能为空) | REC_HEADER(5) | KEY | child page number(4)
#返回index的第一个叶子节点的page no
def first_leaf(filename,columns,keylist,root=4,page_size=16384): 
	"""
	filename: ibd文件名
	columns: 列信息,可变长度, 长度
	keylist: 索引字段 比如[0,2] 表示第0,2个字段是联合索引
	root: root page位置, 4表示主键的root page
	"""
	pageno = root
	with open(filename,'rb') as f:
		next_pageno = root
		for i in range(10):
			f.seek(page_size*pageno,0)
			bdata = f.read(page_size)
			frec_offset = struct.unpack('>H',bdata[97:99])[0] + 99
			frec_header = record_header(bdata[frec_offset-5:frec_offset])
			#print(frec_header,frec_offset,struct.unpack('>H',bdata[97:99])[0])
			if frec_header.record_type == 0 or frec_header.record_type == 3: #找到了, 就是这一页
				break
			data_offset = frec_offset
			var_offset = frec_offset - 5 if root == 4 else frec_offset - 5 - int((len(columns)+7)/8)
			for x in keylist:
				col = columns[x]
				if col['isvar']:
					colsize = struct.unpack('>B',bdata[var_offset-1:var_offset])[0]
					#if colsize > REC_N_FIELDS_ONE_BYTE_MAX:
					if colsize > 255:
						colsize = struct.unpack('>B',bdata[var_offset-1:var_offset])[0]
						var_offset -= 1 
					var_offset -= 1
				else:
					colsize = col['size']
				#_data = bdata[data_offset:data_offset+colsize]
				data_offset += colsize
			#不用 +6 +7  因为是no_leaf 
			pageno = struct.unpack('>L',bdata[data_offset:data_offset+4])[0] #pageno 固定4byte
			#print(pageno,f.tell()/16384,data_offset)
	return pageno
