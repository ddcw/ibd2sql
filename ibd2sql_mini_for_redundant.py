#!/usr/bin/env python
# write by ddcw @https://github.com/ddcw
# 解析row format=REDUNDANT的脚本, 先试试, 后面2.0的时候再合并.
# 本脚本可以单独使用, 对于sdi之类的都单独解析, 所以不再拼接DDL了. 也不支持compress,加密之类的,页不支持溢出页,json,decimal之类的. 就一个Mini脚本,要啥自行车..
# 功能: 解析8.0中的ibd文件(ROW_FORMAT=REDUNDANT)
# 用法:
#  python3  ibd2sql_mini_for_redundant.py  /PATH/xxxx.ibd

# 本脚本采用强制解析, 即每页都直接解析, 不做校验, 只要是PAGE_LEVEL=0的通通解析

import sys
import os
import struct
import json
import zlib
import base64
import time

try:
	HAVE_IBD2SQL = True # 部分数据懒得解析了, 直接沿用ibd2sql去实现. 不行的话,就取为null
	from ibd2sql.blob import first_blob
	from ibd2sql.mysql_json import jsonob
	from ibd2sql.innodb_page import page
	from ibd2sql.innodb_page_index import char_decode
	from ibd2sql.COLLATIONS import COLLID_TO_CHAR
	from ibd2sql.innodb_type import innodb_type_isvar
	class MINI_PAGE(page):
		def __init__(self,bdata):
			super(MINI_PAGE,self).__init__(bdata)
			self.decimal_data = b''
		def read(self,n):
			return self.decimal_data
except:
	HAVE_IBD2SQL = False

ARGV = sys.argv
def USAGE():
	print(f"\nUSAGE:\n\tpython3 {ARGV[0]} /PATH/xxxx.ibd")

WITH_COLNAME = False # 带上字段名
class IBDREADER(object):
	def __init__(self,filename):
		self.filename = filename
		self.f = open(self.filename,'rb')
		self.PAGE_SIZE = 16384
		self.current_page = 0
	def read(self,n=0):
		if n > 0:
			self.current_page = n
		self.f.seek(self.PAGE_SIZE*self.current_page,0)
		data = self.f.read(self.PAGE_SIZE)
		self.current_page += 1
		return data
	def close(self,):
		self.f.close()

def BDATA2INTBD(bdata,):
	n = len(bdata)
	sn = ">"+str(n)+"B"
	tdata = struct.unpack(sn,bdata)
	rdata = 0
	for x in range(n):
		rdata += tdata[x]<<((n-x-1)*8)
	return rdata
	

def TOINT4(bdata,unsigned):
	data = BDATA2INTBD(bdata)
	rdata = 0
	if unsigned:
		rdata = data
	else:
		if data&(2**(len(bdata)*8-1)):
			rdata = data&(2**(len(bdata)*8-1)-1)
		else:
			rdata = -((2**(len(bdata)*8-1))-data) if data > 0 else  data
	return rdata

def INNODB_TIMESPLIT(data,n,rule1):
	# data是int数字,  n是多少bit位, rule1是时间
	# rule1 : [[0,1], [1,11], [12,18] [start,count]   ]
	rdata1 = []
	for start,count in rule1:
		t = ( data & ((2**(n-start)-1)-(2**(n-start-count)-1)) )>>(n-start-count)
		rdata1.append(t)
	return rdata1

