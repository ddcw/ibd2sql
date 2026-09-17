import struct
import sys
#sys.setrecursionlimit(20)

def DEJSONTYPE(t):
	isbig = False
	signed = False
	size = 2
	name = ''
	_type = 'None'
	if t <= 3:
		_type = 'obj' if t <= 1 else 'array'
		isbig = True if t%2 == 1 else False
		name = f"{'large' if isbig else 'small'} JSON object"
		size = 4 if isbig else 2
	elif t == 4:
		_type = 'literal'
		name = "literal"
		size = 2
	elif t <= 10:
		_type = 'int'
		if t in [7,8]:
			size = 4
		if t in [9,10]:
			size = 8
		signed = True if t%2 == 1 else False
		name = f"{'' if signed else 'u'}int{size*8}"
	elif t == 11:
		size = 8
		name = 'double'
		_type = 'double'
	elif t == 12:
		name = 'utf8mb4 string'
		_type = 'char'

	return {
		'isbig':isbig,
		'signed':signed,
		'size':size,
		'name':name,
		'type':_type,
		't':t
	}



class JSON2DICT(object):
	def __init__(self,data):
		self.data = data
		self.offset = 0
		self.offset_start = 0

	def read(self,n,offset_start=1,offset=0):
		toffset = offset_start + offset
		data = self.data[toffset:toffset+n]
		#print(offset_start,'OFFSET:',self.offset,'-->',end='')
		#print(self.offset)
		return offset+n,data

	def init(self,offset_start=1,t=None,offset=0):
		if t is None: # first init
			t = self.data[0]
		dj = DEJSONTYPE(t)
		#print(offset_start,dj['type'],dj)
		if dj['type'] == 'obj': # json object
			offset,data = self.read(dj['size'],offset_start,offset)
			element_count = int.from_bytes(data,'little')
			#print('ELEMENT OBJ COUNT:',element_count)
			offset,data = self.read(dj['size'],offset_start,offset)
			size = int.from_bytes(data,'little')
			offset,key_entry = self._read_key_entry(offset,offset_start,element_count,dj['size'])
			offset,value_entry = self._read_value_entry(offset,offset_start,element_count)
			offset,key = self._read_key(offset,offset_start,key_entry)
			#print(offset_start,'^^^^^^^^^^^^^^^^^^^',len(value_entry))
			offset,value = self._read_value(offset,offset_start,value_entry)
			#print(offset_start,'*******************',value,len(value_entry))
			return {k:v for k,v in zip(key,value)}
		elif dj['type'] == 'array': # json array
			offset,data = self.read(dj['size'],offset_start,offset)
			element_count = int.from_bytes(data,'little')
			#print('ELEMENT ARRAY COUNT:',element_count)
			offset,data = self.read(dj['size'],offset_start,offset)
			size = int.from_bytes(data,'little')
			offset,value_entry = self._read_value_entry(offset,offset_start,element_count)
			offset,value = self._read_value(offset,offset_start,value_entry)
			#print(offset_start,'################VALUE,',value)
			return value
		elif dj['type'] == 'literal': # literal(null/true/false)
			offset,data = self.read(2,offset_start,offset)
			data, = struct.unpack('<B',data)
			if data == 0:
				return None
			elif data == 1:
				return True
			elif data == 2:
				return False
			else:
				return None
		elif dj['type'] == 'int':
			offset,data = self.read(dj['size'],offset_start,offset)
			return int.from_bytes(data,'little',signed=dj['signed'])
		elif dj['type'] == 'double':
			offset,data = self.read(dj['size'],offset_start,offset)
			return struct.unpack('d',data)[0]
		elif dj['type'] == 'char':
			offset,data = self._read_vardata(offset,offset_start)
			return data
		else:
			return 'null'

	def _read_key_entry(self,offset,offset_start,count,size):
		rdata = []
		for x in range(count):
			offset,data = self.read(size,offset_start,offset)
			key_offset = int.from_bytes(data,'little')
			offset,data = self.read(2,offset_start,offset)
			key_length = int.from_bytes(data,'little')
			rdata.append([key_offset,key_length])
		return offset,rdata

	def _read_key(self,offset,offset_start,key_entry):
		rdata = []
		for x in key_entry:
			offset = x[0]
			offset,data = self.read(x[1],offset_start,offset)
			rdata.append(data.decode())
		return offset,rdata

	def _read_value_entry(self,offset,offset_start,count):
		rdata = []
		for x in range(count):
			tdata = None
			offset,data = self.read(1,offset_start,offset)
			t = int.from_bytes(data,'little')
			dj = DEJSONTYPE(t)
			if dj['type'] == 'int':
				offset,data = self.read(dj['size'],offset_start,offset)
				tdata = int.from_bytes(data,'little',signed=dj['signed'])
			elif dj['type'] == 'double':
				offset,data = self.read(dj['size'],offset_start,offset)
				tdata, = struct.unpack('>d',data)
			elif dj['type'] == 'char':
				offset,data = self.read(dj['size'],offset_start,offset)
				tdata = int.from_bytes(data,'little',signed=False)
			elif dj['type'] == 'literal':
				offset,data = self.read(dj['size'],offset_start,offset)
				tdata = int.from_bytes(data,'little',signed=False)
			else:
				offset,data = self.read(dj['size'],offset_start,offset)
				#print('#########################################',offset_start,offset,data)
				tdata = int.from_bytes(data,'little',signed=False) + offset_start
				#print(offset_start,tdata,dj)
			rdata.append([dj,tdata])
		return offset,rdata

	def _read_value(self,offset,offset_start,value_entry):
		rdata = []
		for dj,tdata in value_entry:
			if dj['type'] == 'char':
				#self.offset = dj['size']
				#print('QQQQQQQQQQQQQQQ',offset_start,offset,tdata)
				offset = tdata
				offset,data = self._read_vardata(offset,offset_start)
				rdata.append(data)
			elif dj['type'] in ['array','obj']:
				#print('PPPPPPPPPPPPPPP',offset,tdata,dj)
				rdata.append(self.init(tdata,dj['t']))
			else:
				rdata.append(tdata)
		return offset,rdata

	def _read_vardata(self,offset,offset_start):
		"""Read MySQL JSON binary variable-length string data."""
		length = 0
		shift = 0
		num_bytes = 0
		max_bytes = 5  # uint32 can require up to 5 base-128 bytes

		while num_bytes < max_bytes:
			offset,data = self.read(1,offset_start,offset)
			if len(data) != 1:
				raise ValueError("truncated JSON variable-length field")
			byte, = struct.unpack('<B',data)
			num_bytes += 1
			length |= (byte & 0x7f) << shift
			if not (byte & 0x80):
				if length > 0xffffffff:
					raise ValueError("JSON variable-length field exceeds uint32")
				offset,data = self.read(length,offset_start,offset)
				if len(data) != length:
					raise ValueError("truncated JSON string data")
				return offset,data.decode()
			shift += 7

		raise ValueError("invalid JSON variable-length field")
