#innodb type
# storage/innobase/include/data0type.h
# storage/innobase/include/data0type.ic
import re
import base64

INNODB_TYPE = {
	2: 'tinyint',
	3: 'smallint',
	4: 'int',
	5: 'float',
	6: 'double',
	9: 'bigint',
	10:'mediumint',
	14:'year',
	15:'date',
	16:'varbinary', #varchar
	17:'bit',
	18:'timestamp',
	19:'datetime',
	20:'time',
	21:'decimal',
	22:'enum',
	23:'set',
	24:'tinyblob', #tinytext
	25:'mediumblob', #mediumtext
	26:'longblob', #longtext
	27:'blob', #text
	29:'char', # not binary 虽然和char都是29, 但存储方式不同.... -_-
	30:'geom', # 坐标之力
	31:'json',
	32:'vector' # 向量
}

def innodb_type_isvar(col):
	"""
varsize: varsize.size
   |
   |    size:data size
   |    |
VARSIZE DATA  ----< elements_dict: when type in (enum,set)
   |    |
   |    isbig:isbig?
   |
isvar: isvar?
	"""
	ct = INNODB_TYPE[col['type']]
	isvar = False
	size = 0
	isbig = False
	extra = None
	elements_dict = {}
	for e in col['elements']:
		ename = base64.b64decode(e['name']).decode()
		ekey = e['index']
		elements_dict[ekey] = ename
	esize = len(elements_dict)
	varsize = 0 #可变长度的大小 0:自适应(for varchar),  1+ 记录数据大小的 大小 VARSIZE:DATA Like:varsize.size
	if ct == "tinyint":
		size = 1
	elif col['column_type_utf8'][:6] == 'binary':
		size = int(re.compile(r'binary\((.+)\)').findall(col['column_type_utf8'],)[0])
		ct = 'binary'
	elif ct == "smallint":
		size = 2
	elif ct == "int":
		size = 4
	elif ct == "float":
		try:
			ext = int(re.compile(r'float\((.+)\)').findall(col['column_type_utf8'],)[0])
		except:
			ext = 0
			
		size = 4 if ext <= 24 else 8
	elif ct == "double":
		size = 8
	elif ct == "bigint":
		size = 8
	elif ct == "mediumint":
		size = 3
	elif ct == "year":
		size = 1
	elif ct == "date":
		size = 3
	elif ct == "varbinary":
		isvar = True
	elif ct == "bit":
		try:
			ext = int(re.compile(r'bit\((.+)\)').findall(col['column_type_utf8'],)[0])
		except:
			ext = 0
		size = int((ext+7)/8)
	elif ct == "timestamp":
		try:
			ext = int(re.compile(r'timestamp\((.+)\)').findall(col['column_type_utf8'],)[0])
		except:
			ext = 0
		size = 4+int((ext+1)/2)
	elif ct == "datetime":
		try:
			ext = ext = int(re.compile(r'datetime\((.+)\)').findall(col['column_type_utf8'],)[0])
		except:
			ext = 0
		size = 5+int((ext+1)/2)
	elif ct == "time":
		try:
			ext = int(re.compile(r'time\((.+)\)').findall(col['column_type_utf8'],)[0])
		except:
			ext = 0
		size = 3+int((ext+1)/2)
	elif ct == "decimal":
		try:
			total_digits, decimal_digits = re.compile(r'decimal\((.+)\)').findall(col['column_type_utf8'],)[0].split(',')
			total_digits = int(total_digits)
			decimal_digits = int(decimal_digits)
			integer_p1_count = int((total_digits - decimal_digits)/9) #
			integer_p2_count = total_digits - decimal_digits - integer_p1_count*9
			integer_size = integer_p1_count*4 + int((integer_p2_count+1)/2)
			decimal_p1_count = int(decimal_digits/9)
			decimal_p2_count = decimal_digits - decimal_p1_count*9
			decimal_size = decimal_p1_count*4 + int((decimal_p2_count+1)/2)
			total_size = integer_size + decimal_size

			size = total_size #decimal占用大小
			extra = (integer_size,decimal_size,(total_digits,decimal_digits))
		except:
			size = 0
	elif ct == "enum":
		size = 2 if esize >= 2**8 else 1 #只有一个值, 2字节能表示65535 value
	elif ct == "set":
		size = int((esize+7)/8) #多个值, 每个值一个bit.  MAX:8bytes=64bit
	elif ct == "tinytext":
		varsize = 1
		isvar = True
	elif ct == "mediumblob":
		size = 20
		isvar = True
		isbig = True
	elif ct == "longblob":
		size = 20
		isvar = True
		isbig = True
	elif ct == "blob":
		size = 20
		isvar = True
		isbig = True
	elif ct == "char":
		isvar = True #innodb_default_row_format != COMPACT
		size = int(re.compile(r'char\((.+)\)').findall(col['column_type_utf8'],)[0]) # issue 9
	elif ct == "json":
		size = 20
		isvar = True
		isbig = True
	elif ct == 'geom':
		isvar = True
		isbig = True
	elif ct == 'vector':
		isvar = True
		isbig = True

	return ct,isvar,size,isbig,elements_dict,varsize,extra #数据类型, 是否为变长, 大小, 是否为大字段, set/enum elements

def innodb_data_to_py(bdata,col):
	if dtype == 'int':
		pass
		
