#!/usr/bin/env bash
# write by ddcw @https://github.com/ddcw
# 本脚本为 测试ibd2sql的工具.

# 参数:
# 原始数据库, 即需要测试的数据库
MYSQLBIN1="mysql -h127.0.0.1 -P3374 -p123456 -uroot"
MYSQLDB1="ibd2sql_t1"
SERVER="root:123456@127.0.0.1:3308" #不知道字符集, 就没法生成表结构... 

# 目标数据库, 即解析后的数据存放目录
MYSQLBIN2="mysql -h127.0.0.1 -P3374 -p123456 -uroot"
MYSQLDB2="ibd2sql_t2"

# 中间数据库, 如果是Mysql 5.7则需要使用mysqlfrm解析表结构并插入中间库, 方便获取sdi信息
# 必须是8.0 仅原始数据库为5.7的时候需要
MYSQLBIN3="mysql -h127.0.0.1 -P3314 -p123456 -uroot"
MYSQLDB3="ibd2sql_t3"

# 输出格式:
# NO            DESCRIPTION     CHECKSUM1       CHECKSUM2    STATUS
# 1             VARCHAR         2286445522      2286445522   PASS

export RESULT1=""
RUNSQL1(){
	RESULT1=`echo "${1}" | ${MYSQLBIN1} -NB -D${MYSQLDB1} 2>/dev/null`
}
export RESULT2=""
RUNSQL2(){
	RESULT2=`echo "${1}" | ${MYSQLBIN2} -NB -D${MYSQLDB2} 2>/dev/null`
}
export RESULT3=""
RUNSQL3(){
	RESULT3=`echo "${1}" | ${MYSQLBIN3} -NB -D${MYSQLDB2} 2>/dev/null`
}
export MYSQL_VERSION1=""
export MYSQL_VERSION2=""
export DATADIR1=""
export DATADIR2=""
export ISMYSQL5=false

exit1(){
	echo -e "$@"
	exit 1
}

export HASH1_LIST=""
add_sha1(){
	HASH1_LIST="${HASH1_LIST} ${1}"
}

export CRC32_LIST=""
add_crc32(){
	export CRC32_LIST="${CRC32_LIST} ${1}"
}

# 测试MYSQL连接性
if ${MYSQLBIN1} -NB -D${MYSQLDB1} -e "select 1+1;" >/dev/null 2>&1;then
	RUNSQL1 "select @@version;"
	MYSQL_VERSION1=${RESULT1}
	echo "测试库: MYSQL VERSION ${MYSQL_VERSION1}"
	RUNSQL1 "select @@datadir;"
	DATADIR1=${RESULT1}
else
	exit1 "MYSQLBIN1 MYSQL SOURCE cant connect"
fi
if ${MYSQLBIN2} -NB -D${MYSQLDB2} -e "select 1+1;" >/dev/null 2>&1;then
	RUNSQL2 "select @@version;"
	MYSQL_VERSION2=${RESULT2}
	echo "目标库: MYSQL VERSION ${MYSQL_VERSION2}"
	RUNSQL2 "select @@datadir;"
	DATADIR2=${RESULT2}
else
	exit1 "MYSQLBIN2 MYSQL DEST cant connect"
fi
export MYSQL_VERSION3=""
if [ "${MYSQL_VERSION1::1}" == "5" ];then
	if ${MYSQLBIN3} -NB -D${MYSQLDB3} -e "select 1+1;" >/dev/null 2>&1;then
		RUNSQL3 "select @@version;"
		MYSQL_VERSION3=${RESULT3}
		echo "中间库: MYSQL VERSION ${MYSQL_VERSION3}"
		if [ "${MYSQL_VERSION3::1}" != "8" ];then
			exit1 "中间库的版本需要为 8.x MYSQLBIN3"
		fi
		RUNSQL3 "select @@datadir;"
		DATADIR3=${RESULT3}
		ISMYSQL5=true
	else
		exit1 "需要中间库 MYSQLBIN3"
	fi
fi

