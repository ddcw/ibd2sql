#!/usr/bin/env python3
#为了方便我的环境测试, 我是直接写死路径和数据库名字的. 使用的时候需要注意下
#python getsql.py > xxx.sql #生成数据
#mysql -Dibd2sql < xxx.sql  #导入数据
#python getsql.py 1 > t.sh  #生成测试脚本
#sh t.sh                    #测试
import random
import json
from datetime import datetime, timedelta
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
import sys

def get_json():
	aa = {"aa":"c","bb":{"dd":1}}
	return json.dumps(aa)

#生成随机整数
def get_int(start=-10000,stop=10000):
	return random.randint(start,stop)

#生成随机datetime
def get_datetime(start="1995-01-01 0:0:0",stop="2024-12-30 0:0:0"):
	start = datetime.strptime(start, DATE_FORMAT)
	stop = datetime.strptime(stop, DATE_FORMAT)
	rangesecond = int((stop - start).total_seconds())
	return str(start + timedelta(seconds=random.randint(0,rangesecond)))

#生成随机中文
def get_zh(start=1,stop=40):
	return "测试中文"
	return ''.join(chr(random.randint(0x4E00, 0x9FFF)) for _ in range(random.randint(start,stop)))
		
#生成随机英文
def get_en(start=4,stop=100):
	strings = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
	return ''.join(random.choice(strings) for _ in range(random.randint(start,stop)))

#生成随机表情(就79个,其它的表情懒得找)
def get_emoji(start=1,stop=100):
	return ''.join(chr(random.randint(0x1F600, 0x1F64F)) for _ in range(random.randint(start,stop)))

def getgen_custom(start,stop):
	while True:
		yield ''.join(chr(random.randint(start[0], start[1])) for _ in range(random.randint(stop[0],stop[1])))

def getgen_range(start,step):
	while True:
		yield start
		start += step



