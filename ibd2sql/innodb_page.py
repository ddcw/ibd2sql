import struct
import time
from .page_type import *

PAGE_SIZE = 16384
FIL_PAGE_DATA_END = 8
PAGE_NEW_INFIMUM = 99
PAGE_NEW_SUPREMUM = 112

#MAGIC_SIZE=3  KEY_LEN=32  SERVER_UUID_LEN=36
#(MAGIC_SIZE + sizeof(uint32) + (KEY_LEN * 2) + SERVER_UUID_LEN + sizeof(uint32))
INFO_SIZE = 3+4+32*2+36+4
INFO_MAX_SIZE = INFO_SIZE + 4
#SDI_OFFSET = 38+112+40*256 + INFO_MAX_SIZE
SDI_VERSION = 1

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

#storage/innobase/include/data0type.h
DATA_TRX_ID_LEN = 6
DATA_ROLL_PTR_LEN = 7

REC_N_FIELDS_ONE_BYTE_MAX = 0x7F

class decimal_buff(object):
	def __init__(self,bdata,forward=False):
		self.bdata = bdata
		self.max_size = len(bdata)
		self.forward = forward
		self.offset = 0
		self.count = 0
		
	def read(self,):
		#n = 0
		self.count += 1
		if self.max_size - self.offset >= 4:
			n = 4
		#elif self.max_size - self.offset >= 2:
		#	n = 2
		#elif self.max_size - self.offset > 0:
		#	n = 1
		else:
			n = self.max_size - self.offset
		if self.forward:
			data = self.bdata[self.offset:self.offset+n]
		else:
			if self.offset == 0:
				data = self.bdata[-self.offset-n:]
			else:
				data = self.bdata[-self.offset-n:-self.offset]
		self.offset += n
		return data,self.offset == self.max_size

def _DEBUG(*args):
	pass

class XDES(object):
	"""
     |---> XDES_ID         8  bytes
     |---> XDES_FLST_NODE  12 bytes
XDES-|
     |---> XDES_STATE      4  bytes
     |---> XDES_BITMAP     16 bytes
	"""
	def __init__(self,bdata):
		self.XDES_ID = struct.unpack('>Q',bdata[:8])[0]
		self.XDES_FLST_NODE = (FIL_ADDR(bdata[8:14]), FIL_ADDR(bdata[14:20]))
		self.XDES_STATE = struct.unpack('>L',bdata[20:24])[0]
		self.XDES_BITMAP = FLST_BASE_NODE(bdata[24:40])

	def __str__(self):
		return f"XDES_ID:{self.XDES_ID}  XDES_FLST_NODE:{self.XDES_FLST_NODE} XDES_STATE:{self.XDES_STATE} XDES_BITMAP:{self.XDES_BITMAP}"

class FIL_ADDR(object):
	"""
         |---> FIL_ADDR_PAGE     4 bytes
FIL_ADDR-|
         |---> FIL_ADDR_BYTE     2 bytes
	"""
	def __init__(self,bdata):
		self.FIL_ADDR_PAGE, self.FIL_ADDR_BYTE = struct.unpack('>LH',bdata[:6])

	def __str__(self):
		return f"FIL_ADDR_PAGE:{self.FIL_ADDR_PAGE} FIL_ADDR_BYTE:{self.FIL_ADDR_BYTE}"

class FLST_BASE_NODE(object):
	"""
               |---> FLST_LEN     4 bytes
FLST_BASE_NODE-|---> FLST_FIRST   6 bytes
               |---> FLST_LAST    6 bytes
	"""
	def __init__(self,bdata):
		self.FLST_LEN = struct.unpack('>L',bdata[:4])[0]
		self.FLST_FIRST = FIL_ADDR(bdata[4:10])
		self.FLST_LAST  = FIL_ADDR(bdata[10:16])

	def __str__(self,):
		return f"FLST_LEN:{self.FLST_LEN} FLST_FIRST:{self.FLST_FIRST} FLST_LAST:{self.FLST_LAST}"