class ROWREAD(object):
	def __init__(self,bdata):
		self.bdata = bdata
		self.offset = 101
		self._offset = 101
		self._last_offset = 0

	def read(self,n):
		data = self.bdata[self.offset:self.offset+n]
		self.offset += n
		return data

	def readreverse(self,n):
		data = self.bdata[self._offset-n:self._offset]
		self._offset -= n
		return data

	def read_record_header(self,):
		bdata = self.readreverse(6)
		bb = struct.unpack('>6B',bdata)
		return {
			"instant_flag": True if bb[0]&128 else False,
			"row_version_flag": True if bb[0]&64 else False,
			"deleted": True if bb[0]&32 else False,
			"min_rec": True if bb[0]&16 else False,
			"owned": bb[0]&15,
			"heap_no": 0,
			"n_fields": (((bb[2]<<8)+bb[3])&(2**11-1))>>1,
			"byte1_flag": True if bb[3]&1 else False,
			"next_record":  (bb[4]<<8) + bb[5],
		}

	def read_trx_rollptr(self,):
		trx = self.read(6)
		rollptr = self.read(7)
		return {'trx':trx,'rollptr':rollptr}

	def read_filed(self,colid,dd,rh,f):
		datasize,isnull = self.read_nullandsize(rh)
		extradata = b''
		if datasize > 16384 and HAVE_IBD2SQL:
			bdata = self.read(768)
			SPACE_ID,PAGENO,BLOB_HEADER,REAL_SIZE = struct.unpack('>3LQ',self.read(20))
			extradata = first_blob(f,PAGENO)
		elif datasize > 16384:
			bdata = self.read(768)
		else:
			bdata = self.read(datasize)
		bdata += extradata
		rdata = None
		col = dd['columns'][colid]
		if isnull:
			return rdata
		else:
			if col['type'] in [2,3,4,9,10]: # int
				rdata = TOINT4(bdata,col['is_unsigned'])
			elif col['type'] == 5: # float
				rdata = struct.unpack('f',bdata)[0]
			elif col['type'] == 6: # double
				rdata = struct.unpack('d',bdata)[0]
			elif col['type'] == 14: # year
				rdata = BDATA2INTBD(bdata)+1900
			elif col['type'] == 22: # enum
				rdata = col['elements_dict'][BDATA2INTBD(bdata)]
				rdata = repr(rdata)
			elif col['type'] == 23: # set # 可以包含多个
				_tdata = BDATA2INTBD(bdata)
				_sn = 0
				_sdata = ''
				for x in col['elements_dict']:
					if 1<<_sn & _tdata:
						 _sdata += col['elements_dict'][x] + ","
					_sn += 1
				rdata = repr(_sdata[:-1])
			elif col['type'] == 31: # json
				if HAVE_IBD2SQL and extradata == b'':
					_tdata = jsonob(bdata[1:],struct.unpack('<B',bdata[:1])[0]).init()
					rdata = repr(json.dumps(_tdata))
				else:
					rdata = None
				
			elif col['type'] == 15: # date
				signed,year,month,day = INNODB_TIMESPLIT(
					BDATA2INTBD(bdata[:3]),
					24,
					[[0,1], [1,14], [15,4], [19,5]])
				jingdu = BDATA2INTBD(bdata[3:]) if datasize > 3 else ''
				rdata = f"{'-' if signed == 0 else ''}{year}-{str(month).zfill(2)}-{str(day).zfill(2)}{'.'+str(jingdu) if datasize > 3 else ''}"
				rdata = repr(rdata)
			elif col['type'] == 18: # timestamp
				rdata = repr(time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(BDATA2INTBD(bdata))))
			elif col['type'] == 19: # datetime
				signed,year_month,day,hour,minute,second = INNODB_TIMESPLIT(
					BDATA2INTBD(bdata[:5]),
					40,
					[[0,1], [1,17], [18,5], [23,5], [28,6], [34,6]]
					)
				jingdu = BDATA2INTBD(bdata[5:]) if datasize > 5 else ''
				year = int(year_month/13)
				month = int(year_month%13)
				rdata = f"{'-' if signed == 0 else ''}{year}-{str(month).zfill(2)}-{str(day).zfill(2)} {str(hour).zfill(2)}:{str(minute).zfill(2)}:{str(second).zfill(2)}{'.'+str(jingdu) if datasize > 5 else ''}"
				rdata = repr(rdata)
			elif col['type'] == 20: # time
				signed,hour,minute,second = INNODB_TIMESPLIT(
					BDATA2INTBD(bdata[:3]),
					24,
					[[0,1], [1,11], [12,6], [18,6]]
				)
				jingdu = BDATA2INTBD(bdata[3:]) if datasize > 3 else ''
				rdata = f"{'-' if signed == 0 else ''}{str(hour).zfill(2)}:{str(minute).zfill(2)}:{str(second).zfill(2)}{'.'+str(jingdu) if datasize > 3 else ''}"
				rdata = repr(rdata)
			elif col['type'] == 21: # decimal #TODO
				if HAVE_IBD2SQL:
					aa = MINI_PAGE(b'\x00'*16384)
					aa.decimal_data = bdata
					rdata = aa.read_innodb_decimal(len(bdata),col['extra'])
				else:
					rdata = None
			elif col['type'] == 29 and col['column_type_utf8'].startswith('binary'): # binary
				rdata = hex(BDATA2INTBD(bdata))
			elif col['type'] == 16 and col['column_type_utf8'].startswith('varbinary'): # varbinary
				rdata = hex(BDATA2INTBD(bdata))
			elif col['type'] in [29,16]: # varchar,char
				if HAVE_IBD2SQL:
					#rdata = repr(char_decode(bdata,col).rstrip())
					rdata = repr(char_decode(bdata,col))
				else:
					try:
						#rdata = repr((bdata).decode().rstrip())
						rdata = repr((bdata).decode())
					except:
						rdata = '0x'+(bdata).hex()
			else:
				rdata = '0x'+bdata.hex()
		return rdata

	def read_nullandsize(self,rh):
		nmask = 128 if rh['byte1_flag'] else 32768
		data = 1
		if rh['byte1_flag']:
			data = struct.unpack('>B',self.readreverse(1))[0]
		else:
			data = struct.unpack('>H',self.readreverse(2))[0]
		isnull = True if nmask&data else False
		value = data&(nmask-1) if isnull else data
		_t = value
		value = value - self._last_offset
		#print('SIZE',value,'NULLABLE:',isnull)
		self._last_offset = _t
		return value,isnull

