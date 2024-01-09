from ibd2sql.innodb_page import *
from ibd2sql.mysql_json import jsonob
import struct
import binascii
import json
#from ibd2sql.innodb_type import innodb_type_decode
FIL_PAGE_DATA_END = 8
PAGE_NEW_INFIMUM = 99
PAGE_NEW_SUPREMUM = 112
def page_directory(bdata):
	PAGE_SIZE = 16384
	page_directorys = []
	for x in range(int(PAGE_SIZE/2)): #PAGE_N_DIR_SLOTS slot的数量,
		tdata = struct.unpack('>H',bdata[-(2+FIL_PAGE_DATA_END+x*2):-(FIL_PAGE_DATA_END+x*2)])[0]
		page_directorys.append(tdata)
		if tdata == PAGE_NEW_SUPREMUM:
			break
	return page_directorys


class record_header(object):
	"""
--------------------------------------------------------------------------------------------------------
|          NO USE         |     (1 bit)     |    INSTANT FLAG                                          |
--------------------------------------------------------------------------------------------------------
|          NO USE         |     (1 bit)     |    没使用                                                |
--------------------------------------------------------------------------------------------------------
|          deleted        |     (1 bit)     |    表示是否被标记为删除                                  |
--------------------------------------------------------------------------------------------------------
|          min_rec        |     (1 bit)     |    最小字段(except leaf)                                 |
--------------------------------------------------------------------------------------------------------
|          owned          |     (4 bit)     |    slot第一个字段才有, 记录这个slot大小                  |
--------------------------------------------------------------------------------------------------------
|          heap number    |     (13 bit)    |    堆号(递增) 0:INFIMUM  max:SUPREMUM (不一定准..)       |
--------------------------------------------------------------------------------------------------------
|          record_type    |     (3 bit)     |    0:rec  1:no-leaf  2:min  3:max                        |
--------------------------------------------------------------------------------------------------------
|          next_record    |     (16 bit)    |    下一个字段的偏移量(距离当前offset)                    |
--------------------------------------------------------------------------------------------------------
	"""
	def __init__(self,bdata):
		if len(bdata) != 5:
			return None
		fb = struct.unpack('>B',bdata[:1])[0]
		#print(fb&(REC_INFO_DELETED_FLAG*2),fb&(REC_INFO_DELETED_FLAG*4))
		self.instant = True if fb&128 else False
		self.deleted = True if fb&REC_INFO_DELETED_FLAG else False  #是否被删除
		self.min_rec = True if fb&REC_INFO_MIN_REC_FLAG else False #if and only if the record is the first user record on a non-leaf
		self.owned = fb&REC_N_OWNED_MASK # 大于0表示这个rec是这组的第一个, 就是地址被记录在page_directory里面
		self.heap_no = struct.unpack('>H',bdata[1:3])[0]&REC_HEAP_NO_MASK #heap number, 0 min, 1 max other:rec
		self.record_type = struct.unpack('>H',bdata[1:3])[0]&((1<<3)-1) #0:rec 1:no-leaf 2:min 3:max
		self.next_record = struct.unpack('>h',bdata[3:5])[0] #有符号....

	def __str__(self):
		return f'deleted:{self.deleted}  min_rec:{self.min_rec}  owned:{self.owned}  heap_no:{self.heap_no}  record_type:{self.record_type}  next_record:{self.next_record}'


