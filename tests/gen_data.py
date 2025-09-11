import random
import json
import sys
from datetime import datetime, timedelta


_STRINGS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S"
DATETIME_FORMAT = f"{DATE_FORMAT} {TIME_FORMAT}"

def getgen_int(start=-127,stop=127):
	return random.randint(start,stop)

def _getgen_en(start=1,stop=200):
	return ''.join(random.choice(_STRINGS) for _ in range(random.randint(start,stop)))

def getgen_en(start=1,stop=200):
	return repr(_getgen_en(start,stop))

def getgen_zh(start=1,stop=100):
	return repr(''.join(chr(random.randint(0x4E00, 0x9FFF)) for _ in range(random.randint(start,stop))))

def getgen_emoji(start=1,stop=100):
	return repr(''.join(chr(random.randint(0x1F600, 0x1F64F)) for _ in range(random.randint(start,stop))))

def getgen_datetime(start='1970-01-01 11:11:11',stop='2025-11-11 11:11:11'):
	start = datetime.strptime(start, DATETIME_FORMAT)
	stop = datetime.strptime(stop, DATETIME_FORMAT)
	rangesecond = int((stop - start).total_seconds())
	return repr((start + timedelta(seconds=random.randint(0,rangesecond))).strftime(DATETIME_FORMAT))

def getgen_date(start='1970-01-01 11:11:11',stop='2025-11-11 11:11:11'):
	return repr(datetime.strptime(getgen_datetime()[1:-1],DATETIME_FORMAT).strftime(DATE_FORMAT))

def getgen_time(start='1970-01-01 11:11:11',stop='2025-11-11 11:11:11'):
	return repr(datetime.strptime(getgen_datetime()[1:-1],DATETIME_FORMAT).strftime(TIME_FORMAT))

def getgen_float(start=-100000,stop=100000):
	return random.random()*random.randint(start,stop)

def getgen_decimal(p0=20,p1=4):
	return f"{'-' if random.choice((True,False)) else ''}{str(round(10**random.randint(0,p0-p1)*random.random(),p1))}"

def getgen_json(start=1,stop=10):
	data = {'author':'ddcw','url':'https://github.com/ddcw/ibd2sql'}
	for i in range(4):
		data[_getgen_en()] = _getgen_en()
	if random.choice((True,False)):
		data['test_int2'] = getgen_int(-2**15,2**15)
	if random.choice((True,False)):
		data['test_int4'] = getgen_int(-2**31,2**31)
	if random.choice((True,False)):
		data['test_int8'] = getgen_int(-2**63,2**63)
	if random.choice((True,False)):
		data['test_boolean'] = random.choice((True,False))
	if start < stop and random.choice((True,False)):
		data[_getgen_en()] = getgen_json(start,stop-1) if random.choice((True,False)) else [ getgen_json(start,stop-1) for _ in range(4) ]
	return data


def _ft(tablename):
	return f"`test_ibd2sql_by_ddcw_{tablename}`",f"DROP TABLE IF EXISTS `test_ibd2sql_by_ddcw_{tablename}`;\nCREATE TABLE IF NOT EXISTS `test_ibd2sql_by_ddcw_{tablename}`"

def test_int():
	name,ddl = _ft('int')
	ddl += """(
	id int,
	c_tinyint_01 tinyint,
	c_tinyint_02 tinyint unsigned,
	c_smallint_01 smallint,
	c_smallint_02 smallint unsigned,
	c_mediumint_01 mediumint,
	c_mediumint_02 mediumint unsigned,
	c_int_01 int,
	c_int_02 int unsigned,
	c_bigint_01 bigint,
	c_bigint_02 bigint unsigned
) engine=innodb;
	"""
	print(ddl)
	for i in range(200):
		print(f"insert into {name} values({i},{getgen_int(-127,127)},{getgen_int(0,255)},{getgen_int(-32767,32767)},{getgen_int(0,65535)},{getgen_int(-8388607,8388607)},{getgen_int(0,16777215)},{getgen_int(-2147483647,2147483647)},{getgen_int(0,4294967295)},{getgen_int(-9223372036854775807,9223372036854775807)},{getgen_int(0,18446744073709551615)});")

def test_char(): # char,varchar
	name,ddl = _ft('char')
	ddl += """(
	id int,
	c_char_01 char(20),
	c_char_02 char(127),
	c_char_03 char(255),
	c_varchar_01 varchar(20),
	c_varchar_02 varchar(127),
	c_varchar_03 varchar(255),
	c_varchar_04 varchar(300)
) engine=innodb;
"""
	print(ddl)
	for i in range(200):
		print(f"insert into {name} values({i},{getgen_en(0,18)},{getgen_en(0,120)},{getgen_en(0,255)},{getgen_en(0,20)},{getgen_en(0,126)},{getgen_en(0,255)},{getgen_en(0,300)});")