if len(sys.argv) == 1:
	#初始化数据
	print("use ibd2sql;")
	#全数据类型的表 和 相关数据
	print("drop table if exists ddcw_alltype_table;")
	tb = """create table if not exists ddcw_alltype_table(
	  `id` int primary key AUTO_INCREMENT,
	  `int_col` int DEFAULT NULL,
	  `tinyint_col` tinyint DEFAULT '1',
	  `smallint_col` smallint DEFAULT NULL,
	  `mediumint_col` mediumint DEFAULT NULL,
	  `bigint_col` bigint DEFAULT NULL,
	  `float_col` float DEFAULT NULL,
	  `double_col` double DEFAULT NULL,
	  `decimal_col` decimal(10,2) DEFAULT NULL,
	  `date_col` date DEFAULT NULL,
	  `datetime_col` datetime DEFAULT NULL,
	  `timestamp_col` timestamp NULL DEFAULT NULL,
	  `time_col` time DEFAULT NULL,
	  `year_col` year DEFAULT NULL,
	  `char_col` char(100) DEFAULT NULL,
	  `varchar_col` varchar(100) DEFAULT NULL,
	  `binary_col` binary(10) DEFAULT NULL,
	  `varbinary_col` varbinary(20) DEFAULT NULL,
	  `bit_col` bit(4) DEFAULT NULL,
	  `enum_col` enum('A','B','C') DEFAULT NULL,
	  `set_col` set('X','Y','Z') DEFAULT NULL,
	  `josn_type` json);"""
	print(tb)
	
	for x in range(1,10000):
		sql = f"""insert into ddcw_alltype_table values({x},{get_int(-1000000,10000000)},{get_int(-126,126)},{get_int()},{get_int()},{get_int()},{get_int()},{get_int()},{get_int()},'{str(get_datetime()).split()[0]}','{str(get_datetime())}','{str(get_datetime())}','{str(get_datetime()).split()[1]}',{get_int(1990,2025)},'{get_en()}','{get_en()}',{get_int(10,100)},{get_int(10,100)},1,{get_int(1,2)},{get_int(1,2)},'{get_json()}');"""
		print(sql)
	
	
	#ONLINE DDL的表
	print("drop table if exists ddcw_instant_new_col;")
	print("create table if not exists ddcw_instant_new_col(id int, aa varchar(200));")
	for x in range(1,1000):
		print(f"insert into ddcw_instant_new_col values({x},'{get_en()}');")
	print("alter table ddcw_instant_new_col add new_col varchar(200) default 'ddcw';")
	print(f"insert into ddcw_instant_new_col values(123456,'{get_en()}',null);")
	for x in range(1001,1010):
		print(f"insert into ddcw_instant_new_col values({x},'{get_en()}','{get_en()}');")
	print(f"insert into ddcw_instant_new_col values(12345678,'{get_en()}',null);")
	print("alter table ddcw_instant_new_col add new_col2 varchar(200) comment 'second new col';")
	print(f"insert into ddcw_instant_new_col values(12445679,'{get_en()}','ddcw',null);")
	for x in range(1011,1021):
		print(f"insert into ddcw_instant_new_col values({x},'{get_en()}','{get_en()}','{get_en()}');")
	print(f"insert into ddcw_instant_new_col values(12345680,'{get_en()}',null,null);")
	
	
	#分区表
	#range
	print("drop table if exists ddcw_partition_range;")
	dt = """create table if not exists ddcw_partition_range(id int, name varchar(200)) PARTITION BY RANGE (id) (PARTITION p0 VALUES LESS THAN (10), PARTITION p1 VALUES LESS THAN (100), PARTITION p2 VALUES LESS THAN (200),PARTITION p3 VALUES LESS THAN (10000));"""
	print(dt)
	for x in range(1,1000):
		print(f"insert into ddcw_partition_range values({x},'{get_en()}');")
	
	
	#hash
	print("drop table if exists ddcw_partition_hash;")
	dt = """create table if not exists ddcw_partition_hash(id int, name varchar(200), age_y datetime) PARTITION BY HASH (year(age_y)) partitions 4  ;"""
	print(dt)
	for x in range(1,1000):
		print(f"insert into ddcw_partition_hash values({x},'{get_en()}','{str(get_datetime())}');")
	
	#list
	print("drop table if exists ddcw_partition_list;")
	dt = """create table if not exists ddcw_partition_list(id int, name varchar(200)) PARTITION BY list(id) (PARTITION p1 VALUES IN (1,2,3,4), PARTITION p2 VALUES IN (5,6,7,8) );"""
	print(dt)
	for x in range(1,8):
		print(f"insert into ddcw_partition_list values({x},'{get_en()}');")
	
	#key
	print("drop table if exists ddcw_partition_key;")
	dt = """create table if not exists ddcw_partition_key(id int primary key, name varchar(200)) PARTITION BY KEY() PARTITIONS 2;"""
	print(dt)
	for x in range(1,4):
		print(f"insert into ddcw_partition_key values({x},'{get_en()}');")

	#LOB
	print("drop table if exists ddcw_blob7;")
	dt = """create table if not exists ddcw_blob7(id int, c_lb longblob, c_lt longtext, c_ml mediumblob, c_mb mediumtext, c_t text, c_b blob, c_tb tinyblob, c_tt tinytext);"""
	print(dt)
	for x in range(1,300):
		print(f"insert into ddcw_blob7 values({x},'{get_zh()}{get_en(20,1000)}','{get_zh()}{get_en(20,1000)}','{get_zh()}{get_en(20,100)}','{get_zh()}{get_en(20,100)}','{get_zh()}{get_en(20,100)}','{get_zh()}{get_en(20,100)}','{get_zh()}{get_en(2,10)}','{get_zh()}{get_en(2,10)}');")
	