def ROW2SQL(row,columns,tablename):
	sql = f"INSERT INTO {tablename}"
	colname = ""
	value = ""
	for col in columns:
		if col['name'] in ['DB_ROLL_PTR','DB_TRX_ID','DB_ROW_ID']:
			continue
		colname = f"{colname}{col['name']},"
		value = f"{value}{row[col['name']] if row[col['name']] is not None else 'null'},"
	colname = "("+colname[:-1]+")"
	print(f"{sql}{colname[:-1] if WITH_COLNAME else ''} values({value[:-1]});")

if __name__ == "__main__":
	if len(ARGV) not in [2,3]:
		USAGE()
	for x in ARGV[1:]:
		if str(x).upper().find('-H') >= 0:
			USAGE()

	for filename in ARGV[1:]:
		if not os.path.exists(filename):
			print(f"{filename}不存在!")
			USAGE()
	filename = ARGV[1]
	# 开整
	f = IBDREADER(filename)
	if len(ARGV) == 3: # 分区表和5.7的情况
		_f = IBDREADER(ARGV[2])
		fsp_bdata = _f.read()
	else:
		fsp_bdata = f.read()
	if fsp_bdata[24:26] != b'\x00\x08': 
		print(f"这文件{filename}不是ibd文件!")
		sys.exit(2)
	SDI_PAGE_NO = struct.unpack('>I',fsp_bdata[38+112+40*256+115:][4:8])[0]
	if fsp_bdata[10390:10390+115] != b'\x00'*115:
		print(f"这文件{filename}加密了, 暂不支持")
	if len(ARGV) == 3:
		bdata = _f.read(SDI_PAGE_NO)
	else:
		bdata = f.read(SDI_PAGE_NO) # 暂不支持general tablespace
	offset = struct.unpack('>h',bdata[97:99])[0]+99 +12 +6 +7 
	dunzip_len,dzip_len = struct.unpack('>LL',bdata[offset:offset+8])
	unzbdata = zlib.decompress(bdata[offset+8:offset+8+dzip_len])
	dic_info = json.loads(unzbdata.decode())
	dd = dic_info['dd_object']
	if dd['row_format'] != 4:
		print('只支持redundant格式')
		sys.exit(4)
	_n = -1
	for col in dd['columns']:
		_n += 1
		if col['type'] in [22,23]: # enum,set
			_xx = {}
			for i in col['elements']:
				_xx[i['index']] = base64.b64decode(i['name']).decode()
			dd['columns'][_n]['elements_dict'] = _xx
		if HAVE_IBD2SQL:
			dd['columns'][_n]['character_set'] = COLLID_TO_CHAR[col['collation_id']][0]
			ct,isvar,size,isbig,elements_dict,varsize,extra = innodb_type_isvar(col)
			dd['columns'][_n]['extra'] = extra
	TABLE_NAME = dd['name']
	f.current_page = 2
	ROWID = True if dd['indexes'][0]['elements'][0]['length'] == 4294967295 else False
	PRIMARRY_KEY = []
	for x in dd['indexes'][0]['elements']:
		if x['length'] == 4294967295:
			continue
		MAX_LEN = len(base64.b64decode(dd['columns'][x['ordinal_position']]['default_value']))
		isprefix = True if MAX_LEN > x['length'] else False
		PRIMARRY_KEY.append([x['ordinal_position'],isprefix])
	# 获取主键的INDEXID, inode的第一个page就是,但太麻烦了, 所以我们从PK ROOT PAGE获取. 但是对于5.7的话,就可能得人工指定了.
	rootpagebdata = f.read(int(dict([ x.split('=') for x in  dd['indexes'][0]['se_private_data'].split(';')[:-1] ])['root']))
	if len(ARGV) == 3:
		rootpagebdata = f.read(int( struct.unpack('>L',f.read(2)[50:50+192][64:68])[0] )) # 还是解析inode吧...
	INDEXID = struct.unpack('>L',rootpagebdata[70:74])[0]
	INDEXID = struct.pack('>L',INDEXID) # 转为二进制,方便比较, 上面是为了获取.
	for _pageno in range(int(os.stat(filename).st_size/16384)-2):
		bdata = f.read(_pageno)
		if bdata[24:26] != b'E\xbf' or bdata[64:66] != b'\x00\x00' or bdata[70:74] != INDEXID:
			continue # b'E\xbf': 17855,idxpage   b'\x00\x00' page_level:0叶子节点
		rr = ROWREAD(bdata)
		isfirst = True
		while True:
			rh = rr.read_record_header()
			if rh['next_record'] == 0:
				break
			if isfirst:
				rr.offset = rh['next_record']
				rr._offset = rh['next_record']
				isfirst = False
				continue
			row = {}
			for k,isprefix in PRIMARRY_KEY:
				_tdata = rr.read_filed(k,dd,rh,f.f)
				if not isprefix:
					row[dd['columns'][k]['name']] = _tdata
			if len(PRIMARRY_KEY) == 0:
				rr.read_nullandsize(rh) # rowid
				rowid = rr.read(6)
			rr.read_nullandsize(rh) # trx
			rr.read_nullandsize(rh) # rollptr
			trxrollptr = rr.read_trx_rollptr()
			_idx = -1
			for col in dd['columns']:
				_idx += 1
				if col['name'] in row or (col['name'] in ['DB_ROW_ID','DB_TRX_ID','DB_ROLL_PTR']):
					continue
				try:
					row[col['name']] = rr.read_filed(_idx,dd,rh,f.f)
				except Exception as e:
					print(e,f.current_page,rr.offset,row,rh) # 大概率是坏块或者索引不匹配的问题
					sys.exit(2)
			rr.offset = rh['next_record']
			rr._offset = rh['next_record']
			rr._last_offset = 0
			ROW2SQL(row,dd['columns'],TABLE_NAME)
		#break # 先1页试试水
	f.close()