#@mysql storage/innobase/row/row0row.cc :: row_build_low
class ROW(page):
	"""
---------------------------------------------------------------------------
|                    variabels of length(1-2 byes)                        |
---------------------------------------------------------------------------
|                 null bitmask (1bit for per nullable filed)              |
---------------------------------------------------------------------------
|                 FILED COUNT WITH TRX&ROLLPTR (for INSTANT)              |
---------------------------------------------------------------------------
|                        record_header (5 bytes)                          |
---------------------------------------------------------------------------
|                           KEY/ROW_ID                                    |
---------------------------------------------------------------------------
|                  TRX_ID (6 bytes) (only for leaf page)                  |
---------------------------------------------------------------------------
|                  ROLL_PTR (7 bytes) (only for leaf page)                |
---------------------------------------------------------------------------
|                Non-KEY FILEDS( PK only for seconday key)                |
---------------------------------------------------------------------------
	"""
	def __init__(self,*args,**kwargs):
		super().__init__(*args,**kwargs)
		self.debug('INIT ROW BASE INFO')

		self.table = kwargs['table']  #必须要表对象, 不然解析不了字段信息
		self.idxno = kwargs['idx'] #索引信息 索引号 self.table.index[idx]

		#基础信息
		self.row = []  #数据
		self.rowno = 0 #行数
		self.pageno = 0        #page no 没啥用...
		self.haveindex = False #没得索引
		self.page_type = "INDEX PAGE" 
		self.HAVE_LEAF_PAGE = False #是否有叶子页
		self.HAVE_NONE_LEAF_PAGE = False #是否有非叶子页
		self.SET = True #默认将set/enum换成对应的值
		self.next_record = PAGE_NEW_INFIMUM #下一个字段的位置

		#过滤条件
		self.maxtrx = 2**(6*8)
		self.mintrx = 0
		self.maxrollptr = 2**(7*8)
		self.minrollptr = 0
		self.DELETED = False #True 只要delete的数据, False只要非delete的数据 (鱼与熊掌不可兼得)

		self.null_bitmask_count = self.table.null_bitmask_count
		self.null_bitmask_len = int((self.null_bitmask_count+7)/8) if self.table.have_null else 0
		self.debug(f"NULL BITMASK LENGTH: {self.null_bitmask_len} bytes. (nullable col count:{self.null_bitmask_count})")

		#有哪些字段, 仅ordinal_position
		self.column_list = [ x for x in self.table.column ]
		self.key_column_list = [] #
		self.prekey = {} #索引字段是否为前缀索引
		if self.idxno: #如果有索引
			self.haveindex = True
			for x in self.table.index[self.idxno]['element_col']:
				self.prekey[x[0]] = True if x[1] == 0 else False
			#self.key_column_list = [ x[0] for x in self.table.index[self.idxno]['element_col'] ]
			
		self.debug("######################################## FIELD INFO START ####################################") 
		for x in self.table.column:
			self.debug('name:',self.table.column[x]['name'], ' type:',self.table.column[x]['type'], ' size:',self.table.column[x]['size'],'  isvar:',self.table.column[x]['isvar'], '  is_nullable:',self.table.column[x]['is_nullable'])
		self.debug("######################################## FIELD INFO END ######################################") 
		self.debug(f"CLUSTER INDEX: IDXNO: {self.idxno}  IDX COLUMMN COUNT:{len(self.table.index[self.idxno]['element_col'])}  INDEX ELEMENT:{[x[0] for x in self.table.index[self.idxno]['element_col']]}" if self.haveindex else "没得索引")
		self.debug(f"ROW INIT FINISH FOR < {self.table.get_name()} >\n")


	def init(self,bdata):
		self.bdata = bdata

	def _read_key(self,):
		pass

	def _read_null_bitmask(self,):
		pass


	def _read_field(self,col):
		data = None
		n = col['size']
		extra = col['extra']
		is_unsigned = col['is_unsigned']
		_expage = None
		_bf_offset = self.offset
		if col['isbig']:
			#data = self.read_innodb_big()
			size = self._read_innodb_varsize()
			if size + self.offset > 16384:
				size = 20 #超过这一页大小了, 就只要20bytes
				data = self.read(size)
				real_size = int.from_bytes(data[-4:],'big')
				self.debug("THIS BIG COLUMN SIZE:",real_size,'bytes  detail:',data)
				_expage = data
				data = None
				
			elif col['ct'] == "json": #json类型
				_tdata = self.read(size)
				#data = _tdata
				data = jsonob(_tdata[1:],int.from_bytes(_tdata[:1],'little')).init()
				data = json.dumps(data)
			else: #其它lob类型
				data = self.read(size).decode()
		elif col['isvar']: #变量
			data = self.read_innodb_varchar(True)
		elif col['ct'] in ['int','tinyint','smallint','bigint','mediumint']: #int类型
			data = self.read_innodb_int(n,is_unsigned)
		elif col['ct'] == 'float': 
			data = self.read_innodb_float(n)
		elif col['ct'] == 'double': 
			data = self.read_innodb_double(n)
		elif col['ct'] == 'decimal': 
			data = self.read_innodb_decimal(n,extra)
		elif col['ct'] == 'set': #set
			data = self._read_uint(n)
			if self.SET:
				_sn = 0
				_sdata = ''
				for x in col['elements_dict']:
					if 1<<_sn & data:
						_sdata += col['elements_dict'][x] + ","
					_sn += 1
				data = _sdata[:-1]
				data = repr(data)
		elif col['ct'] in ['enum','set']: #枚举类型
			data = self._read_uint(n)
			if self.SET:
				#data = col['elements_dict'][data]
				data = repr(col['elements_dict'][data])
		elif col['ct'] == 'time':
			data = self.read_innodb_time(n)
		elif col['ct'] == 'datetime':
			data = self.read_innodb_datetime(n)
		elif col['ct'] == 'date':
			data = self.read_innodb_date(n)
		elif col['ct'] == 'timestamp':
			data = self.read_innodb_timestamp(n)
		elif col['ct'] == 'year':
			data = self._read_uint(n) + 1900
		elif col['ct'] == 'bit':
			data = self._read_uint(n)
		elif col['ct'] == 'binary':
			data = self._read_uint(n)#.decode()
		elif col['ct'] == 'tinytext':
			s = int.from_bytes(self.readreverse(1),'big')
			data = self.read(s).decode()
		else:
			self.debug("WARNING Unknown col:",col)
			data = self.read(n)

		_af_offset = self.offset
		self.debug(f"\t{_bf_offset} ----> {_af_offset} data:{data}  bdata:{self._bdata}")
		#self._crc32 += binascii.crc32(self._bdata,self._crc32)
		return data,_expage

	def read_row(self):
		self.debug(f"################## READ ROW START (PAGE NO:{self.pageno}) ########################")
		self.debug(f"READ ALL ROWS FROM PAGE (PAGE_ID={self.pageno})")
		self.debug(f"RESET offset TO PAGE_NEW_INFIMUM ({PAGE_NEW_INFIMUM})")
		if self.DELETED:
			self.next_offset = self.page_header.PAGE_FREE
			self.debug(f"ONLY READ WITH DELETED FLAG")
		else:
			self.next_offset = PAGE_NEW_INFIMUM
		#print(self.next_offset,self.bdata[38:38+56][6:8],self.page_header)
		self.offset = PAGE_NEW_INFIMUM #懒得解析page directory了. 直接走PAGE_NEW_INFIMUM
		self._read_all_row()
		for x in self.row:
			yield x
		self.debug(f"################## READ ROW END (PAGE NO:{self.pageno})   #########################")
		#return None

	def _read_all_row(self):
		#先清空环境
		self.row = []  #数据
		self.rowno = 0 #行数
		row = []       #数据行
		#[{'type':xx,'trx':xx,'rollptr':xx,'have_extra':True,'extra_page':[xxx],'row':[0,66,'哈哈']]},  ]
		rn = 0 #统计数据行数
		rhn = 0
		self.next_record = 1
		#含instant的字段的数量 instant column count
		_icc  = sum([ 1 if self.table.column[x]['instant'] else 0 for x in self.table.column ])
		while self.next_offset != 112 and self.next_offset < 16384 and self.next_offset > 0 and self.next_record != 0:
			self._offset = self.offset = self.next_offset
			_row = {} #这一行数据,有额外信息
			_data = {} #具体的字段值
			_expage = {} #额外页.
			_row['trx'] = None
			_row['rollptr'] = None
			col_count = len(self.table.column)

			#读字段头 record header
			rhn += 1
			self.debug(f"NO:{rhn} READ RECORD HEADER (5 bytes) _offset:{self._offset} offset:{self.offset} START")
			rheader = record_header(self.readreverse(5))
			if rheader.record_type == 2: #最小字段
				self.next_offset += rheader.next_record
				self.debug(f"\tTHIS ROW IS PAGE_NEW_INFIMUM, WILL CONTINUE. (offset:{self.offset})")
				continue
			elif rheader.record_type == 3: #最大字段
				self.debug(f"PAGE NO {self.pageno} READ FINISH.(offset:{self.offset})")
				break
			elif rheader.record_type == 1:  #non leaf
				self.next_offset += rheader.next_record
				self.HAVE_NONE_LEAF_PAGE = True
				continue
			elif rheader.record_type == 0: #leaf 
				self.HAVE_LEAF_PAGE = True
			self.next_offset += rheader.next_record #设置下一个字段的offset
			self.next_record = rheader.next_record
			_row['type'] = rheader.record_type

			#DELETE判断:
			if self.DELETED and not rheader.deleted:
				continue

			self.debug(f"\tREAD RECORD HEADER (5 bytes) _offset:{self._offset} offset:{self.offset} FINISH")
				
			self.debug(f'\tPAGE NO     : {self.pageno}')
			self.debug(f"\tREAD ROW NO : {rn}   CURRENT_OFFSET:{self.offset}")
			self.debug(f"\tREC INSTANT : {rheader.instant}")
			self.debug(f"\tREC DELETED : {rheader.deleted}")
			self.debug(f"\tREC MIN_REC : {rheader.min_rec}")
			self.debug(f"\tREC OWNED   : {rheader.owned}")
			self.debug(f"\tREC HEAP_NO : {rheader.heap_no}")
			self.debug(f"\tREC TYPE    : {rheader.record_type}")
			self.debug(f"\tREC NEXT    : {rheader.next_record}")
			self.debug(f"\t20 bytes ON BOTH SIDES OF RECORD, {self.bdata[self._offset-20:self._offset]}, {self.bdata[self._offset:self._offset+20]}")


			#INSTANT
			self.debug("GET COUNT COLUMN FOR THIS ROW")
			if self.table.instant and rheader.instant:
				self.debug(f"\tREAD INSTANT SIZE, _OFFSET:{self._offset}  OFFSET:{self.offset} START.")
				col_count = self._read_innodb_varsize()
				self.debug(f"\tREAD INSTANT SIZE, _OFFSET:{self._offset}  OFFSET:{self.offset} FINISH")
			else:
				self.debug(f"\tREAD COLUM COUNT")
				col_count = len(self.table.column)
				self.debug(f"\tREAD COLUM COUNT FINISH")
			self.debug(f"\tTHIS ROW HAS {col_count} FILEDS")


			#NULL
			null_bitmask = 0
			null_bitmask_count = 0
			null_bitmask_len = 0 #null bitmask 的占用的字节数量
			#if self.null_bitmask_len > 0:
			self.debug(f"READ NULL BITMASK")
			if self.table.have_null and rheader.instant:
				null_bitmask_count = self.table.null_bitmask_count+self.table.null_bitmask_count_instant
				#null_bitmask_len = int((self.table.null_bitmask_count+self.table.null_bitmask_count_instant+7)/8)
			elif self.table.have_null:
				null_bitmask_count = self.table.null_bitmask_count
				#self.debug("READ NULL BISTMASK",self.table.null_bitmask_count,self.table.null_bitmask_count_instant,rheader.instant)
				#nbl = self.table.null_bitmask_count if self.table.null_bitmask_count_instant == 0 and not rheader.instant else self.table.null_bitmask_count_instant + self.table.null_bitmask_count
				#null_bitmask = self._readreverse_uint(int((nbl+7)/8))
				#self.debug(f'NULL BITMASK: {null_bitmask}  NULLABLE FILED COUNT: {self.null_bitmask_len}')
			elif rheader.instant:
				null_bitmask_count = self.table.null_bitmask_count_instant
			else:
				self.debug("\tNO NULLABLE FIELD.")
			null_bitmask_len = int((null_bitmask_count+7)/8)
			null_bitmask = self._readreverse_uint(null_bitmask_len)
			self.debug(f"\tNULLABLE FILED COUNT: {self.table.null_bitmask_count}  NULLABLE FIELD COUNT(FOR INSTANT):{self.table.null_bitmask_count_instant}")
			_idnb = [ 1 if null_bitmask&(1<<x) else 0 for x in range(8*null_bitmask_len) ]
			_idnb.reverse()
			self.debug(f'\tNULL BITMASK: COUNT:{null_bitmask_count}  ID:',null_bitmask,_idnb)
			#self.debug(f"NULL_COUNT:{self.table.null_bitmask_count}  NULL_COUNT_INSTANT:{self.table.null_bitmask_count_instant}  ")


			#读索引
			self.debug("READ KEY FILED")
			if self.haveindex: #有索引的时候
				for colno,prefix_key in self.table.index[self.idxno]['element_col']:
					col = self.table.column[colno]
					self.debug(f"\tREAD KEY COLNO:{colno} NAME:{col['name']}")

					#pk 不需要判断null
					if prefix_key == 0:
						_data[colno],_expage[colno] = self._read_field(col)
						col_count -= 1
						self.debug(f"\tREAD KEY NO:{colno} NAME:{col['name']} FINISH. VALUES: {_data[colno]}")
					else:
						_,__ = self._read_field(col)
						self.debug(f'前缀索引数据为: {_} . SKIP IT.' )

			else: 
				self.debug("\tNO CLUSTER KEY.WILL READ 6 bytes(ROWID)",)
				_row_id = self._read_uint(6) #ROW_ID
				self.debug(f"\t ROW_ID:{_row_id}")

			#读事务信息
			self.debug("READ TRX(6) AND ROLLPTR(7) INFO")
			_row['trx'] = self._read_uint(6)
			col_count -= 1
			_row['rollptr'] = self._read_uint(7)
			col_count -= 1
			self.debug(f"\tTRX: {_row['trx']}  ROLLPTR: {_row['rollptr']}")


			#读剩余字段
			self.debug(f"READ THE REST OF FIELD. (column count: {col_count})")
			_nc = -1 #可为空的字段的计数
			for colno in self.table.column:
				col = self.table.column[colno]
				self.debug("\tREAD FIELD COLNO:",colno,"NAME:",col['name'],"TYPE:",col['type'],'CT:',col['ct'])
				#if colno in _data or (rheader.instant  and col['instant']):
				if colno in _data:
					self.debug("\tIS KEY, WILL CONTINUE")
					continue

				col_count -= 1
				if not rheader.instant and col['instant']:
					self.debug("\t IS INSTANT AND DEFAULT VALUE")
					_data[colno] = col['default'] if not col['instant_null'] else None
					continue

				if col['instant']:
					self.debug("\t IS INSTANT, READ BUT FINALLY")
					continue


				if col['is_nullable']:
					_nc += 1
					self.debug(f"\tCOL {colno} {col['name']} MAYBE NULL. USE NULL_BITMASK")
					if null_bitmask&(1<<_nc):
						_data[colno] = None #NULL
						self.debug(f"\t\tCOL {colno} {col['name']} IS NULL, WILL CONTINE")
						continue
					else:
						self.debug(f"\t\tCOL {colno} {col['name']} IS NOT NULL.")
						_data[colno],_expage[colno] = self._read_field(col)
				else:
					self.debug(f"\tCOL {colno} {col['name']} REQUIRE NOT NULL. READ DATA")
					_data[colno],_expage[colno] = self._read_field(col)

			#匹配条件
			self.debug(f'FILTER TRX and ROLLPTR')
			if _row['trx'] and ( _row['trx'] <= self.mintrx or _row['trx'] >= self.maxtrx ):
				self.debug(f"!!! SKIP ROW NO {rn} .  {_row['trx']} not in ({self.mintrx},{self.maxtrx})")
				continue
			if _row['rollptr'] and (_row['rollptr'] <= self.minrollptr or _row['rollptr'] >= self.maxrollptr):
				self.debug(f"!!! SKIP ROW NO {rn} .  {_row['rollptr']} not in ({self.minrollptr},{self.maxrollptr})")
				continue
			self.debug(f"TRX:{_row['rollptr']} and ROLLPTR:{_row['rollptr']} is PASS")

			#读剩下的字段(FOR INSTANT)
			for colno in self.table.column:
				col = self.table.column[colno]
				if colno in _data or (not col['instant']):
					continue
				self.debug(f'READ THE REST OF FILED (INSTANT) (column count:{col_count})')
				col_count -= 1

				if col_count + _icc  < 1 and not self.haveindex: #记录的字段取完了, 剩余的就是默认值
					self.debug(f"\t NO MORE RECORD FILED, COL({colno})({col['name']}) WILL USE DEFAULT VALUE.{col['default']}")
					#_data[colno],_expage[colno] = None if col['instant_null']  else col['default'],None
					_data[colno],_expage[colno] = col['instant_value'],None
					self.debug(col)
					continue

				if not rheader.instant:
					_data[colno],_expage[colno] = col['default'],None
					self.debug(f"\tINSTANT:{rheader.instant}",col['instant_value'])
					continue
				else:
					self.debug(f"\tINSTANT:{rheader.instant}",col['instant_value'])
					#break
					
				if col['is_nullable']:
					_nc += 1
					self.debug(f"\tINSTANT COL {colno} {col['name']} MAYBE NULL.")
					if null_bitmask&(1<<_nc):
						self.debug(f"\tINSTANT COL {colno} {col['name']} IS NULL. WILL CONTINE")
						_data[colno],_expage[colno] = None,None
						#_data[colno],_expage[colno] = col['default'],None
						continue
					else:
						self.debug(f"\tINSTANT COL {colno} {col['name']} IS NOT NULL. READ DATA")
						#_data[colno],_expage[colno] = col['default'],None
						_data[colno],_expage[colno] = self._read_field(col)
				else:
					self.debug(f"\tINSTANT COL {colno} {col['name']} REQUIRE NOT NULL. READ DATA")
					_data[colno],_expage[colno] = self._read_field(col)




			rn += 1
			_row['row'] = _data
			_row['expage'] = _expage
			row.append(_row)
			#self.debug("############################# AFTER READ INSTANT CRC32 ",self._crc32)
			self.debug(f'READ ROW NO: {rn}  FINISH.  CURRENT_OFFSET: {self.offset}\t')
			#self.debug('XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',self.offset)
		self.row = row
		self.debug(f'################### THIS PAGE({self.pageno}) HAVE {rn} ROWS. ###################\n')