class PAGE_BTR_SEG(object):
	"""
             |---> SAPCE_ID    4 bytes
PAGE_BTR_SEG-|---> PAGE_ID     4 bytes
             |---> PAGE_OFFSET 2 bytes

	"""
	def __init__(self,bdata):
		self.SAPCE_ID, self.PAGE_ID, self.PAGE_OFFSET = struct.unpack('>LLH',bdata[:10])

class page_header(object):
	"""
            |---> PAGE_N_DIR_SLOTS      2 bytes
            |---> PAGE_HEAP_TOP         2 bytes
            |---> PAGE_N_HEAP           2 bytes
            |---> PAGE_FREE             2 bytes
            |---> PAGE_GARBAGE          2 bytes
            |---> PAGE_LAST_INSERT      2 bytes
            |---> PAGE_DIRECTION        2 bytes
PAGE_HEADER-|---> PAGE_N_DIRECTION      2 bytes
            |---> PAGE_N_RECS           2 bytes
            |---> PAGE_MAX_TRX_ID       2 bytes
            |---> PAGE_LEVEL            2 bytes
            |---> PAGE_INDEX_ID         2 bytes
            |---> PAGE_BTR_SEG_LEAF     10 bytes
            |---> PAGE_BTR_SEG_TOP      10 bytes


	"""
	def __init__(self,bdata):
		self.PAGE_N_DIR_SLOTS, self.PAGE_HEAP_TOP, self.PAGE_N_HEAP, self.PAGE_FREE, self.PAGE_GARBAGE, self.PAGE_LAST_INSERT, self.PAGE_DIRECTION, self.PAGE_N_DIRECTION, self.PAGE_N_RECS, self.PAGE_MAX_TRX_ID, self.PAGE_LEVEL, self.PAGE_INDEX_ID = struct.unpack('>9HQHQ',bdata[:36])
		self.PAGE_BTR_SEG_LEAF = PAGE_BTR_SEG(bdata[36:46])
		self.PAGE_BTR_SEG_TOP = PAGE_BTR_SEG(bdata[46:56])


def page_directory(object):
	"""
	没必要遍历page directory, 因为是解析所有数据, 直接一行行访问就是....
	如果要根据where解析的话, 可以解析page.
	"""
	def __init__(self,bdata):
		pass