else:
	#print("parse data")
	t = """
#解析数据
python main.py /data/mysql_3314/mysqldata/ibd2sql/ddcw_alltype_table.ibd --sql --ddl --schema ibd2sql2 > /tmp/testibd2sql_alltype_table.sql
python main.py /data/mysql_3314/mysqldata/ibd2sql/ddcw_instant_new_col.ibd --sql --ddl --schema ibd2sql2 > /tmp/testibd2sql_instant_new_col.sql
python main.py /data/mysql_3314/mysqldata/ibd2sql/ddcw_partition_key#p#p0.ibd   --schema ibd2sql2 --ddl --sql > /tmp/testibd2sql_pt_key.sql
python main.py /data/mysql_3314/mysqldata/ibd2sql/ddcw_partition_key#p#p1.ibd   --schema ibd2sql2 --sql --sdi-table /data/mysql_3314/mysqldata/ibd2sql/ddcw_partition_key#p#p0.ibd >> /tmp/testibd2sql_pt_key.sql
python main.py /data/mysql_3314/mysqldata/ibd2sql/ddcw_partition_hash#p#p0.ibd  --schema ibd2sql2 --ddl --sql > /tmp/testibd2sql_pt_hash.sql
python main.py /data/mysql_3314/mysqldata/ibd2sql/ddcw_partition_hash#p#p1.ibd  --schema ibd2sql2 --sql --sdi-table /data/mysql_3314/mysqldata/ibd2sql/ddcw_partition_hash#p#p0.ibd >> /tmp/testibd2sql_pt_hash.sql
python main.py /data/mysql_3314/mysqldata/ibd2sql/ddcw_partition_hash#p#p2.ibd  --schema ibd2sql2 --sql --sdi-table /data/mysql_3314/mysqldata/ibd2sql/ddcw_partition_hash#p#p0.ibd >> /tmp/testibd2sql_pt_hash.sql
python main.py /data/mysql_3314/mysqldata/ibd2sql/ddcw_partition_hash#p#p3.ibd  --schema ibd2sql2 --sql --sdi-table /data/mysql_3314/mysqldata/ibd2sql/ddcw_partition_hash#p#p0.ibd >> /tmp/testibd2sql_pt_hash.sql
python main.py /data/mysql_3314/mysqldata/ibd2sql/ddcw_partition_list#p#p1.ibd  --schema ibd2sql2 --ddl --sql > /tmp/testibd2sql_pt_list.sql
python main.py /data/mysql_3314/mysqldata/ibd2sql/ddcw_partition_list#p#p2.ibd  --schema ibd2sql2 --sql --sdi-table /data/mysql_3314/mysqldata/ibd2sql/ddcw_partition_list#p#p1.ibd >> /tmp/testibd2sql_pt_list.sql
python main.py /data/mysql_3314/mysqldata/ibd2sql/ddcw_partition_range#p#p0.ibd --schema ibd2sql2 --sql --ddl > /tmp/testibd2sql_pt_range.sql
python main.py /data/mysql_3314/mysqldata/ibd2sql/ddcw_partition_range#p#p1.ibd --schema ibd2sql2 --sql --sdi-table /data/mysql_3314/mysqldata/ibd2sql/ddcw_partition_range#p#p0.ibd >> /tmp/testibd2sql_pt_range.sql
python main.py /data/mysql_3314/mysqldata/ibd2sql/ddcw_partition_range#p#p2.ibd --schema ibd2sql2 --sql --sdi-table /data/mysql_3314/mysqldata/ibd2sql/ddcw_partition_range#p#p0.ibd >> /tmp/testibd2sql_pt_range.sql
python main.py /data/mysql_3314/mysqldata/ibd2sql/ddcw_partition_range#p#p3.ibd --schema ibd2sql2 --sql --sdi-table /data/mysql_3314/mysqldata/ibd2sql/ddcw_partition_range#p#p0.ibd >> /tmp/testibd2sql_pt_range.sql
python main.py /data/mysql_3314/mysqldata/ibd2sql/ddcw_blob7.ibd --schema ibd2sql2 --sql --ddl > /tmp/testibd2sql_blob.sql

#清空环境
mysql -h127.0.0.1 -P3314 -p123456 -e 'drop database ibd2sql2;'
mysql -h127.0.0.1 -P3314 -p123456 -e 'create database ibd2sql2;'
	
#导入数据
mysql -h127.0.0.1 -P3314 -p123456 < /tmp/testibd2sql_alltype_table.sql
mysql -h127.0.0.1 -P3314 -p123456 < /tmp/testibd2sql_instant_new_col.sql
mysql -h127.0.0.1 -P3314 -p123456 < /tmp/testibd2sql_pt_key.sql
mysql -h127.0.0.1 -P3314 -p123456 < /tmp/testibd2sql_pt_hash.sql
mysql -h127.0.0.1 -P3314 -p123456 < /tmp/testibd2sql_pt_list.sql
mysql -h127.0.0.1 -P3314 -p123456 < /tmp/testibd2sql_pt_range.sql
mysql -h127.0.0.1 -P3314 -p123456 < /tmp/testibd2sql_blob.sql


#校验数据
mysql -h127.0.0.1 -P3314 -p123456 -e 'checksum table ibd2sql.ddcw_alltype_table, ibd2sql2.ddcw_alltype_table;'
mysql -h127.0.0.1 -P3314 -p123456 -e 'checksum table ibd2sql.ddcw_instant_new_col, ibd2sql2.ddcw_instant_new_col;'
mysql -h127.0.0.1 -P3314 -p123456 -e 'checksum table ibd2sql.ddcw_partition_hash, ibd2sql2.ddcw_partition_hash;'
mysql -h127.0.0.1 -P3314 -p123456 -e 'checksum table ibd2sql.ddcw_partition_key, ibd2sql2.ddcw_partition_key;'
mysql -h127.0.0.1 -P3314 -p123456 -e 'checksum table ibd2sql.ddcw_partition_list, ibd2sql2.ddcw_partition_list;'
mysql -h127.0.0.1 -P3314 -p123456 -e 'checksum table ibd2sql.ddcw_partition_range, ibd2sql2.ddcw_partition_range;'
mysql -h127.0.0.1 -P3314 -p123456 -e 'checksum table ibd2sql.ddcw_blob7, ibd2sql2.ddcw_blob7;'
	"""
	print(t)
