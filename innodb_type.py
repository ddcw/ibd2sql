#@ddcw
import re
import struct
import time

#根据字段类型返回是否可变长和长度
#如果是char的话, 需要知道字符集, 这里就默认使用utf8mb3了, 大小就是3字节
def innodb_isvar_size(col):
	if re.match('varchar',col['column_type_utf8'],re.I):
		return True,int(re.compile('varchar\((.+)\)').findall(col['column_type_utf8'],)[0]),'varchar'
	
	if re.match('varbinary',col['column_type_utf8'],re.I):
		return True,int(re.compile('varbinary\((.+)\)').findall(col['column_type_utf8'],)[0]),'varbinary'
	
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
		#return False,4,'float'
		ext = 0
		if re.match('float\(.*\)',col['column_type_utf8'],re.I):
			ext = int(re.compile('float\((.+)\)').findall(col['column_type_utf8'],)[0])
			
		#实际上超过24就是 double了...
		return False,4 if ext <= 24 else 8,'float'

	if re.match('double',col['column_type_utf8'],re.I):
		return False,8,'double'

	# include/decimal.h
	if re.match('decimal',col['column_type_utf8'],re.I):
		if re.match('decimal\(.*\)',col['column_type_utf8'],re.I):
			total_digits, decimal_digits = re.compile('decimal\((.+)\)').findall(col['column_type_utf8'],)[0].split(',')
			total_digits = int(total_digits)
			decimal_digits = int(decimal_digits)
			integer_p1_count = int((total_digits - decimal_digits)/9) #
			integer_p2_count = total_digits - decimal_digits - integer_p1_count*9
			integer_size = integer_p1_count*4 + int((integer_p2_count+1)/2)
			decimal_p1_count = int(decimal_digits/9)
			decimal_p2_count = decimal_digits - decimal_p1_count*9
			decimal_size = decimal_p1_count*4 + int((decimal_p2_count+1)/2)
			total_size = integer_size + decimal_size
		return False,total_size,'decimal',(integer_size,decimal_size,(total_digits,decimal_digits))

	if re.match('bit',col['column_type_utf8'],re.I):
		ext = 0
		if re.match('bit\(.*\)',col['column_type_utf8'],re.I):
			ext = int(re.compile('bit\((.+)\)').findall(col['column_type_utf8'],)[0])
		return False,int((ext+7)/8),'bit'


	#没得numeric, 其实就是decimal
	if re.match('numeric',col['column_type_utf8'],re.I):
		return False,0,'numeric'

	#并没得real类型, 所以不需要解析
	if re.match('real',col['column_type_utf8'],re.I):
		return False,4,'real'

	if re.match('char',col['column_type_utf8'],re.I):
		return False,int(re.compile('char\((.+)\)').findall(col['column_type_utf8'],)[0]),'char'

	if re.match('binary',col['column_type_utf8'],re.I):
		return False,int(re.compile('binary\((.+)\)').findall(col['column_type_utf8'],)[0]),'binary'

	if re.match('tinyblob',col['column_type_utf8'],re.I):
		return True,0,'tinyblob'

	if re.match('tinytext',col['column_type_utf8'],re.I):
		return True,0,'tinytext'

	if re.match('mediumtext',col['column_type_utf8'],re.I):
		return True,0,'mediumtext'

	if re.match('mediumblob',col['column_type_utf8'],re.I):
		return True,0,'mediumblob'

	if re.match('longtext',col['column_type_utf8'],re.I):
		return True,0,'longtext'

	if re.match('longblob',col['column_type_utf8'],re.I):
		return True,0,'longblob'

	if re.match('blob',col['column_type_utf8'],re.I): #不支持
		return True,256,'blob'

	if re.match('text',col['column_type_utf8'],re.I): #不支持
		return True,256,'text'

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

	if re.match('json',col['column_type_utf8'],re.I): #不支持
		return True,0,'json'

	if re.match('set',col['column_type_utf8'],re.I):
		return False,2,'set'

	if re.match('enum',col['column_type_utf8'],re.I):
		return False,8,'enum'

	return True,0,'TODO'


#数据转换
#https://dev.mysql.com/doc/refman/8.0/en/time.html
#https://dev.mysql.com/doc/refman/8.0/en/storage-requirements.html#data-types-storage-reqs-date-time
def transdata(dtype,bdata,is_unsigned=False,extra=None): 
	if dtype == 'int':
		_t = struct.unpack('>L',bdata[:4])[0]
		"""
		如果有符号且<2**31 就减去2**31 
		"""
		return (_t&((1<<31)-1))-2**31 if _t < 2**31 and not is_unsigned else (_t&((1<<31)-1))
		#return (_t&((1<<31)-1)) if _t&(1<<31) else -(_t&((1<<31)-1))

	if dtype == 'tinyint':
		_t = struct.unpack('>B',bdata)[0]
		return (_t&((1<<7)-1))-2**7 if _t < 2**7 and not is_unsigned else (_t&((1<<7)-1))

	if dtype == 'smallint':
		_t = struct.unpack('>H',bdata)[0]
		return (_t&((1<<15)-1))-2**15 if _t < 2**15 and not is_unsigned else (_t&((1<<15)-1))

	if dtype == 'mediumint':
		_t = int.from_bytes(bdata,'big')
		return (_t&((1<<23)-1))-2**23 if _t < 2**23 and not is_unsigned else (_t&((1<<23)-1))

	if dtype == 'bigint':
		_t = struct.unpack('>Q',bdata[:8])[0]
		return (_t&((1<<63)-1))-2**63 if _t < 2**63 and not is_unsigned else (_t&((1<<63)-1))

	if dtype == 'float':
		return struct.unpack('f',bdata)[0]

	if dtype == 'double':
		return struct.unpack('d',bdata)[0]

	if dtype  == 'decimal':
		p1 = extra[0] #整数部分字节数
		p2 = extra[1] #小数部分
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
		#print(f'{p1_data}.{p2_data}')
		return f"{p1_data}.{p2_data}"

	if dtype  == 'bit':
		#返回int类型.
		return int.from_bytes(bdata,'big')

	if dtype == 'char':
		#print(bdata)
		return bdata.decode().rstrip() #默认去掉结尾的空格
		#return bdata.decode()

	if dtype == 'binary':
		return bdata.decode()

	if dtype  == 'varchar':
		return bdata.decode()

	if dtype  == 'varbinary':
		return bdata.decode()

	if dtype  == 'tinyblob':
		return bdata.decode()

	if dtype  == 'tinytext':
		return bdata.decode()

	if dtype  == 'blob':
		return bdata.decode()

	if dtype  == 'text':
		return bdata.decode()

	if dtype  == 'mediumblob':
		return bdata.decode()

	if dtype  == 'mediumtext':
		return bdata.decode()

	if dtype  == 'longtext':
		return bdata.decode()

	if dtype  == 'longblob':
		return bdata.decode()

	if dtype  == 'json':
		return '' #TODO

	if dtype == 'set':
		#print(bdata,'set')
		return int.from_bytes(bdata,'big')

	if dtype == 'enum':
		#print(bdata,'enum')
		return int.from_bytes(bdata,'big')

	if dtype == 'year':
		return struct.unpack('>B',bdata)[0]+1901-1

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

