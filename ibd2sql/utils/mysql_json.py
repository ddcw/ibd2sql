#@mysql sql/json_binary.h
import struct
import sys
import base64
#from .b2data import B2DECIMAL,map_decimal
# 没考虑到json也会使用decimal, 会导致循环引用, 所以就把decimal搬过来了,虽然代码重复了. 但懒得新开文件导入了.
def map_decimal(n):
	return [ [4,9] for _ in range(n//9) ] + ([[ ((n%9)+1)//2 if n%9 < 7 else 4,n%9 ]] if n%9 > 0 else [])

def _READ_DECIMAL(data,p,offset):
	rdata = ""
	for psize,pzfill in p:
		tdata = int.from_bytes(data[offset:offset+psize],'big',signed=False)
		rdata += str(tdata).zfill(pzfill)
		offset += psize
	return rdata,offset

def B2DECIMAL(data,p1,p2):
	p1_data = ""
	signed = False if struct.unpack('>B',data[:1])[0] & 128 else True
	if signed:
		data = bytes((~b&0xff) for b in data)
	data = struct.pack('>B',data[0]-128)+data[1:]
	offset = 0
	p1_data,offset = _READ_DECIMAL(data,p1,offset)
	p2_data,offset = _READ_DECIMAL(data,p2,offset)
	p1_data = str(0 if p1_data == '' else int(p1_data))
	return f"{'-' if signed else ''}{p1_data}.{p2_data}"

_ = """
                                                               - -----------------
                                                              | JSON OBJECT/ARRAY |
                                                               - -----------------
                                                                      |
 -------------------------------------------------------------------------
| TYPE | ELEMENT_COUNT | KEY-ENTRY(if object) | VALUE-ENTRY | KEY | VALUE |
 -------------------------------------------------------------------------
                               |                    |          |
                               |                    |     --------------
                   --------------------------       |    | UTF8MB4 DATA |
                  | KEY-OFFSET |  KEY-LENGTH |      |     --------------
                   --------------------------       |
                                                    |
                                         --------------------------------
                                         | TYPE | OFFSET/VALUE(if small) |
                                         --------------------------------

small 2 bytes   large 4 bytes
---------------------------------------------------
TYPE          1 byte
COUNT         2/4 bytes
SIZE          2/4 bytes
VALUE         VALUE/OBJECT/ARRAY
---------------------------------------------------

---------------------------------------------------
OBJECT VALUE = KEY_ENTRY + VALUE_ENTRY + KEY + VALUE  #KEY肯定是字符串, 所以不需要记录数据类型
ARRAY  VALUE = VALUE_ENTRY + VALUE #不需要KEY

KEY_ENTRY   = KEY_OFFSET(2/4bytes) + KEY_LNGTH(2 bytes)
VALUE_ENTRY = TYPE(1byte) + OFFSET(2/4 bytes)/VALUE  (如果类型是int,literal之类的,就直接是值了, 否则就走OFFSET)
---------------------------------------------------

"""

#  type ::=
#      0x00 |       // small JSON object
#      0x01 |       // large JSON object
#      0x02 |       // small JSON array
#      0x03 |       // large JSON array
#      0x04 |       // literal (true/false/null)
#      0x05 |       // int16
#      0x06 |       // uint16
#      0x07 |       // int32
#      0x08 |       // uint32
#      0x09 |       // int64
#      0x0a |       // uint64
#      0x0b |       // double
#      0x0c |       // utf8mb4 string
#      0x0f         // custom data (any MySQL data type)


#  value ::=
#      object  |
#      array   |
#      literal |
#      number  |
#      string  |
#      custom-data

class jsonob(object):
	def __init__(self,bdata,t):
		"""
		bdata = json data
		t 类型 json类型
		"""
		self.bdata = bdata
		self.t = t
		self.offset = 0
		self.ssize = 2 if self.t == 0x00 or self.t == 0x02 else 4
		self._type = None
		self._bdata = b''
		#print("BEGIN JSON TO B, CURRENT TYPE:",self.t)

	def read_key_entry(self):
		"""
		read key-entry
		"""
		#print("READ KEY ENTRY")
		key_entry = []
		for x in range(self.element_count):
			key_offset = self.read_little()
			key_length = self.read_little(2)
			key_entry.append((key_offset,key_length))
		self.key_entry = key_entry

	def read_value_entry(self):
		#print("READ VALUE ENTRY")
		value_entry = []
		for x in range(self.element_count):
			t = self.read_little(1)
			#print("\t entry: type:",t)
			data = None
			if t < 0x04:
				#print("READ VALUE ENTRY JSON object/array")
				data  = self.read_little()
			elif t == 0x04: #literal
				#print("READ VALUE ENTRY literal")
				_data = self.read_little(2) # literal固定为2
				if _data == 1:
					data = True
				elif _data == 2:
					data = False
				elif _data == 0:
					data = None
				else:
					data = ''
				if self.ssize > 2: # 与ssize无关..., skip padding
					self.read(self.ssize-2)
			elif t >= 0x05 and t <= 0x06: #inline data
				#print("READ VALUE ENTRY Inline data for INT",t,0x05,0x0a)
				data = self.read_inline_data(t)
				if self.ssize > 2:
					self.read(self.ssize-2)
			elif (t == 0x07 or t == 0x08) and self.ssize > 2:
				data = self.read_inline_data(t)
			else:
				data = self.read_little()
			#elif t == 0x0b: #double
				#print("READ VALUE ENTRY Double")
				#data = struct.unpack('d',self.read(8))[0]
			#	data = self.read_little()
			#elif t == 0x0c or t == 0x09 or t == 0x0a: #string
				#print("READ DATA ENTRY STRING",self.offset)
			#	data = self.read_little() #OFFSET
			value_entry.append((t,data))
		self.value_entry = value_entry
		#print("VALUE ENTRY LIST ---------",self.value_entry)

	def read_key(self):
		#print("READ KEY")
		key = []
		for x in self.key_entry:
			key.append(self.bdata[x[0]:x[0]+x[1]].decode()  )
		self.key = key

	def read_value(self):
		#print("READ VALUE")
		value = []
		for x in self.value_entry:
			#print("VALUE TYPE:xxxxxxx",x[0])
			if x[0] == 0x0c: #字符串
				_s,size = self.read_var(x[1])
				#size = int.from_bytes(self.bdata[x[1]:x[1]+1],'little') #先都按1字节计算
				value.append(self.bdata[x[1]+_s:x[1]+_s+size].decode()) 
			elif x[0] == 0x0b:
				value.append(struct.unpack('<d',self.bdata[x[1]:x[1]+8])[0])
			elif x[0] == 0x07: # int32
				if self.ssize == 2:
					value.append(int.from_bytes(self.bdata[x[1]:x[1]+4],'little',signed=True))
				else:
					value.append(x[1])
			elif x[0] == 0x08: # uint32
				if self.ssize == 2:
					value.append(int.from_bytes(self.bdata[x[1]:x[1]+4],'little',signed=False))
				else:
					value.append(x[1])
			elif x[0] == 0x09: # int64
				value.append(int.from_bytes(self.bdata[x[1]:x[1]+8],'little',signed=True))
			elif x[0] == 0x0a: # uint64
				value.append(int.from_bytes(self.bdata[x[1]:x[1]+8],'little',signed=False))
			elif x[0] <= 0x03: #json对象, 又递归
				#s = self.ssize
				s = 4 if x[0] == 0x01 or x[0] == 0x03 else 2 # 由类型决定大小
				size = int.from_bytes(self.bdata[x[1]+s: x[1]+s+s ], 'little')
				data = self.bdata[x[1]:x[1]+size]
				_aa = jsonob(data,x[0])
				value.append(_aa.init())
			elif x[0] == 0x0f: # opaque
				value.append(self._decode_opaque(x[1]))
			else:
				value.append(x[1])
		self.value = value
				
	def read_var(self,offset):
		"""
		读mysql的varchar的 记录长度的大小, 范围字节数量和大小
		如果第一bit是1 就表示要使用2字节表示,如果第二字节的第1bit为1,则使用3字节,依次类推:
			后面1字节表示 使用有多少个128字节, 然后加上前面1字节(除了第一bit)的数据(0-127) 就是最终数据
-----------------------------------------------------
| 1 bit flag | 7 bit data | if flag, 8 bit data*128 |
-----------------------------------------------------
		"""
		level = 1
		real_size = 0
		while level < 100:
			current_data = struct.unpack('<B',self.bdata[offset:offset+level][-1:])[0]
			if current_data & 128:
				real_size += (current_data-128)*(128**(level-1))
				level += 1
			else:
				real_size += current_data*(128**(level-1))
				break
		return level,real_size

	def read_scalar(self,):
		if self.t == 0x04: # literal
			return {0:None, 1:True, 2:False}.get(self.bdata[0])
		elif self.t <= 0x0a: # (u)int16-64
			n = {0x05:2, 0x06:2, 0x07:4, 0x08:4, 0x09:8,0x0a:8}[self.t]
			signed = self.t in (0x05,0x07,0x09)
			return int.from_bytes(self.bdata[:n],'little',signed=signed)
		elif self.t == 0x0b: # double
			return struct.unpack('<d',self.bdata[:8])[0]
		elif self.t == 0x0c: # string
			_s,size = self.read_var(0)
			return self.bdata[_s:_s+size].decode('utf-8')
		elif self.t == 0x0f: # custom data (JSONB_TYPE_OPAQUE): mysql: decimal,date,time,datetime
			return self._decode_opaque(0)
		return None

	def _decode_opaque(self,pos):
		field_type = self.bdata[pos]
		pos += 1
		_s,size = self.read_var(pos)
		data = self.bdata[pos+_s:pos+_s+size]
		#print('type:',field_type,'data:',data)
		rdata = None
		# 我们这里是吧decimal当作字符串的,所以会被json.dumps加上引号... 使用float,double会有精度问题, 使用Decimal的话,也会有json.dumps问题(Object of type Decimal is not JSON serializable); 就只有自己在json.dumps外面封装一层了. (以后再说吧-_-)
		if field_type == 246: # decimal, Json_decimal::get_binary
			precision,scale = data[0],data[1]
			p1 = map_decimal(precision-scale)
			p1.reverse()
			p2 = map_decimal(scale)
			rdata = B2DECIMAL(data[2:],p1,p2)
		elif field_type in [7,10,11,12]: # timestamp,date,time,datetime
			rdata = self._decode_packed_datetime(field_type,data[:8]) # 固定8字节(TIME_to_longlong_packed)
		elif field_type == 253: # MYSQL_TYPE_VAR_STRING varchar
			rdata = data.decode('utf-8','replace')
		else:
			rdata = f'base64:type{field_type}:{base64.b64encode(data).decode()}'
		return rdata

	def _decode_packed_datetime(self,field_type,data):
		packed = int.from_bytes(data,'little',signed=True)
		signed = packed < 0
		tp = -packed if signed else packed
		sign = '-' if signed else ''
		us = tp%(1<<24) # 小段字节序的,也就是前面部分是us.感觉描述得还是别扭... [us:dt]
		dt = tp>>24
		rdata = None
		if field_type == 11: # time
			rdata = f'{sign}{dt>>12:02d}:{(dt>>6)%64:02d}:{dt%64:02d}'
		else:
			ymd = dt >> 17
			hms = dt % (1<<17)
			ym = ymd>>5
			year = ym//13
			month = ym%13
			day = ymd%32
			if field_type == 10: # date
				rdata = f'{sign}{year:04d}-{month:02d}-{day:02d}'
			else: # datetime,timestamp
				rdata = f'{sign}{year:04d}-{month:02d}-{day:02d} {hms>>12:02d}:{(hms>>6)%64:02d}:{hms%64:02d}'
		# 精度,与mysql保持一致,固定输出精度
		if field_type != 10: 
			rdata += '.' + str(us).zfill(6)
		return rdata

	def init(self,):
		#print(self.bdata)
		if self.t >= 0x04: # 标量
			return self.read_scalar()
		self.element_count = self.read_little()
		#print("ELEMENT COUNT:",self.element_count)
		#print(self.read_little())
		self._size = self.read_little()
		#print(f"THIS OBJECT SIZE:",self._size, "ACTUAL SIZE:",len(self.bdata))
		if self._size != len(self.bdata):
			return None
		#print("WILL INIT")
		if self.t == 0x00 or self.t == 0x01: #object
			self._type = "JSON Object"
			#print(f"THIS TYPE IS {self._type}")
			self.data = {}
			self.read_key_entry()
			self.read_value_entry()
			self.read_key()
			self.read_value()
			self.data = {k:v for k,v in zip(self.key,self.value)}

		elif self.t == 0x02 or self.t == 0x03: #array
			self._type = "JSON Array"
			#print(f"THIS TYPE IS {self._type}")
			self.data = []
			self.read_value_entry()
			self.read_value()
			self.data = self.value
		return self.data
			

	def read_little(self,ssize=None):
		ssize = self.ssize if ssize is None else ssize
		s = int.from_bytes(self.read(ssize),'little')
		#print(f"READ LITTLE SIZE: {ssize} bytes  bdata:{self._bdata} value:{s} ")
		return s

	def read(self,n):
		_t = self.bdata[self.offset:self.offset+n]
		self.offset += n
		self._bdata = _t
		return _t

	def _read_int(self,n):
		data = self.read(n)
		return int.from_bytes(data,'big')

	def read_uint(self,n,is_unsigned=True):
		_t = self._read_int(n)
		_s = n*8 - 1
		#print("read uint",self._bdata,_t,_s)
		return (_t&((1<<_s)-1))-2**_s if _t < 2**_s and not is_unsigned else (_t&((1<<_s)-1))

	def read_int(self,n):
		return self.read_uint(n,False)

	def read_inline_data(self,t):
		n = 0
		is_unsigned = False # 默认是False,居然写成了True这么久都没发现...
		#print("\tread_inline_data TYPE:",t)
		if t == 0x05: #int16
			n = 2
		elif t == 0x06: #uint16
			n = 2
			is_unsigned = True
		elif t == 0x07: #int32
			n = 4
		elif t == 0x08: #uint32
			n = 4
			is_unsigned = True
		elif t == 0x09: #int64
			n = 8
		elif t == 0x0a: #uint64
			n = 8
			is_unsigned = True
		#return self.read_uint(n,is_unsigned)
		signed = False if is_unsigned else True
		rs = int.from_bytes(self.read(n),'little',signed=signed)
		#print("\tINLINE DATA:",rs)
		return rs




#aa = btojson(b'\x00\x01\x00\r\x00\x0b\x00\x02\x00\x05{\x00t1')
#aa = btojson(b'\x00\x01\x00,\x00\x0b\x00\x02\x00\x0c\r\x00t1\x1eAAAAAAAAAAAAAAAAACBBBBBBBBBBBB')
#aa = btojson(b'\x00\x02\x00)\x00\x12\x00\x02\x00\x14\x00\x02\x00\x00\x16\x00\x0c&\x00a1a2\x01\x00\x10\x00\x0b\x00\x02\x00\x0c\r\x00b1\x02b1\x02a6')
#aa = jsonob(b'\x01\x00\r\x00\x0b\x00\x02\x00\x05{\x00t1',0x00)
#aa = jsonob(b'\x01\x00,\x00\x0b\x00\x02\x00\x0c\r\x00t1\x1eAAAAAAAAAAAAAAAAACBBBBBBBBBBBB',0x00)
#aa = jsonob(b'\x02\x00)\x00\x12\x00\x02\x00\x14\x00\x02\x00\x00\x16\x00\x0c&\x00a1a2\x01\x00\x10\x00\x0b\x00\x02\x00\x0c\r\x00b1\x02b1\x02a6',0x00)
#aa = jsonob(b'\x03\x00T\x00\x00\r\x00\x007\x00\x00G\x00\x01\x00*\x00\x0b\x00\x02\x00\x00\r\x0013\x01\x00\x1d\x00\x0b\x00\x02\x00\x00\r\x00CC\x01\x00\x10\x00\x0b\x00\x02\x00\x0c\r\x00DD\x02DD\x01\x00\x10\x00\x0b\x00\x02\x00\x0c\r\x00BB\x02BB\x01\x00\r\x00\x0b\x00\x02\x00\x05\x02\x00FF',0x02)
#print(aa.init())