def test_text(): # tinytext,mediumtext,text,longtext
	name,ddl = _ft('text')
	ddl += """(
	id int,
	c_tinytext tinytext,
	c_mediumtext mediumtext,
	c_text text,
	c_longtext longtext
) engine=innodb;
"""
	print(ddl)
	for i in range(2):
		#print(f"insert into {name} values({i},{getgen_en(0,127)},{getgen_en(0,8388607)},{getgen_en(0,8388607)},{getgen_en(0,8388607)});")
		print(f"insert into {name} values({i},{getgen_en(0,127)},{getgen_en(0,127)},{getgen_en(0,255)},{getgen_en(0,255)});")

def test_blob(): # tinyblob,mediumblob,blob,longblob
	name,ddl = _ft('blob')
	ddl += """(
	id int,
	c_tinyblob tinyblob,
	c_mediumblob mediumblob,
	c_blob blob,
	c_longblob longblob
) engine=innodb;
"""
	print(ddl)
	for i in range(200):
		#print(f"insert into {name} values({i},{getgen_en(0,127)},{getgen_en(0,8388607)},{getgen_en(0,8388607)},{getgen_en(0,8388607)});")
		print(f"insert into {name} values({i},{getgen_en(0,127)},{getgen_en(0,127)},{getgen_en(0,255)},{getgen_en(0,255)});")

def test_binary(): # binary,varbinary,bit
	name,ddl = _ft('binary')
	ddl += """(
	id int,
	c_binary_01 binary(20),
	c_binary_02 binary(127),
	c_binary_03 binary(255),
	c_varbinary_01 varbinary(20),
	c_varbinary_02 varbinary(127),
	c_varbinary_03 varbinary(300),
	c_bit_01 bit(20),
	c_bit_02 bit(31),
	c_bit_03 bit(64)
) engine=innodb;
"""
	print(ddl)
	for i in range(200):
		print(f"insert into {name} values({i},{getgen_en(0,20)},{getgen_en(0,127)},{getgen_en(0,255)},{getgen_en(0,20)},{getgen_en(0,127)},{getgen_en(0,300)},{getgen_en(0,2)},{getgen_en(0,3)},{getgen_en(0,8)});")

def test_set(): # enum,set
	name,ddl = _ft('set')
	ddl += """(
	id int,
	c_set set('X','Y','Z'),
	c_enum enum('A','B','C')
) engine=innodb;
"""
	print(ddl)
	for i in range(200):
		print(f"insert into {name} values({i},{getgen_int(0,3)},{repr(random.choice(('A','B','C')))} );")

def test_time(): # date,time,datetime,timestamp,year
	name,ddl = _ft('time')
	ddl += """(
	id int,
	c_date date,
	c_time time,
	c_datetime datetime,
	c_timestamp timestamp, 
	c_year year 
) engine=innodb;
"""
	print(ddl)
	for i in range(20):
		print(f"insert into {name} values({i},{getgen_date()},{getgen_time()},{getgen_datetime()},{getgen_datetime()},{getgen_int(1901,2025)});")

def test_json(): # json
	name,ddl = _ft('json')
	ddl += """(
	id int,
	c_json json
) engine=innodb;
"""
	print(ddl)
	for i in range(200):
		print(f"insert into {name} values({i},{repr(json.dumps(getgen_json()))});")

def test_spatial(): # geometry,point,linestring,polygon,multipoint,multilinestring,multipolygon,geometrycollection
	name,ddl = _ft('spatial')
	ddl += """(
	id int,
	c_geometry geometry,
	c_point point /*!80003 SRID 4326 */,
	c_linestring linestring,
	c_polygon polygon,
	c_geometrycollection geometrycollection,
	c_multipoint multipoint,
	c_multilinestring multilinestring,
	c_multipolygon multipolygon
) engine=innodb;
"""
	print(ddl)
	for x in range(2):
		print(f"insert into {name} values({x},ST_GeomFromText('point({x} {x})'), ST_GeomFromText('point({x} {x})', 4326), ST_GeomFromText('linestring({x} {x}, {x} {x}, {x} {x}, {x} {x})'), ST_GeomFromText('polygon((0 0,0 3,3 3,3 0,0 0),(1 1,1 2,2 2,2 1,1 1))'), ST_GeomFromText('GeometryCollection(Point(1 1),LineString(2 2, 3 3))'), ST_GeomFromText('MULTIPOINT((60 -24),(28 -77))'),  ST_GeomFromText('MultiLineString((1 1,2 2,3 3),(4 4,5 5))'), ST_GeomFromText('MultiPolygon(((0 0,0 3,3 3,3 0,0 0),(1 1,1 2,2 2,2 1,1 1)))') );")