class page(object):
	"""
                                            |---> FIL_PAGE_SPACE_OR_CHECKSUM  4 bytes
                                            |---> FIL_PAGE_OFFSET             4 bytes
                                            |---> FIL_PAGE_PREV               4 bytes
                 |---> FIL_HEADER(38 bytes)-|---> FIL_PAGE_NEXT               4 bytes
                 |                          |---> FIL_PAGE_LSN                8 bytes
                 |                          |---> FIL_PAGE_TYPE               2 bytes
                 |                          |---> FIL_PAGE_FILE_FLUSH_LSN     8 bytes
                 |                          |---> FIL_PAGE_SPACE_ID           4 bytes
                 |
INNODB_PAGE(16K)-|---> PAGE_DATA   
                 |
                 |
                 |                          |---> CHECKSUM                    4 bytes
                 |---> FIL_TRAILER(8 bytes)-|
                                            |---> FIL_PAGE_LSN                4 bytes


	"""
	def __init__(self,*args,**kwargs):
		self.bdata = args[0]
		bdata = self.bdata
		self.DEBUG = kwargs['debug'] if 'debug' in kwargs else _DEBUG
		self.page_name = 'innodb page'
		self.FIL_PAGE_SPACE_OR_CHKSUM, self.FIL_PAGE_OFFSET, self.FIL_PAGE_PREV, self.FIL_PAGE_NEXT, self.FIL_PAGE_LSN, self.FIL_PAGE_TYPE, self.FIL_PAGE_FILE_FLUSH_LSN = struct.unpack('>4LQHQ',bdata[:34])
		self.FIL_PAGE_SPACE_ID = struct.unpack('>L',bdata[34:38])[0]
		self.CHECKSUM, self.FIL_PAGE_LSN = struct.unpack('>2L',bdata[-8::])
		self.offset = 38

		if self.FIL_PAGE_TYPE in (FIL_PAGE_INDEX,FIL_PAGE_SDI):
			self.page_header = page_header(self.read(56))
			self._offset = self.offset #读varsie的,

		#保存下一个字段的偏移量相对值
		self.next_offset = self.offset
		self._bdata = b'' #保存read的值, 方便调试

	def read_innodb_int(self,n,is_unsigned):
		"""
		读Innodb的 tinyint,smallint,mediumint,int,bigint, year, bit
		"""
		if is_unsigned:
			return self._read_uint(n)
		else:
			_t = self._read_uint(n)
			_s = n*8 - 1
			return (_t&((1<<_s)-1))-2**_s if _t < 2**_s and not is_unsigned else (_t&((1<<_s)-1))

	def read_innodb_float(self,n):
		"""
		读innodb的 float类型
		"""
		return struct.unpack('f',self.read(n))[0]

	def read_innodb_double(self,n):
		return struct.unpack('d',self.read(n))[0]

	def read_innodb_bit(self,n):
		bdata = self.read(n)
		return int.from_bytes(bdata,'big')
		#return struct.unpack()


	def read_innodb_decimal(self,n,extra):
		"""
整数部分和小数部分是分开的,
每部分 的每9位10进制数占4字节, 剩余的就按 1-2 为1字节, 这样算
Example:
    (5,2)  整数就是2字节,   小数是1字节
    (10,3) 整数就是4字节,  小数是2字节
		"""
		bdata = self.read(n)
		signed = False if int.from_bytes(bdata[:1],'big')&128 else True
		# issue 58  
		if signed:
			bdata = bytes((~b&0xff) for b in bdata)
		_signed = signed
		signed = False
		#print(bdata,extra)
		p1 = extra[0] #整数部分字节数
		p2 = extra[1] #小数部分
		#fh = True if struct.unpack('B',bdata[:1])[0]&127 else False
		cc = struct.pack('B',struct.unpack('B',bdata[:1])[0]&127)+bdata[1:p1]
		t1 = decimal_buff(cc)
		t1data = []
		lastbytes1=0
		while True:
			data,isend = t1.read()
			if data == b'':
				break
			lastbytes1 = len(data)
			_data = int.from_bytes(data,'big',signed=signed)
			_data += 1 if signed else 0
			t1data.append(_data)
		t2 = decimal_buff(bdata[p1:],True)
		t2data = []
		while True:
			data,isend = t2.read()
			if data == b'':
				break
			_data = int.from_bytes(data,'big',signed=signed)
			_data += 1 if signed else 0
			# 小数部分存在填充的判断(issue 44)
			if isend:
				if t2.count == 1:
					_data =  str(_data).zfill(extra[2][1])
				else:
					_data =  str(_data).zfill(extra[2][1]-9*t2.count)
			else:
				if _data < 0:
					_data = "-" + str(_data)[1:].zfill(9)
				else:
					_data =  str(_data).zfill(9)
				
			t2data.append(_data)
		t1data.reverse()
		if signed and len(t1data) > 1:
			t1data[0] = 128-t1data[0]
		elif signed and len(t1data) == 1:
			t1data[0] = (t1data[0] ^ (2**(8*lastbytes1-1)-1)) + 1
		rdata = "".join([ str(x).replace('-','') for x in t1data ]) + "." + "".join([ str(x).replace('-','') for x in t2data ])
		data = f"{'-' if _signed else ''}{rdata}"
		return data


		p1_bdata = bdata[:p1]
		p2_bdata = bdata[p1:]
		p1_data = int.from_bytes(p1_bdata,'big',signed=True)
		p2_data = int.from_bytes(p2_bdata,'big',signed=True)
		p1_n = (p1*8)-1
		p2_n = (p2*8)-1
		if p1_data < 0:
			p1_data = p1_data + (2**(8*p1-1))
		else:
			p1_data = p1_data - (2**(8*p1-1)) + 1
		if p2_data < 0:
			p2_data = -(p2_data + 1)
		return f"{p1_data}.{p2_data}"

	def read_innodb_set(self,):
		pass

	def read_innodb_enum(slef):
		pass

	def _read_innodb_varsize(self,maxsize=256):
		"""
		返回varchar等类型 记录大小 所需的空间(1-2bytes)
		2 bytes 直接表示64KB, 肯定不够(2**16 = 16384)
		所以, 第一字节小于等于 128 字节时, 就1字节.  否则就第一字节超过128字节的部分 *256 再加上第二字节部分来表示总大小 就是256*256 =  65536 这方法有点秀
		"""
		_size = self.readreverse(1)
		size = struct.unpack('>B',_size)[0]
		if maxsize <= 255:
			return size
		if size > REC_N_FIELDS_ONE_BYTE_MAX:
			size = struct.unpack('>B',self.readreverse(1))[0] + (size-128)*256
		return size
			

	def read_innodb_varchar(self,willdecode=True):
		"""
		所有变量
		"""
		size = self._read_innodb_varsize()
		self.debug("\tVAR FILED VAR SIZE:",size)
		bdata = self.read(size)
		rdata = ''
		if willdecode:
			try:
				rdata = bdata.decode().rstrip() #默认去掉结尾的空,美观
			except Exception as e:
				self.debug("ERORR:",e)
		else:
			rdata = bdata
		return rdata

	#https://dev.mysql.com/doc/refman/8.0/en/storage-requirements.html
	def read_innodb_datetime(self,n):
		"""
5 bytes + fractional seconds storage
1bit符号  year_month:17bit  day:5  hour:5  minute:6  second:6
---------------------------------------------------------------------
|             signed                 |          1  bit              |     
|--------------------------------------------------------------------
|         year and month             |          17 bit              |
|--------------------------------------------------------------------
|             day                    |          5  bit              |
|--------------------------------------------------------------------
|             hour                   |          5  bit              |
|--------------------------------------------------------------------
|            minute                  |          6  bit              |
|--------------------------------------------------------------------
|            second                  |          6  bit              |
---------------------------------------------------------------------
|      fractional seconds storage    |each 2 digits is stored 1 byte|
---------------------------------------------------------------------

		"""
		bdata = self.read(n)
		idata = int.from_bytes(bdata[:5],'big')
		year_month = ((idata & ((1 << 17) - 1) << 22) >> 22)
		year = int(year_month/13)
		month = int(year_month%13)
		day = ((idata & ((1 << 5) - 1) << 17) >> 17)
		hour = ((idata & ((1 << 5) - 1) << 12) >> 12)
		minute = ((idata & ((1 << 6) - 1) << 6) >> 6)
		second = (idata& ((1 << 6) - 1))
		great0 = True if idata&(1<<39) else False
		fraction = int.from_bytes(bdata[5:],'big') if len(bdata)>5 else None
		#就不转为datetime类型了(不会涉及到计算). 就字符串吧, 好看点
		#return f"{'' if great0 else '-'}{year}-{month}-{day} {hour}:{minute}:{second}{'' if fraction is None else '.'+str(fraction)}"
		if fraction is None:
			return f'{year}-{month}-{day} {hour}:{minute}:{second}' if great0 else f'-{year}-{month}-{day} {hour}:{minute}:{second}'
		else:
			return f'{year}-{month}-{day} {hour}:{minute}:{second}.{fraction}' if great0 else f'-{year}-{month}-{day} {hour}:{minute}:{second}.{fraction}'

	def read_innodb_time(self,n):
		"""
1bit符号  hour:11bit    minute:6bit  second:6bit  精度1-3bytes
-------------------------------------------------------------------
|            signed            |              1  bit              |
-------------------------------------------------------------------
|             hour             |              11 bit              |
-------------------------------------------------------------------
|            minute            |              6  bit              |
-------------------------------------------------------------------
|            second            |              6  bit              |
-------------------------------------------------------------------
|  fractional seconds storage  |  each 2 digits is stored 1 byte  |
-------------------------------------------------------------------
		"""
		bdata = self.read(n)
		idata = int.from_bytes(bdata[:3],'big')
		hour = ((idata & ((1 << 10) - 1) << 12) >> 12)
		minute = (idata & ((1 << 6) - 1) << 6) >> 6
		second = (idata& ((1 << 6) - 1))
		great0 = True if idata&(1<<23) else False
		fraction = int.from_bytes(bdata[3:],'big') if len(bdata)>3 else None
		if fraction is None:
			return f'{hour}:{minute}:{second}' if great0 else f'-{1024-hour}:{minute}:{second}'
		else:
			return f'{hour}:{minute}:{second}.{fraction}' if great0 else f'-{1024-hour}:{minute}:{second}.{fraction}'

	def read_innodb_date(self,n):
		"""
一共3字节 1bit符号,  14bit年  4bit月  5bit日
-----------------------------------
|     signed   |     1  bit       |
-----------------------------------
|      year    |     14 bit       |
-----------------------------------
|     month    |     4  bit       |
-----------------------------------
|      day     |     5  bit       |
-----------------------------------
		"""
		bdata = self.read(n)
		idata = int.from_bytes(bdata[:3],'big')
		year = ((idata & ((1 << 14) - 1) << 9) >> 9)
		month = (idata & ((1 << 4) - 1) << 5) >> 5
		day = (idata& ((1 << 5) - 1))
		great0 = True if idata&(1<<23) else False
		return f'{year}-{month}-{day}' if great0 else f'-{year}-{month}-{day}'

	def read_innodb_timestamp(self,n):
		"""
		4 bytes + fraction
		"""
		bdata = self.read(n)
		ltime = time.localtime(int.from_bytes(bdata[:4],'big'))
		fraction = int.from_bytes(bdata[4:],'big') if len(bdata)>4 else None
		return f'{ltime.tm_year}-{ltime.tm_mon}-{ltime.tm_mday} {ltime.tm_hour}:{ltime.tm_min}:{ltime.tm_sec}.{fraction if fraction is not None else ""}'
		if fraction is None:
			return f'{ltime.tm_year}-{ltime.tm_mon}-{ltime.tm_mday} {ltime.tm_hour}:{ltime.tm_min}:{ltime.tm_sec}'
		else:
			return f'{ltime.tm_year}-{ltime.tm_mon}-{ltime.tm_mday} {ltime.tm_hour}:{ltime.tm_min}:{ltime.tm_sec}.{fraction}'

	def read_innodb_big(self):
		"""
		读大字段
		"""
		return self.read(20)

	def read_innodb_json(self):
		pass


	def read(self,n):
		_tdata = self.bdata[self.offset:self.offset+n]
		self.offset += n
		self._bdata = _tdata
		return _tdata

	def readreverse(self,n): #往前读n字节
		_tdata = self.bdata[self._offset-n:self._offset]
		self._offset -= n
		return _tdata

	def readvar(self,):
		colsize = struct.unpack('>B',self.bdata[self._offset-1:self._offset])[0]
		if colsize < REC_N_FIELDS_ONE_BYTE_MAX:
			colsize = struct.unpack('<H',self.bdata[self._offset-2:self._offset])[0] - 2**15
			self._offset -= 1
		self._offset -= 1
		return self.read(colsize)
		

	def _read(self,n,signed):
		return int.from_bytes(self.read(n), byteorder='big', signed=signed)

	def _readreverse_int(self,n,signed):
		return int.from_bytes(self.readreverse(n), byteorder='big', signed=signed)

	def _readreverse_uint(self,n):
		return int.from_bytes(self.readreverse(n), byteorder='big')

	def _read_uint(self,n):
		return self._read(n,False)

	def _read_int(self,n):
		return self._read(n,True)

	def read_uint2(self):
		return self._read_uint(2)

	def read_int2(self):
		return self._read_int(2)

	def read_uint4(self):
		return self._read_uint(4)

	def read_int4(self):
		return self._read_int(4)

	def read_int8(self):
		return self._read_int(8)

	def read_uint8(self):
		return self._read_uint(8)

	def __str__(self):
		return f'page_name: {self.page_name}'

	def debug(self,*args):
		#self.DEBUG(args)
		#self.DEBUG("".join([ str(x) for x in args ]))
		self.DEBUG(" ".join([ str(x) for x in args ]))