class index(ROW):
	"""
------------------------------------------------
|            FIL_HEADER(38 bytes)              |
------------------------------------------------
|            PAGE_HEADER(56 bytes)             |
------------------------------------------------
|            ROW(INFIMUM)(5+7+1)               |
------------------------------------------------
|            ROW(SUPERMUM)(5+8+1)              |
------------------------------------------------
|            ROW(var+bitmask+5+k+d)            |
------------------------------------------------
|              ............                    |
------------------------------------------------
|            ROW(var+bitmask+5+k+d)            |
------------------------------------------------
|            PAGE_DIRECTORY(n*2)               |
------------------------------------------------
|              FIL_TRAILER(8)                  |
------------------------------------------------
	"""
	def __init__(self,*args,**kwargs):
		super().__init__(*args,**kwargs)
		self.table = kwargs['table']  #必须要表对象, 不然解析不了字段信息
		#self.HAS_NULL = self.table.have_null #是否有空值
		#self.offset += 5 #懒得解析page directory了. 直接走INFIMUM..
		#self._offset = self.offset
		#rheader = record_header(self.readreverse(5))
		#self.offset += rheader.next_record #第一行先去掉



class find_leafpage(ROW):
	def __init__(self,*args,**kwargs):
		super().__init__(*args,**kwargs)
		self.table = kwargs['table']
		idx = kwargs['idx'] #索引信息 索引号 self.table.index[idx]
		self.IS_LEAF_PAGE = False

		self.offset += 5 #INFIMUM..
		#self.debug('<START FIND LEAF PAGE>')

	def find(self):
		IS_LEAF_PAGE = False
		NEXT_PAGE_ID = 0
		self.next_offset = PAGE_NEW_INFIMUM 
		self.debug("CURRENT PAGE ID(find leaf page):",self.pageno)
		while self.next_offset != 112 and self.next_offset < 16384 and self.next_offset > 0:
			self._offset = self.offset = self.next_offset
			rheader = record_header(self.readreverse(5))
			self.next_offset += rheader.next_record
			self.debug(f"FIND LEAF PAGE ---->  OFFSET:{self.offset}  RECORD TYPE:{rheader.record_type}")
			if rheader.record_type == 2: #最小字段
				continue
			elif rheader.record_type == 3: #最大字段
				break
			elif rheader.record_type == 1:  #non leaf
				#解析得到page_id
				if self.null_bitmask_len > 0:
					null_bitmask = self._readreverse_uint(self.null_bitmask_len)
				if self.haveindex:
					for colno,prefix_key in self.table.index[self.idxno]['element_col']:
						col = self.table.column[colno]
						_,__ = self._read_field(col)
				else:
					self._read_uint(6) #ROW_ID
				#cluster index Non-leaf page dont have trx and rollptr
				#_ = self._read_uint(6) 
				#_ = self._read_uint(7)
				NEXT_PAGE_ID = self._read_uint(4)
				break
			elif rheader.record_type == 0:
				IS_LEAF_PAGE = True
				break
		return IS_LEAF_PAGE,NEXT_PAGE_ID
			

	def init(self):
		while self.offset != 112:
			self._offset = self.offset
			self.debug('offset',self.offset)
			rheader = record_header(self.readreverse(5))
			self.offset += rheader.next_record
			if rheader.record_type == 0:
				self.IS_LEAF_PAGE = True
				break
			elif rheader.record_type == 3:
				break
		self.debug("CURRENT TYPE:",rheader.record_type)