def test_vector(): # vector
	name,ddl = _ft('vector')
	ddl += """(
	id int,
	c_vector vector
) engine=innodb;
"""
	print(ddl)
	for x in range(200):
		print(f"insert into {name} values({x},TO_VECTOR('[{x},{x}]'));")

def test_instant(): # add column
	name,ddl = _ft('instant')
	ddl += """(
	id int,
	name varchar(20)
) engine=innodb;
"""
	print(ddl)
	for x in range(200):
		print(f"insert into {name} values({x},{getgen_en(0,20)});")
	print(f'ALTER TABLE {name} ADD COLUMN test varchar(20),ALGORITHM=INSTANT;')
	for x in range(200):
		print(f"insert into {name} values({x},{getgen_en(0,20)},{getgen_en(0,20)});")

def test_row_version(): # add/drop column
	name,ddl = _ft('row_version')
	ddl += """(
	id int,
	name varchar(20)
) engine=innodb;
"""
	print(ddl)
	for x in range(200):
		print(f"insert into {name} values({x},{getgen_en(0,20)});")
	print(f'ALTER TABLE {name} ADD COLUMN test varchar(20),ALGORITHM=INSTANT;')
	for x in range(200):
		print(f"insert into {name} values({x},{getgen_en(0,20)},{getgen_en(0,20)});")
	print(f'ALTER TABLE {name} DROP COLUMN name,ALGORITHM=INSTANT;')
	for x in range(200):
		print(f"insert into {name} values({x},{getgen_en(0,20)});")

def test_partition(): # partition
	# range
	name,ddl = _ft('partition_range')
	ddl += """(id int,name varchar(200)) engine=innodb PARTITION BY RANGE (id) (PARTITION p0 VALUES LESS THAN (10), PARTITION p1 VALUES LESS THAN (100), PARTITION p2 VALUES LESS THAN (200),PARTITION p3 VALUES LESS THAN (10000));"""
	print(ddl)
	for x in range(200):
		print(f"insert into {name} values({x},{getgen_int(0,10000)});")

	# hash
	name,ddl = _ft('partition_hash')
	ddl += """(id int, name varchar(200), age_y datetime) engine=innodb PARTITION BY HASH (year(age_y)) partitions 4 ;"""
	print(ddl)
	for x in range(200):
		print(f"insert into {name} values({x},{getgen_en()},{getgen_datetime()});")

	# list
	name,ddl = _ft('partition_list')
	ddl += """(id int, aa varchar(200)) engine=innodb PARTITION BY list(id)(PARTITION p1 VALUES IN (0,1,2,3,4), PARTITION p2 VALUES IN (5,6,7,8) );"""
	print(ddl)
	for x in range(8):
		print(f"insert into {name} values({x},{getgen_en()});")

	# key
	name,ddl = _ft('partition_key')
	ddl += """(id int primary key, aa varchar(200)) engine=innodb PARTITION BY KEY() PARTITIONS 2;"""
	print(ddl)
	for x in range(200):
		print(f"insert into {name} values({x},{getgen_en()});")

def test_subpartition(): # subpartition
	name,ddl = _ft('sub_partition_rangehash')
	ddl += """(id INT, purchased DATE) engine=innodb
    PARTITION BY RANGE( YEAR(purchased) )
    SUBPARTITION BY HASH( TO_DAYS(purchased) )
    SUBPARTITIONS 2 (
        PARTITION p0 VALUES LESS THAN (1990),
        PARTITION p1 VALUES LESS THAN (2000),
        PARTITION p2 VALUES LESS THAN MAXVALUE
    );"""
	print(ddl)
	for x in range(200):
		print(f"insert into {name} values({x},{getgen_date()});")


def test_char_maxlen1(): # char&latin1
	name,ddl = _ft('char_maxlen1')
	ddl += """(id int, name varchar(200)) engine=innodb default charset=latin1;"""
	print(ddl)
	for x in range(200):
		print(f"insert into {name} values({x},{getgen_en()});")

def test_char_emoji(): # emoji
	name,ddl = _ft('char_emoji')
	ddl += """(id int, name varchar(200)) engine=innodb default charset=utf8mb4;"""
	print(ddl)
	for x in range(200):
		print(f"insert into {name} values({x},{getgen_emoji()});")

def test_foreign_key(): # CONSTRAINT FOREIGN KEY
	pass

def test_check(): # CONSTRAINT CHECK
	pass

def test_gen(): # GENERATED ALWAYS VIRTUAL/STORED
	pass

def test_ddl_pk(): # primary key
	pass

def test_ddl_unique_key(): # unique key
	pass

def test_ddl_key(): # key
	pass

def test_ddl_spatial_key(): # spatial key
	pass