#解析数据, 并导入到mysqlbin2库
test1(){
	name=$1
	sha1=$2
	comm="python3 main.py "
	RUNSQL1 "flush tables;"
	RUNSQL2 "drop table if exists ${name}"
	tmpfile="/tmp/.ddcw_test_ibd2sql.sql" #保存SQL的文件, 管道符有点问题...
	#sleep 5 # 等表同步到磁盘, 时间短了, 可能数据未落盘.
	# 判断是否为分区表.
	ISPARTITION=false
	FIRSTPARITION_NAME=""
	mysqlflag="p"
	if $ISMYSQL5;then
		mysqlflag="P"
	fi
	if [ `ls ${DATADIR1}/${MYSQLDB1}/${name}#P#*.ibd 2>/dev/null | wc -l` -gt 0 ];then
		mysqlflag="P"
	fi
	if [ `ls ${DATADIR1}/${MYSQLDB1}/${name}#${mysqlflag}#*.ibd 2>/dev/null | wc -l` -gt 0 ];then
		ISPARTITION=true
		for filename in `ls ${DATADIR1}/${MYSQLDB1}/${name}#${mysqlflag}#*.ibd`;do
			${comm} --ddl ${filename} >/dev/null 2>&1 && FIRSTPARITION_NAME=${filename##*/}
		done
	fi
	
	if $ISMYSQL5;then
		mysqlflag="P"
		mysqlfrm --server=${SERVER} --diagnostic ${DATADIR1}/${MYSQLDB1}/${name}.frm 2>/dev/null |grep -v '^WARNING: ' | grep -v '^#' | sed "s/\`${MYSQLDB1}\`/\`${MYSQLDB3}\`/" | sed 's/, DEFAULT CHARSET=utf8//g' | ${MYSQLBIN3} -NB -D${MYSQLDB3} >/dev/null 2>&1
		mysqlfrm --server=${SERVER} --diagnostic ${DATADIR1}/${MYSQLDB1}/${name}.frm 2>/dev/null |grep -v '^WARNING: ' | grep -v '^#' | sed "s/\`${MYSQLDB1}\`/\`${MYSQLDB2}\`/" | sed 's/, DEFAULT CHARSET=utf8//g' | ${MYSQLBIN2} -NB -D${MYSQLDB2} >/dev/null 2>&1
		if [ `ls ${DATADIR3}/${MYSQLDB3}/${name}#${mysqlflag}#*.ibd 2>/dev/null | wc -l` -gt 0 ];then
			ISPARTITION=true
			for filename in `ls ${DATADIR3}/${MYSQLDB3}/${name}#${mysqlflag}#*.ibd`;do
				${comm} --ddl ${filename} >/dev/null 2>&1 && FIRSTPARITION_NAME=${filename##*/}
			done
		fi
		if ${ISPARTITION};then
			comm="${comm} --mysql5 --sdi-table ${DATADIR3}/${MYSQLDB3}/${FIRSTPARITION_NAME}"
		else
			comm="${comm} --mysql5 --sdi-table ${DATADIR3}/${MYSQLDB3}/${name}.ibd"
		fi
	else
		if ${ISPARTITION};then
			${comm} --ddl ${DATADIR1}/${MYSQLDB1}/${FIRSTPARITION_NAME} --table ${name} --schema ${MYSQLDB2} 2>/dev/null | ${MYSQLBIN2} -NB -D${MYSQLDB2} >/dev/null 2>&1
			comm="${comm} --sdi-table ${DATADIR1}/${MYSQLDB1}/${FIRSTPARITION_NAME}"
		else
			${comm} --ddl ${DATADIR1}/${MYSQLDB1}/${name}.ibd --table ${name} --schema ${MYSQLDB2} 2>/dev/null | ${MYSQLBIN2} -NB -D${MYSQLDB2} >/dev/null 2>&1
			comm="${comm} --ddl "
		fi
	fi

	# 解析数据
	if ${ISPARTITION};then
		if [ `ls ${DATADIR1}/${MYSQLDB1}/${name}#p#*.ibd 2>/dev/null | wc -l` -gt 0 ];then
			mysqlflag="p"
		elif [ `ls ${DATADIR1}/${MYSQLDB1}/${name}#P#*.ibd 2>/dev/null | wc -l` -gt 0 ];then
			mysqlflag="P"
		fi
		for filename in `ls ${DATADIR1}/${MYSQLDB1}/${name}#${mysqlflag}#*.ibd`;do
			${comm} --sql ${filename} --table ${name} --schema ${MYSQLDB2} 2>/dev/null | ${MYSQLBIN2} -NB -D${MYSQLDB2} >/dev/null 2>&1
		done
	else
		${comm} --sql ${DATADIR1}/${MYSQLDB1}/${name}.ibd --table ${name} --schema ${MYSQLDB2} 2>/dev/null | ${MYSQLBIN2} -NB -D${MYSQLDB2} >/dev/null 2>&1
	fi

	# 校验数据
	#RUNSQL1 "flush tables;"
	#RUNSQL2 "flush tables;"
	#sleep 5 # 等表同步到磁盘
	if [ "${sha1}" == "" ];then
		RUNSQL1 "checksum table ${name};"
		RUNSQL2 "checksum table ${name};"
	else
		#其实还是使用的crc32, 方便展示
		#RUNSQL1 "set session group_concat_max_len=102400000000;select crc32(group_concat(id,aa,bb)) from ${name}"
		#RUNSQL2 "set session group_concat_max_len=102400000000;select crc32(group_concat(id,aa,bb)) from ${name}"
		RUNSQL1 "select concat('select crc32(group_concat(concat(',group_concat(COLUMN_NAME),'))) from ${name}') from information_schema.columns where table_name='${name}' and table_schema='${MYSQLDB1}';"
		RUNSQL1 "${RESULT1}"
		RUNSQL2 "select concat('select crc32(group_concat(concat(',group_concat(COLUMN_NAME),'))) from ${name}') from information_schema.columns where table_name='${name}' and table_schema='${MYSQLDB2}';"
		RUNSQL2 "${RESULT2}"
	fi
	printf1 ${name} `echo ${RESULT1} | awk '{print $NF}'` `echo ${RESULT2} | awk '{print $NF}'`
	
}

export NUMBER=0
export INCONSISTENT=0 #记录不一致的数据量
printf1(){
	NUMBER=$[ ${NUMBER} + 1 ]
	if [ "${2}" == "${3}" ];then
		STATUS="PASS"
	else
		STATUS="FAILD"
		INCONSISTENT=$[ ${INCONSISTENT} + 1 ]
	fi
	printf "%-3s\t%-20s\t%-10s\t%-10s\t%-10s\n" ${NUMBER} $1 $2 $3 ${STATUS}
}
#printf1 VARCHAR         2286445522      2286445522   



test_varchar(){
	# varchar
	RUNSQL1 "drop table if exists ddcw_test_varchar_500;"
	RUNSQL1 "create table if not exists ddcw_test_varchar_500(id int , aa varchar(500));"
	RUNSQL1 "insert into ddcw_test_varchar_500 values(1,repeat('x', 127));"
	RUNSQL1 "insert into ddcw_test_varchar_500 values(2,repeat('x', 255));"
	RUNSQL1 "insert into ddcw_test_varchar_500 values(3,repeat('x', 499));"
	RUNSQL1 "insert into ddcw_test_varchar_500 values(4,repeat('x', 500));"
	RUNSQL1 "insert into ddcw_test_varchar_500 values(5,null);"
	RUNSQL1 "insert into ddcw_test_varchar_500 values(5,'');"
	#test1 ddcw_test_varchar_500
	add_crc32 ddcw_test_varchar_500


	# char
	RUNSQL1 "drop table if exists ddcw_test_char;"
	RUNSQL1 "create table if not exists ddcw_test_char(id int, aa char(127), bb char(255));"
	RUNSQL1 "insert into ddcw_test_char values(1,repeat('x', 127),repeat('x', 255))"
	RUNSQL1 "insert into ddcw_test_char values(2,'x','x')"
	RUNSQL1 "insert into ddcw_test_char values(3,null,'null')"
	RUNSQL1 "insert into ddcw_test_char values(4,null,null)"
	RUNSQL1 "insert into ddcw_test_char values(5,'null',null)"
	RUNSQL1 "insert into ddcw_test_char values(6,'','')"
	add_crc32 ddcw_test_char

	# set
	RUNSQL1 "drop table if exists ddcw_test_set;"
	RUNSQL1 "create table if not exists ddcw_test_set(id int, aa set('a','b'))"
	RUNSQL1 "insert into ddcw_test_set values(1,'a')"
	RUNSQL1 "insert into ddcw_test_set values(2,'b')"
	RUNSQL1 "insert into ddcw_test_set values(3,null)"
	RUNSQL1 "insert into ddcw_test_set values(4,'a,b')"
	RUNSQL1 "insert into ddcw_test_set values(4,'')"
	add_crc32 ddcw_test_set

	# enum
	RUNSQL1 "drop table if exists ddcw_test_enum;"
	RUNSQL1 "create table if not exists ddcw_test_enum(id int, aa enum('a','b','c'))"
	RUNSQL1 "insert into  ddcw_test_enum values(1,'a')"
	RUNSQL1 "insert into  ddcw_test_enum values(2,'b')"
	RUNSQL1 "insert into  ddcw_test_enum values(3,null)"
	RUNSQL1 "insert into  ddcw_test_enum values(3,'')"
	add_crc32 ddcw_test_enum


	# 8.0
	if ${ISMYSQL5};then
		echo "This is not MYSQL 8.x, skip binary/bigvarchar/blob/json/geom"
		return 0
	fi

	# binary
	RUNSQL1 "drop table if exists ddcw_test_binary;"
	RUNSQL1 "create table if not exists ddcw_test_binary(id int, aa binary(255))"
	RUNSQL1 "insert into ddcw_test_binary values(1,repeat('x', 127))"
	RUNSQL1 "insert into ddcw_test_binary values(2,repeat('x', 255))"
	RUNSQL1 "insert into ddcw_test_binary values(3,null)"
	RUNSQL1 "insert into ddcw_test_binary values(4,'')"
	add_crc32 ddcw_test_binary

	# varbinary
	RUNSQL1 "drop table if exists ddcw_test_varbinary;"
	RUNSQL1 "create table if not exists ddcw_test_varbinary(id int, aa varbinary(16000))"
	RUNSQL1 "insert into ddcw_test_varbinary values(1,repeat('x', 127))"
	RUNSQL1 "insert into ddcw_test_varbinary values(2,repeat('x', 16000))"
	RUNSQL1 "insert into ddcw_test_varbinary values(3,null)"
	RUNSQL1 "insert into ddcw_test_varbinary values(4,'')"
	add_crc32 ddcw_test_varbinary

	# varchar_extra
	RUNSQL1 "drop table if exists ddcw_test_varchar_16380;"
	RUNSQL1 "create table if not exists ddcw_test_varchar_16380(id int , aa varchar(16380));"
	RUNSQL1 "insert into ddcw_test_varchar_16380 values(1,repeat('x', 127));"
	RUNSQL1 "insert into ddcw_test_varchar_16380 values(2,repeat('x', 255));"
	RUNSQL1 "insert into ddcw_test_varchar_16380 values(3,repeat('x', 499));"
	RUNSQL1 "insert into ddcw_test_varchar_16380 values(4,repeat('x', 500));"
	RUNSQL1 "insert into ddcw_test_varchar_16380 values(4,repeat('x', 16380));"
	RUNSQL1 "insert into ddcw_test_varchar_16380 values(5,null);"
	RUNSQL1 "insert into ddcw_test_varchar_16380 values(6,'');"
	add_crc32 ddcw_test_varchar_16380

	# blob/text
	RUNSQL1 "drop table if exists ddcw_test_lob;"
	RUNSQL1 "create table if not exists ddcw_test_lob(id int, aa blob, bb longblob)"
	RUNSQL1 "insert into ddcw_test_lob values(1,'','')"
	RUNSQL1 "insert into ddcw_test_lob values(2,null,null)"
	RUNSQL1 "insert into ddcw_test_lob values(3,repeat('x', 32768),repeat('x', 1048576))"
	add_crc32 ddcw_test_lob

	# json
	RUNSQL1 "drop table if exists ddcw_test_json;"
	RUNSQL1 "create table if not exists ddcw_test_json(id int, aa json)"
	RUNSQL1 "insert into ddcw_test_json values(1,'')"
	RUNSQL1 "insert into ddcw_test_json values(2,'{\"aa\": \"c\", \"bb\": {\"dd\": 1}}')"
	RUNSQL1 "insert into ddcw_test_json values(1,null)"
	add_crc32 ddcw_test_json

	# geom
	RUNSQL1 "drop table if exists ddcw_test_geom;"
	RUNSQL1 "create table if not exists ddcw_test_geom(a geometry, b point SRID 4326, c linestring, d polygon, aa geometrycollection, bb multipoint, cc multilinestring, dd multipolygon);"
	for x in {1..100};do
		RUNSQL1 "insert into ddcw_test_geom values(ST_GeomFromText('point(${x} ${x})'), ST_GeomFromText('point(${x} ${x})', 4326), ST_GeomFromText('linestring(${x} ${x}, ${x} ${x}, ${x} ${x}, ${x} ${x})'), ST_GeomFromText('polygon((0 0,0 3,3 3,3 0,0 0),(1 1,1 2,2 2,2 1,1 1))'),  ST_GeomFromText('GeometryCollection(Point(1 1),LineString(2 2, 3 3))'), ST_GeomFromText('MULTIPOINT((60 -24),(28 -77))'),  ST_GeomFromText('MultiLineString((1 1,2 2,3 3),(4 4,5 5))'), ST_GeomFromText('MultiPolygon(((0 0,0 3,3 3,3 0,0 0),(1 1,1 2,2 2,2 1,1 1)))')   );"
	done
	add_crc32 ddcw_test_geom

}

test_int(){
	# tinyint
	RUNSQL1 "drop table if exists ddcw_test_tinyint;"
	RUNSQL1 "create table if not exists ddcw_test_tinyint(aa tinyint, bb tinyint unsigned);"
	RUNSQL1 "insert into ddcw_test_tinyint values(-127,0)"
	RUNSQL1 "insert into ddcw_test_tinyint values(-0,-0)"
	RUNSQL1 "insert into ddcw_test_tinyint values(127,127)"
	RUNSQL1 "insert into ddcw_test_tinyint values(1,255)"
	RUNSQL1 "insert into ddcw_test_tinyint values(2,null)"
	RUNSQL1 "insert into ddcw_test_tinyint values(null,1)"
	RUNSQL1 "insert into ddcw_test_tinyint values(null,null)"
	#test1 ddcw_test_tinyint
	add_crc32 ddcw_test_tinyint

	# smallint
	RUNSQL1 "drop table if exists ddcw_test_smallint;"
	RUNSQL1 "create table if not exists ddcw_test_smallint(aa smallint, bb smallint unsigned);"
	RUNSQL1 "insert into ddcw_test_smallint values(-32767,0)"
	RUNSQL1 "insert into ddcw_test_smallint values(-0,0)"
	RUNSQL1 "insert into ddcw_test_smallint values(32767,32767)"
	RUNSQL1 "insert into ddcw_test_smallint values(1,65535)"
	RUNSQL1 "insert into ddcw_test_smallint values(2,null)"
	RUNSQL1 "insert into ddcw_test_smallint values(null,1)"
	RUNSQL1 "insert into ddcw_test_smallint values(null,null)"
	#test1 ddcw_test_smallint
	add_crc32 ddcw_test_smallint


	# mediumint
	RUNSQL1 "drop table if exists ddcw_test_mediumint;"
	RUNSQL1 "create table if not exists ddcw_test_mediumint(aa mediumint, bb mediumint unsigned);"
	RUNSQL1 "insert into ddcw_test_mediumint values(-8388607,0)"
	RUNSQL1 "insert into ddcw_test_mediumint values(-0,-0)"
	RUNSQL1 "insert into ddcw_test_mediumint values(0,0)"
	RUNSQL1 "insert into ddcw_test_mediumint values(8388607,8388607)"
	RUNSQL1 "insert into ddcw_test_mediumint values(1,16777215)"
	RUNSQL1 "insert into ddcw_test_mediumint values(2,null)"
	RUNSQL1 "insert into ddcw_test_mediumint values(null,1)"
	RUNSQL1 "insert into ddcw_test_mediumint values(null,null)"
	#test1 ddcw_test_mediumint
	add_crc32 ddcw_test_mediumint

	# int
	RUNSQL1 "drop table if exists ddcw_test_int;"
	RUNSQL1 "create table if not exists ddcw_test_int(aa int, bb int unsigned);"
	RUNSQL1 "insert into ddcw_test_int values(-2147483647,0)"
	RUNSQL1 "insert into ddcw_test_int values(-0,-0)"
	RUNSQL1 "insert into ddcw_test_int values(0,0)"
	RUNSQL1 "insert into ddcw_test_int values(2147483647,2147483647)"
	RUNSQL1 "insert into ddcw_test_int values(1,4294967295)"
	RUNSQL1 "insert into ddcw_test_int values(2,null)"
	RUNSQL1 "insert into ddcw_test_int values(null,1)"
	RUNSQL1 "insert into ddcw_test_int values(null,null)"
	#test1 ddcw_test_int
	add_crc32 ddcw_test_int

	# bigint
	RUNSQL1 "drop table if exists ddcw_test_bigint;"
	RUNSQL1 "create table if not exists ddcw_test_bigint(aa bigint, bb bigint unsigned);"
	RUNSQL1 "insert into ddcw_test_bigint values(-9223372036854775807,0)"
	RUNSQL1 "insert into ddcw_test_bigint values(-0,-0)"
	RUNSQL1 "insert into ddcw_test_bigint values(0,0)"
	RUNSQL1 "insert into ddcw_test_bigint values(9223372036854775807,9223372036854775807)"
	RUNSQL1 "insert into ddcw_test_bigint values(1,18446744073709551615)"
	RUNSQL1 "insert into ddcw_test_bigint values(2,null)"
	RUNSQL1 "insert into ddcw_test_bigint values(null,1)"
	RUNSQL1 "insert into ddcw_test_bigint values(null,null)"
	#test1 ddcw_test_bigint
	add_crc32 ddcw_test_bigint

	# float 1681 | UNSIGNED for decimal and floating point data types is deprecated and support for it will be removed in a future release
	RUNSQL1 "drop table if exists ddcw_test_float;"
	RUNSQL1 "create table if not exists ddcw_test_float(aa float(24), bb float(25));"
	RUNSQL1 "insert into  ddcw_test_float values(-123.123,-123.123)"
	RUNSQL1 "insert into  ddcw_test_float values(-3.1,-1.12)"
	RUNSQL1 "insert into  ddcw_test_float values(3.3,2.3)"
	RUNSQL1 "insert into  ddcw_test_float values(-0,-0)"
	RUNSQL1 "insert into  ddcw_test_float values(0,0)"
	RUNSQL1 "insert into  ddcw_test_float values(10,10)"
	RUNSQL1 "insert into  ddcw_test_float values(null,null)"
	RUNSQL1 "insert into  ddcw_test_float values(1,null)"
	RUNSQL1 "insert into  ddcw_test_float values(null,1)"
	#test1 ddcw_test_float
	add_crc32 ddcw_test_float

	# double
	RUNSQL1 "drop table if exists ddcw_test_double;"
	RUNSQL1 "create table if not exists ddcw_test_double(aa double, bb double);"
	RUNSQL1 "insert into   ddcw_test_double values(-123.123,-123.123)"
	RUNSQL1 "insert into   ddcw_test_double values(-3.1,-1.12)"
	RUNSQL1 "insert into   ddcw_test_double values(3.3,2.3)"
	RUNSQL1 "insert into   ddcw_test_double values(-0,-0)" # mysql bug 114962
	RUNSQL1 "insert into   ddcw_test_double values(0,0)"
	RUNSQL1 "insert into   ddcw_test_double values(10,10)"
	RUNSQL1 "insert into   ddcw_test_double values(null,null)"
	RUNSQL1 "insert into   ddcw_test_double values(1,null)"
	RUNSQL1 "insert into   ddcw_test_double values(null,1)"
	#test1 ddcw_test_double
	add_crc32 ddcw_test_double

	# decimal
	RUNSQL1 "drop table if exists ddcw_test_decimal;"
	RUNSQL1 "create table if not exists ddcw_test_decimal(aa decimal(20,10), bb decimal(10,5));"
	RUNSQL1 "insert into   ddcw_test_decimal values(123456.123456, 12345.12345)"
	RUNSQL1 "insert into   ddcw_test_decimal values(-123456.123456, -12345.12345)"
	RUNSQL1 "insert into   ddcw_test_decimal values(-1234567890.1234567890, -1.1)"
	RUNSQL1 "insert into   ddcw_test_decimal values(-0, -0)"
	RUNSQL1 "insert into   ddcw_test_decimal values(null, 1)"
	RUNSQL1 "insert into   ddcw_test_decimal values(1, null)"
	RUNSQL1 "insert into   ddcw_test_decimal values(null, null)"
	RUNSQL1 "insert into   ddcw_test_decimal values(1, 1)"
	#test1 ddcw_test_decimal
	# 生成一点随机数
	for i in {1..100};do
		if [ $[ $i % 2 ] -eq 0 ];then
			fh="-"
		else
			fh=""
		fi
		int1="$(shuf -i 0-999999999 -n 1).$(shuf -i 0-999999999 -n 1)"
		RUNSQL1 "insert into   ddcw_test_decimal values(${fh}$(shuf -i 0-999999999 -n 1).$(shuf -i 0-999999999 -n 1), ${fh}$(shuf -i 0-99999 -n 1).$(shuf -i 0-99999 -n 1))"
	done
	add_crc32 ddcw_test_decimal
}

test_time(){
	# year
	RUNSQL1 "drop table if exists ddcw_test_year;"
	RUNSQL1 "create table if not exists ddcw_test_year(id int, aa year);"
	RUNSQL1 "insert into ddcw_test_year values(1, 1901);"
	RUNSQL1 "insert into ddcw_test_year values(2, 2155);"
	RUNSQL1 "insert into ddcw_test_year values(3, 2024);"
	for i in {4..100};do
		RUNSQL1 "insert into ddcw_test_year values {${i},$(shuf -i 1901-2155 -n 1)}"
	done
	add_crc32 ddcw_test_year

	# date
	RUNSQL1 "drop table if exists ddcw_test_date;"
	RUNSQL1 "create table if not exists ddcw_test_date(id int, aa date);"
	RUNSQL1 "insert into ddcw_test_date values(1, '2024-05-20');"
	RUNSQL1 "insert into ddcw_test_date values(2, '1000-01-01');"
	RUNSQL1 "insert into ddcw_test_date values(3, '9999-12-31');"
	RUNSQL1 "insert into ddcw_test_date values(4, '1970-1-1');"
	add_crc32 ddcw_test_date

	# datetime
	RUNSQL1 "drop table if exists ddcw_test_datetime;"
	RUNSQL1 "create table if not exists ddcw_test_datetime(id int, aa datetime(6));"
	RUNSQL1 "insert into ddcw_test_datetime values(1, '2024-05-20 11:11:11');"
	RUNSQL1 "insert into ddcw_test_datetime values(2, '1000-01-01 00:00:00');"
	RUNSQL1 "insert into ddcw_test_datetime values(3, '9999-12-31 23:59:59');"
	RUNSQL1 "insert into ddcw_test_datetime values(4, '1970-1-1 00:00:00');"
	RUNSQL1 "insert into ddcw_test_datetime values(5, '2024-05-20 11:11:11.1234');"
	RUNSQL1 "insert into ddcw_test_datetime values(6, '-2024-05-20 11:11:11.1234');"
	startdate="2000-01-01"
	stopdate="2024-12-30"
	starttimestamp=$(date -d "${startdate}" +%s)
	stoptimestamp=$(date -d "${stopdate}" +%s)
	for i in {1..100};do
		randomdate=$(date -d "@$(shuf -i ${starttimestamp}-${stoptimestamp} -n 1)" '+%Y-%m-%d %H:%M:%S')
		RUNSQL1 "insert into ddcw_test_datetime values(${i},'${randomdate}')"
	done
	add_crc32 ddcw_test_datetime

	# time
	RUNSQL1 "drop table if exists ddcw_test_time;"
	RUNSQL1 "create table if not exists ddcw_test_time(id int, aa time(6));"
	RUNSQL1 "insert into ddcw_test_time values(1,'00:00:00')"
	RUNSQL1 "insert into ddcw_test_time values(2,'23:59:59')"
	RUNSQL1 "insert into ddcw_test_time values(3,'-12:00:00')"
	RUNSQL1 "insert into ddcw_test_time values(4,'4:00:00.12')"
	add_crc32 ddcw_test_time

	# timestamp
	RUNSQL1 "drop table if exists ddcw_test_timestamp;"
	RUNSQL1 "create table if not exists ddcw_test_timestamp(id int, aa timestamp(6))"
	RUNSQL1 "insert into ddcw_test_timestamp values(1, '2024-05-20 11:11:11');"
	RUNSQL1 "insert into ddcw_test_timestamp values(2, '1970-1-1 00:00:00');"
	RUNSQL1 "insert into ddcw_test_timestamp values(3, '2024-05-20 11:11:11.1234');"
	RUNSQL1 "insert into ddcw_test_timestamp values(4, '-2024-05-20 11:11:11.1234');"
	add_crc32 ddcw_test_timestamp
}


test_add_column(){
	RUNSQL1 "drop table if exists ddcw_test_add_col"
	RUNSQL1 "create table if not exists ddcw_test_add_col(id int, aa varchar(20))"
	RUNSQL1 "insert into ddcw_test_add_col values(1,'aa')"
	RUNSQL1 "alter table ddcw_test_add_col add column bb varchar(20)"
	RUNSQL1 "insert into ddcw_test_add_col values(2,'bb','newbBYDDCW')"
	add_crc32 ddcw_test_add_col
}

test_partition(){
	RUNSQL1 "drop table if exists ddcw_test_p_range"
	RUNSQL1 "create table if not exists ddcw_test_p_range (id int, name varchar(200)) PARTITION BY RANGE (id) (PARTITION p0 VALUES LESS THAN (10), PARTITION p1 VALUES LESS THAN (100), PARTITION p2 VALUES LESS THAN (200),PARTITION p3 VALUES LESS THAN (10000));"
	for x in {1..100};do
		RUNSQL1 "insert into ddcw_test_p_range values(${x},'aa')"
	done
	add_crc32 ddcw_test_p_range

	# hash
	RUNSQL1 "drop table if exists ddcw_test_p_hash"
	RUNSQL1 "create table if not exists ddcw_test_p_hash(id int, name varchar(200), age_y datetime) PARTITION BY HASH (year(age_y)) partitions 4  ;"
	startdate="2000-01-01"
	stopdate="2024-12-30"
	starttimestamp=$(date -d "${startdate}" +%s)
	stoptimestamp=$(date -d "${stopdate}" +%s)
	for i in {1..100};do
		randomdate=$(date -d "@$(shuf -i ${starttimestamp}-${stoptimestamp} -n 1)" '+%Y-%m-%d %H:%M:%S')
		RUNSQL1 "insert into ddcw_test_p_hash values(${i},'https://github.com/ddcw/ibd2sql','${randomdate}')"
	done
	add_crc32 ddcw_test_p_hash

	# list
	RUNSQL1 "drop table if exists ddcw_test_p_list"
	RUNSQL1 "create table if not exists ddcw_test_p_list(id int, aa varchar(200))PARTITION BY list(id) (PARTITION p1 VALUES IN (1,2,3,4), PARTITION p2 VALUES IN (5,6,7,8) );"
	for i in {1..8};do
		RUNSQL1 "insert into ddcw_test_p_list values(${i},'https://github.com/ddcw/ibd2sql')"
	done
	add_crc32 ddcw_test_p_list

	#key
	RUNSQL1 "drop table if exists ddcw_test_p_key"
	RUNSQL1 "create table if not exists ddcw_test_p_key(id int primary key, aa varchar(200)) PARTITION BY KEY() PARTITIONS 2;"
	for i in {1..100};do
		RUNSQL1 "insert into ddcw_test_p_key values(${i},'https://github.com/ddcw/ibd2sql')"
	done
	add_crc32 ddcw_test_p_key

	# subpartition
	RUNSQL1 "drop table if exists ddcw_test_sp_rangehash"
	RUNSQL1 "CREATE TABLE if not exists ddcw_test_sp_rangehash(id INT, purchased DATE)
    PARTITION BY RANGE( YEAR(purchased) )
    SUBPARTITION BY HASH( TO_DAYS(purchased) )
    SUBPARTITIONS 2 (
        PARTITION p0 VALUES LESS THAN (1990),
        PARTITION p1 VALUES LESS THAN (2000),
        PARTITION p2 VALUES LESS THAN MAXVALUE
    );"
	for x in {1..100};do
		RUNSQL1 "insert into ddcw_test_sp_rangehash values(1${x},'1988-01-01');"
		RUNSQL1 "insert into ddcw_test_sp_rangehash values(2${x},'1999-01-01');"
		RUNSQL1 "insert into ddcw_test_sp_rangehash values(3${x},'2024-05-20');"
	done
	add_crc32 ddcw_test_sp_rangehash

}

test_ascii(){
	RUNSQL1 "drop table if exists ddcw_test_ascii"
	RUNSQL1 "create table if not exists ddcw_test_ascii(id int, aa char(255) CHARACTER SET ascii, bb char(32))"
	for x in {1..100};do
		RUNSQL1 "insert into ddcw_test_ascii values(${x},'https://github.com/ddcw/ibd2sql','ddcw')"
	done
	#add_crc32 ddcw_test_ascii # 没做字段字符集的展示,导致crc32结果不一致, 那就使用hash吧 -_-.
	add_sha1 ddcw_test_ascii
}

test_default_date(){
	RUNSQL1 "drop table if exists ddcw_test_default_time"
	RUNSQL1 "create table if not exists ddcw_test_default_time (id int, aa datetime)"
}

test_hidden_drop_col(){
	RUNSQL1 "drop table if exists ddcw_test_drop_col;"
	RUNSQL1 "create table if not exists ddcw_test_drop_col (id int, aa varchar(20))"
	for i in {1..100};do
		RUNSQL1 "insert into ddcw_test_drop_col values(${i},'ddcw')"
	done
	RUNSQL1 "/*!80030 set session sql_generate_invisible_primary_key=ON*/; alter table ddcw_test_drop_col drop column aa;"
	add_crc32 ddcw_test_drop_col
}

test_60_ddl(){
	RUNSQL1 "drop table if exists ddcw_test_60_ddl;"
	RUNSQL1 "create table if not exists ddcw_test_60_ddl(cc0 varchar(32), cc1 varchar(32), cc2 varchar(32), cc3 varchar(32), cc4 varchar(32), cc5 varchar(32), cc6 varchar(32), cc7 varchar(32), cc8 varchar(32), cc9 varchar(32));"
	echo ""
	COLLIST=() 
	for i in {1..60};do
		# 判断是加列还是删列
		action='del'
		if [[ ${COLLIST[@]} == '' ]];then
			action='add'
		else
			if [ $[ $RANDOM % 2 ] -eq 0 ];then
				action='add'
			fi
		fi

		if [ "${action}" == 'add' ];then
			COLLIST+=($i)
			ddl="alter table ddcw_test_60_ddl add column c${i} varchar(32)"
			if [ $[ $RANDOM % 2 ] -eq 0 ];then
				ddl+=" after cc$[ $RANDOM % 9 ]"
			fi
			RUNSQL1 "${ddl}"
		elif [ "${action}" == 'del' ];then
			_n=$[ ${RANDOM} % ${#COLLIST[@]} ]
			colname="c${COLLIST[$_n]}"
			ddl="alter table ddcw_test_60_ddl drop column ${colname}"
			RUNSQL1 "${ddl}"
			unset 'COLLIST[_n]'
			COLLIST=("${COLLIST[@]}")
			
		fi
		echo "-- DDL: ${ddl};"
		# 插入数据
		for x in {1..60};do
			sql="insert into ddcw_test_60_ddl values("
			for y in {1..10}; do sql+="\"`echo $RANDOM|md5sum|awk '{print $1}'`\",";done
			aa=0
			while [ ${aa} -lt ${#COLLIST[@]} ];do
				aa=$[ ${aa} + 1 ]
				sql+="\"`echo $RANDOM|md5sum|awk '{print $1}'`\","
			done
			sql=${sql::-1}")"
			RUNSQL1 "${sql}"
			#echo "${sql};"
		done

	done
	add_sha1 ddcw_test_60_ddl
	add_crc32 ddcw_test_60_ddl
}

test_vector(){
	RUNSQL1 "drop table if exists ddcw_test_vector;"
	RUNSQL1 "create table if not exists ddcw_test_vector(id int, aa vector(2048), bb vector(6666));"
	RUNSQL1 "insert into ddcw_test_vector values(1,TO_VECTOR('[2048,2048]'),TO_VECTOR('[6666,6666]'))"
	RUNSQL1 "insert into ddcw_test_vector values(2,null,TO_VECTOR('[1,1]'))"
	RUNSQL1 "insert into ddcw_test_vector values(3,TO_VECTOR('[1,1]'),null)"
	RUNSQL1 "insert into ddcw_test_vector values(4,null,null)"
	add_crc32 ddcw_test_vector
}

echo "<数据类型测试> 初始化数据中..."
test_varchar
test_int #含double, float, decimal
test_time #时间类型
echo "<ddl if instant> 初始化数据中..."
test_add_column #instant
echo "<partition&subpartition> 初始化数据中..."
test_partition # 分区表&子分区
# 5.7 升级(不好测)
echo "<ascii charset> 初始化数据中..."
test_ascii
#echo "<default date> 初始化数据中..."
#test_default_date
test_hidden_drop_col
if ${ISMYSQL5};then
	echo "skip <test_60_ddl>"
else
	echo "<test_60_ddl> 初始化数据中..."
	test_60_ddl
fi
if [ "${MYSQL_VERSION1::1}" == "9" ];then
	echo "<test_vector> 初始化数据中..."
	test_vector
else
	echo "skip <test_vector>"
fi

RUNSQL1 "flush tables;" 
sleep 3
printf "%-3s\t%-20s\t%-10s\t%-10s\t%-10s\n" NO DESCRIPTION CHECKSUM1 CHECKSUM2 STATUS
for x in ${CRC32_LIST};
do
	test1 ${x}
done
for x in ${HASH1_LIST};
do
	test1 ${x} "sha1" 
done

if [ ${INCONSISTENT} -eq 0 ];then
	echo "测试通过"
	exit 0
else
	echo "测试未通过, 失败数量: ${INCONSISTENT}"
	exit 1
fi


