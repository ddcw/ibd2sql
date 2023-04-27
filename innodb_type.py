import re
import struct
import time

#根据字段类型返回是否可变长和长度
def innodb_isvar_size(col):
	if re.match('varchar',col['column_type_utf8'],re.I):
		return True,int(re.compile('varchar\((.+)\)').findall(col['column_type_utf8'],)[0]),'varchar'
	
	if re.match('tinyint',col['column_type_utf8'],re.I):
		return False,1,'tinyint'

	if re.match('smallint',col['column_type_utf8'],re.I):
		return False,2,'smallint'

	if re.match('mediumint',col['column_type_utf8'],re.I):
		return False,3,'mediumint'

	if re.match('bigint',col['column_type_utf8'],re.I):
		return False,8,'bigint'

	if re.match('int',col['column_type_utf8'],re.I):
		return False,4,'int'

	if re.match('float',col['column_type_utf8'],re.I):
		return False,4,'float'

	if re.match('double',col['column_type_utf8'],re.I):
		return False,8,'double'

	if re.match('real',col['column_type_utf8'],re.I):
		return False,8,'real'

	if re.match('char',col['column_type_utf8'],re.I):
		return False,int(re.compile('char\((.+)\)').findall(col['column_type_utf8'],)[0]),'char'

	if re.match('blob',col['column_type_utf8'],re.I):
		return True,0,'blob'

	if re.match('text',col['column_type_utf8'],re.I):
		return True,0,'text'

	if re.match('timestamp',col['column_type_utf8'],re.I):
		ext = 0
		if re.match('timestamp\(.*\)',col['column_type_utf8'],re.I):
			ext = int(re.compile('timestamp\((.+)\)').findall(col['column_type_utf8'],)[0])
		return False,4+int((ext+1)/2),'timestamp'

	if re.match('datetime',col['column_type_utf8'],re.I):
		ext = 0
		if re.match('datetime\(.*\)',col['column_type_utf8'],re.I):
			ext = int(re.compile('datetime\((.+)\)').findall(col['column_type_utf8'],)[0])
		return False,5+int((ext+1)/2),'datetime' #5,6,7,8

	if re.match('year',col['column_type_utf8'],re.I):
		return False,1,'year'

	if re.match('time',col['column_type_utf8'],re.I):
		ext = 0
		if re.match('time\(.*\)',col['column_type_utf8'],re.I):
			ext = int(re.compile('time\((.+)\)').findall(col['column_type_utf8'],)[0])
		return False,3+int((ext+1)/2),'time' 

	if re.match('date',col['column_type_utf8'],re.I):
		return False,3,'date'

	return True,0,'TODO'


#数据转换
#https://dev.mysql.com/doc/refman/8.0/en/time.html
#https://dev.mysql.com/doc/refman/8.0/en/storage-requirements.html#data-types-storage-reqs-date-time
def transdata(dtype,bdata,precision=None): #暂不支持精度, 根据对象长度就可以判断的,
	if dtype == 'int':
		_t = struct.unpack('>L',bdata[:4])[0]
		return (_t&((1<<31)-1)) if _t&(1<<31) else -(_t&((1<<31)-1))

	if dtype  == 'varchar':
		return bdata.decode()

	if dtype == 'char':
		return bdata.decode().rstrip() #默认去掉结尾的空格

	if dtype in ['year','tinyint']:
		return struct.unpack('>B',bdata)[0]

	#一共3字节 1bit符号,  14bit年  4bit月  5bit日 这TM有点意思..... -_-
	if dtype == 'date':
		idata = int.from_bytes(bdata[:3],'big')
		year = ((idata & ((1 << 14) - 1) << 9) >> 9)
		month = (idata & ((1 << 4) - 1) << 5) >> 5
		day = (idata& ((1 << 5) - 1))
		great0 = True if idata&(1<<23) else False
		return f'{year}-{month}-{day}' if great0 else f'-{year}-{month}-{day}'

	#1bit符号  year_month:17bit  day:5  hour:5  minute:6  second:6 
	if dtype == 'datetime':
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
		if fraction is None:
			return f'{year}-{month}-{day} {hour}:{minute}:{second}' if great0 else f'-{year}-{month}-{day} {hour}:{minute}:{second}' 
		else:
			return f'{year}-{month}-{day} {hour}:{minute}:{second}.{fraction}' if great0 else f'-{year}-{month}-{day} {hour}:{minute}:{second}.{fraction}' 
	

	if dtype == 'timestamp':
		ltime = time.localtime(int.from_bytes(bdata[:4],'big'))
		fraction = int.from_bytes(bdata[4:],'big') if len(bdata)>4 else None
		if fraction is None:
			return f'{ltime.tm_year}-{ltime.tm_mon}-{ltime.tm_mday} {ltime.tm_hour}:{ltime.tm_min}:{ltime.tm_sec}'
		else:
			return f'{ltime.tm_year}-{ltime.tm_mon}-{ltime.tm_mday} {ltime.tm_hour}:{ltime.tm_min}:{ltime.tm_sec}.{fraction}'

	#一共3字节 1bit符号  hour:11bit    minute:6bit  second:6bit  
	if dtype == 'time':
		idata = int.from_bytes(bdata[:3],'big')
		hour = ((idata & ((1 << 10) - 1) << 12) >> 12) #实际上10bit, 还有个保留位
		minute = (idata & ((1 << 6) - 1) << 6) >> 6
		second = (idata& ((1 << 6) - 1))
		great0 = True if idata&(1<<23) else False
		fraction = int.from_bytes(bdata[3:],'big') if len(bdata)>3 else None
		if fraction is None:
			return f'{hour}:{minute}:{second}' if great0 else f'-{hour}:{minute}:{second}'
		else:
			return f'{hour}:{minute}:{second}.{fraction}' if great0 else f'-{hour}:{minute}:{second}.{fraction}'