def test_ddl_pre_key(): # pre-key
	pass

def test_ddl_comp_key(): # key(id,name)
	pass

def test_ddl_comp_pre_key(): # key(id,name(20))
	pass

def test_ddl_fulltext_key(): # fulltext
	pass

def test_ddl_invisible(): # key(col) INVISIBLE
	pass

def test_on_update(): # on update
	pass

def test_hentai_ddl():
	ddl = """
create table if not exists test_ibd2sql_ddl_00(
	id bigint unsigned not null primary key auto_increment,
  	name varchar(200)
);

create table if not exists test_ibd2sql_ddl_01(
  `id` serial primary key auto_increment, -- serial: bigint unsigned not null
  `id_default` int default 0,
  `id_unsigned_zerofill` int unsigned zerofill,
  `int_col` int DEFAULT NULL,
  `id_invisible` int /*!80023 INVISIBLE */,
  `tinyint_col` tinyint DEFAULT '1',
  `boolean_col` boolean, -- tinyint(1)
  `smallint_col` smallint DEFAULT NULL,
  `mediumint_col` mediumint DEFAULT NULL,
  `bigint_col` bigint DEFAULT NULL,
  `float_col` float DEFAULT NULL,
  `double_col` double DEFAULT NULL,
  `decimal_col` decimal(10,2) DEFAULT NULL,
  `date_col` date DEFAULT NULL,
  `datetime_col` datetime(6),
  `timestamp_col` timestamp DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
  `time_col` time(4) DEFAULT NULL,
  `year_col` year DEFAULT NULL,
  `char_col` char(100) CHARACTER SET utf8 COLLATE utf8_danish_ci DEFAULT NULL,
  `nchar_col` nchar(10), -- 同char(10)
  `varchar_col` varchar(100),
  `nvarchar_col` nvarchar(10), -- 同nvarchar(10)
  `binary_col` binary(10) DEFAULT NULL,
  `varbinary_col` varbinary(20) DEFAULT NULL,
  `bit_col` bit(4) DEFAULT NULL,
  `enum_col` enum('A','B','C'),
  `set_col` set('X','Y','Z'),
  `json_type_col` json DEFAULT NULL,
  `tinyblob_col` tinyblob,
  `mediumblob_col` mediumblob,
  `blob_col` blob,
  `longblob_col` longblob,
  `tinytext_col` tinytext,
  `mediumtext_col` mediumtext,
  `text_col` text,
  `longtext_col` longtext,
  `gen_stored` INT GENERATED ALWAYS AS (int_col + 1) STORED,
  `gen_virtual` INT GENERATED ALWAYS AS (id_default + 1) virtual,
  `spatial_geometry` geometry,
  `spatial_point` point not null /*!80003 SRID 4326 */,
  `spatial_linestring` linestring,
  `spatial_polygon` polygon,
  `spatial_geometrycollection` geometrycollection,
  `spatial_multipoint` multipoint,
  `spatial_multilinestring` multilinestring,
  `spatial_multipolygon` multipolygon,
  `concat_char` varchar(201) as (concat(char_col,' ',varchar_col)),
  unique key(int_col),
  key(bigint_col),
  key(concat_char),
  key(varchar_col desc),
  key(int_col,time_col),
  key(int_col) /*!80000 INVISIBLE */,
  fulltext(varchar_col,text_col),
  spatial index(spatial_point),
  check (int_col>0 and tinyint_col>0),
  foreign key(id) references test_ibd2sql_ddl_00(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""
	print(ddl)

def test_1000_column():
	ddl = 'drop table if exists test_ibd2sql_ddl_1000;create table if not exists test_ibd2sql_ddl_1000( id int'
	for i in range(1000):
		ddl += f",c{i} varchar(1) null default 'a'"
	ddl += ");"
	print(ddl)

if __name__ == '__main__':
	MYSQL_VERSION_ID = int(sys.argv[1]) if len(sys.argv) == 2 else 0
	test_int()
	test_char()
	test_set()
	test_time()
	test_char_maxlen1()
	test_1000_column()
	#test_text()
	#test_blob()
	#test_binary()
	#if MYSQL_VERSION_ID >= 50708:
	#	test_json()
	#if MYSQL_VERSION_ID >= 50706:
	#	test_spatial()
	if MYSQL_VERSION_ID >= 50719:
		test_partition()
	if MYSQL_VERSION_ID >= 90001:
		test_vector()
	if MYSQL_VERSION_ID >= 80013 and MYSQL_VERSION_ID <= 80028:
		test_instant()
	if MYSQL_VERSION_ID > 80028:
		test_row_version()
	if MYSQL_VERSION_ID >= 80028:
		test_hentai_ddl()
		test_char_emoji()
		test_subpartition()
