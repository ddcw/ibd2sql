#@mysql sql/json_binary.h
import struct
import sys

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
				_data = self.read_little()
				if _data == 1:
					data = True
				elif _data == 2:
					data = False
				elif _data == 0:
					data = None
				else:
					data = ''
			elif t >= 0x05 and t <= 0x0a: #inline data
				#print("READ VALUE ENTRY Inline data for INT",t,0x05,0x0a)
				data = self.read_inline_data(t)
			elif t == 0x0b: #double
				#print("READ VALUE ENTRY Double")
				#data = struct.unpack('d',self.read(8))[0]
				data = self.read_little()
			elif t == 0x0c: #string
				#print("READ DATA ENTRY STRING",self.offset)
				data = self.read_little() #OFFSET
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
				value.append(struct.unpack('d',self.bdata[x[1]:x[1]+8])[0])
			elif x[0] <= 0x03: #json对象, 又递归
				s = self.ssize
				size = int.from_bytes(self.bdata[x[1]+s: x[1]+s+s ], 'little')
				data = self.bdata[x[1]:x[1]+size]
				_aa = jsonob(data,x[0])
				value.append(_aa.init())
			else:
				value.append(x[1])
		self.value = value
				
	def read_var(self,offset):
		"""
		读mysql的varchar的 记录长度的大小, 范围字节数量和大小
		如果第一bit是1 就表示要使用2字节表示:
			后面1字节表示 使用有多少个128字节, 然后加上前面1字节(除了第一bit)的数据(0-127) 就是最终数据
-----------------------------------------------------
| 1 bit flag | 7 bit data | if flag, 8 bit data*128 |
-----------------------------------------------------
		"""
		_s = int.from_bytes(self.bdata[offset:offset+1],'little')
		size = 1
		if _s & (1<<7):
			size += 1
			_s = self.bdata[offset:offset+2]
			_t = int.from_bytes(_s[1:2],'little')*128 + int.from_bytes(_s[:1],'little')-128
		else:
			_t = _s
			
		return size,_t


	def init(self,):
		#print(self.bdata)
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
		is_unsigned = True
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
