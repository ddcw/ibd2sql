# convert binary data to data(int/str/json)
# future: geom

import struct
import json
import time
from .charset.armscii8 import DD_ARMSCII8
from .charset.dec8 import DD_DEC8
from .charset.geostd8 import DD_GEOSTD8
from .charset.hp8 import DD_HP8
from .charset.keybcs2 import DD_KEYBCS2
from .charset.swe7 import DD_SWE7
from .charset.tis620 import DD_TIS620
from .mysql_json import jsonob
from .mysql_json2 import JSON2DICT

# Format Big Unsigned Int 4 bytes
_F_B_U_INT4 = struct.Struct('>L')

# Format Double
_F_D = struct.Struct('d')

def map_decimal(n):
	# [[bytes, length], [],... ]
	return [ [4,9] for _ in range(n//9) ] + ([[ ((n%9)+1)//2 if n%9 < 7 else 4,n%9 ]] if n%9 > 0 else [])

# convert binary data to unsigned int
def B2UINT4(data):
	return struct.unpack('>L',data)[0]

def B2INT4(data):
	return struct.unpack('>L',data)[0] - 2147483648

def B2UINT3(data):
	return struct.unpack('>L',data+b'\x00')[0]>>8

def B2INT3(data):
	return (struct.unpack('>L',data+b'\x00')[0]>>8) - 8388608

def B2UINT2(data):
	return struct.unpack('>H',data)[0]

def B2INT2(data):
	return struct.unpack('>H',data)[0] - 32768

def B2UINT1(data):
	return struct.unpack('>B',data)[0]

def B2INT1(data):
	return struct.unpack('>B',data)[0] - 128

def B2UINT8(data):
	return struct.unpack('>Q',data)[0]

def B2INT8(data):
	return struct.unpack('>Q',data)[0] - 9223372036854775808

def B2UINT6(data):
	return (B2UINT4(data[:4])<<16) + B2UINT2(data[4:6])

def B2UINT7(data):
	return (B2UINT4(data[:4])<<24) + B2UINT3(data[4:7])

def B2BIT(data): # unsigned big int
	return '0x' + data.hex()

B2INT = B2INT4

def B2DOUBLE(data):
	return struct.unpack('d',data)[0]

def B2FLOAT(data):
	return struct.unpack('f',data)[0]

def B2YEAR(data):
	return B2UINT1(data) + 1900

def __year(data):
	return str(data).zfill(4)

def __month(data):
	return str(data).zfill(2)

def __day(data):
	return str(data).zfill(2)

def __hour(data):
	return str(data).zfill(2)

def __minute(data):
	return str(data).zfill(2)

def __second(data):
	return str(data).zfill(2)

def B2DATE(data):
	t = B2UINT3(data)
	signed = t&8388608
	year = (t&8388096)>>9
	month = (t&480)>>5
	day = t&31
	return repr(__year(year)+'-'+__month(month)+'-'+__day(day))

def B2TIME(data,pad): #(data,with fsp)
	t = B2INT3(data[:3])
	signed = ''
	fractional = ''
	if t < 0:
		signed = '-'
		hour= 2047 - ((8384512&t)>>12)
		minute = 63 - ((4032&t)>>6)
		second = 63 - (63&t)
		if pad > 0:
			fr = int.from_bytes(data[3:],'big')
			if fr == 0:
				second += 1
				fractional = 0
			else:
				fractional = 2**((pad+1)//2*8) - fr
	else:
		hour = (8384512&t)>>12
		minute = (4032&t)>>6
		second = 63&t
		if pad > 0:
			fractional = int.from_bytes(data[3:],'big')
	if fractional != '':
		fractional = "." + str(fractional).zfill(pad)[:pad]
	return repr(signed + __hour(hour) + ':' + __minute(minute) + ':' + __second(second) 
		+ fractional)

def B2DATETIME(data,pad):
	t = (B2UINT4(data[:4])<<8) + B2UINT1(data[4:5])
	months = (t&549751619584)>>22
	year = months//13
	month = months%13
	day = (t&4063232)>>17
	hour = (t&126976)>>12
	minute = (t&4032)>>6
	second = t&63
	fractional = ''
	if pad > 0:
		fractional = "." + str(int.from_bytes(data[5:],'big')).zfill(pad)[:pad]
	return repr(__year(year)+'-'+__month(month)+'-'+__day(day)+' '
		+ __hour(hour) + ':' + __minute(minute) + ':' + __second(second) 
		+ fractional)
			

def B2TIMESTAMP(data,pad):
	t = time.localtime(B2UINT4(data[:4]))
	year = t.tm_year
	month = t.tm_mon
	day = t.tm_mday
	hour = t.tm_hour
	minute = t.tm_min
	second = t.tm_sec
	fractional = ''
	if pad > 0:
		fractional = "." + str(int.from_bytes(data[4:],'big')).zfill(pad)[:pad]
	return repr(__year(year)+'-'+__month(month)+'-'+__day(day)+' '
		+ __hour(hour) + ':' + __minute(minute) + ':' + __second(second) 
		+ fractional)
	

# decode binary data
def B2STR_armscii8(data):
	return repr(b''.join([ DD_ARMSCII8[x] for x in data ]).decode())

def B2STR_ascii(data):
	return repr(data.decode('utf-8'))

def B2STR_big5(data):
	return repr(data.decode('big5'))

def B2STR_binary(data):
	return '0x'+data.hex()

def B2STR_cp1250(data):
	return repr(data.decode('cp1250'))

def B2STR_cp1251(data):
	return repr(data.decode('cp1251'))

def B2STR_cp1256(data):
	return repr(data.decode('cp1256'))

def B2STR_cp1257(data):
	return repr(data.decode('cp1257'))

def B2STR_cp850(data):
	return repr(data.decode('cp850'))

def B2STR_cp852(data):
	return repr(data.decode('cp852'))

def B2STR_cp866(data):
	return repr(data.decode('cp866'))

def B2STR_cp932(data):
	return repr(data.decode('cp932'))

def B2STR_dec8(data):
	return repr(b''.join([ DD_DEC8[x] for x in data ]).decode())

def B2STR_eucjpms(data):
	return repr(data.decode('euc-jp'))

def B2STR_euckr(data):
	return repr(data.decode('euc-kr'))

def B2STR_gb18030(data):
	return repr(data.decode('gb18030'))

def B2STR_gb2312(data):
	return repr(data.decode('gb2312'))

def B2STR_gbk(data):
	return repr(data.decode('gbk'))

def B2STR_geostd8(data):
	return repr(b''.join([ DD_GEOSTD8[x] for x in data ]).decode())

def B2STR_greek(data):
	return repr(data.decode('iso8859-7'))

def B2STR_hebrew(data):
	return repr(data.decode('iso8859-8'))

def B2STR_hp8(data):
	return repr(b''.join([ DD_HP8[x] for x in data ]).decode())

def B2STR_keybcs2(data):
	return repr(b''.join([ DD_KEYBCS2[x] for x in data ]).decode())

def B2STR_koi8r(data):
	return repr(data.decode('koi8-r'))

def B2STR_koi8u(data):
	return repr(data.decode('koi8-u'))

def B2STR_latin1(data):
	return repr(data.decode('latin1'))

def B2STR_latin2(data):
	return repr(data.decode('iso8859-2'))

def B2STR_latin5(data):
	return repr(data.decode('iso8859-9'))

def B2STR_latin7(data):
	return repr(data.decode('iso8859-13'))

def B2STR_macce(data):
	return repr(data.decode('mac-latin2'))

def B2STR_macroman(data):
	return repr(data.decode('macroman'))

def B2STR_sjis(data):
	return repr(data.decode('shift-jis'))

def B2STR_swe7(data):
	return repr(b''.join([ DD_SWE7[x] for x in data ]).decode())

def B2STR_tis620(data):
	#return repr(data.decode('tis-620'))
	return repr(b''.join([ DD_TIS620[x] for x in data ]).decode())

def B2STR_ucs2(data):
	return repr(data.decode('utf-16-be'))

def B2STR_ujis(data):
	return repr(data.decode('euc_jp'))

def B2STR_utf16(data):
	return repr(data.decode('utf-16-be'))

def B2STR_utf16le(data):
	return repr(data.decode('utf-16-le'))

def B2STR_utf32(data):
	return repr(data.decode('utf-32-be'))

def B2STR_utf8(data):
	return repr(data.decode('utf-8'))

def B2STR_utf8mb4(data):
	return repr(data.decode('utf-8'))

B2STR = B2STR_utf8

def _READ_DECIMAL(data,p,offset):
	rdata = ""
	for psize,pzfill in p:
		tdata = int.from_bytes(data[offset:offset+psize],'big',signed=False)
		rdata += str(tdata).zfill(pzfill)
		offset += psize
	return rdata,offset

# decimal
# b'\x7f\xff\xff\xff\xff\xff\xff\xfc\xff\xeb'  -3.0020
# b'\x80\x00\x00\x00\x00\x00\x00\x03\x00\x14'   3.0020
def B2DECIMAL(data,p1,p2):
	p1_data = ""
	signed = False if struct.unpack('>B',data[:1])[0] & 128 else True
	if signed:
		data = bytes((~b&0xff) for b in data)
	data = struct.pack('>B',data[0]-128)+data[1:]
	offset = 0
	p1_data,offset = _READ_DECIMAL(data,p1,offset)
	p2_data,offset = _READ_DECIMAL(data,p2,offset)
	p1_data = str(int(p1_data))
	return f"{'-' if signed else ''}{p1_data}.{p2_data}"
		
	p1_data = "".join([ toint(bdata).zfill(zfill) for zfill,bdata in data[0] ])
	p2_data = "".join([ toint(bdata).zfill(zfill) for zfill,bdata in data[1] ])
	return str(int(p1_data)) + str(p2_data)

# ENUM
def B2ENUM(data,elements):
	return repr(elements[int.from_bytes(data,'big',signed=False)])

# SET
def B2SET(data,elements):
	data = int.from_bytes(data,'big',signed=False)
	rdata = ""
	n = 0
	for x in elements:
		if 1<<n & data:
			rdata += elements[x] + ","
		n += 1
	return repr(rdata[:-1])

# GEOMETRY
def B2GEOMETRY(data,srsid):
	extra_srsid = f"{srsid:08x}" if srsid == 0 else ""
	return f"0x{extra_srsid}{hex(int.from_bytes(data,'big',signed=False))[2:]}"

# VECTOR
def B2VECTOR(data):
	return data.hex()

def B2JSON(data):
	#return repr(json.dumps(jsonob(data[1:],struct.unpack('<B',data[:1])[0]).init()))
	return repr(json.dumps(jsonob(data[1:],struct.unpack('<B',data[:1])[0]).init()))
	#return repr(json.dumps(JSON2DICT(data).init()))
