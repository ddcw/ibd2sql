#!/usr/bin/env bash
MYSQL_CONN='mysql -h127.0.0.1 -P3314 -uroot -p123456'
#MYSQL_CONN="/data/mysql5096/soft/mysql-5.0.96-linux-x86_64-glibc23/bin/mysql -h192.168.101.21 -P5096 -p123456 -uu1"
SCHEMA_01='t20250828_01'
SCHEMA_02='t20250828_02'
IBD2SQL_COM="python3 ../main.py"

# check
if ${MYSQL_CONN} -e "create database if not exists ${SCHEMA_02};create database if not exists ${SCHEMA_01};" >/dev/null 2>&1;then
	echo "starting...."
else
	echo "faild to connect mysql."
	exit 1
fi

mysql_version_id=$(${MYSQL_CONN} -NB -e "select @@version" 2>/dev/null|sed -E 's/\.([0-9])\./0\1/g;s/-log//g')

# init data
echo "init data for ${mysql_version_id}"
python3 gen_data.py ${mysql_version_id} 2>/dev/null | ${MYSQL_CONN} ${SCHEMA_01} 2>/dev/null
$(${MYSQL_CONN} -NB -e "flush tables" 2>/dev/null)
sleep 5

# check data
TC=0
SC=0
echo "check data"
datadir=$(${MYSQL_CONN} -NB -e "select @@datadir" 2>/dev/null)
for tblname in `${MYSQL_CONN} -NB -e "select table_name from information_schema.tables where table_schema='${SCHEMA_01}' and table_name not like '%_partition_%'" 2>/dev/null`;
do
	echo -n "${tblname}"
	$(${MYSQL_CONN} ${SCHEMA_02} -NB -e "drop table if exists ${tblname}" 2>/dev/null)
	${IBD2SQL_COM} ${datadir}/${SCHEMA_01}/${tblname}.ibd --ddl --sql --schema ${SCHEMA_02} 2>/dev/null| ${MYSQL_CONN} ${SCHEMA_02} 2>/dev/null
	checksum1=$(${MYSQL_CONN} ${SCHEMA_01} -NB -e "checksum table ${tblname}" 2>/dev/null | awk '{print $NF}')
	checksum2=$(${MYSQL_CONN} ${SCHEMA_02} -NB -e "checksum table ${tblname}" 2>/dev/null | awk '{print $NF}')
	echo -ne "\t${checksum1}\t${checksum2}"
	TC=$[ ${TC} + 1 ]
	if [ "${checksum1}" == "${checksum2}" ];then
		echo -e "\tPASS"
		SC=$[ ${SC} + 1 ]
	else
		echo -e "\tFAILED"
	fi
done

for tblname in `${MYSQL_CONN} -NB -e "select table_name from information_schema.tables where table_schema='${SCHEMA_01}' and table_name like '%_partition_%'" 2>/dev/null`;
do
	echo -n "${tblname}"
	$(${MYSQL_CONN} ${SCHEMA_02} -NB -e "drop table if exists ${tblname}" 2>/dev/null)
	${IBD2SQL_COM} ${datadir}/${SCHEMA_01}/${tblname}\#*.ibd --ddl --sql --schema ${SCHEMA_02} | ${MYSQL_CONN} 2>/dev/null
	checksum1=$(${MYSQL_CONN} ${SCHEMA_01} -NB -e "checksum table ${tblname}" 2>/dev/null | awk '{print $NF}')
	checksum2=$(${MYSQL_CONN} ${SCHEMA_02} -NB -e "checksum table ${tblname}" 2>/dev/null | awk '{print $NF}')
	echo -ne "\t${checksum1}\t${checksum2}"
	TC=$[ ${TC} + 1 ]
	if [ "${checksum1}" == "${checksum2}" ];then
		echo -e "\tPASS"
		SC=$[ ${SC} + 1 ]
	else
		echo -e "\tFAILED"
	fi
done

echo -e "summary: ${SC}/${TC}"
