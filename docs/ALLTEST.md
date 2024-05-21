本文为 [ibd2sql](https://github.com/ddcw/ibd2sql) 完整测试结果.



# 测试方法

编辑 `test.sh`脚本, 修改对应信息.

1. MYSQLBIN1 表示要测试的数据库连接信息
2. MYSQLBIN2 表示 `解析出来的结果`保存的数据集连接信息
3. MYSQLBIN3 如果`MYSQLBIN1` 是5.7的版本, 则需要这个中间库. 仅生成sdi信息(无数据产生).
4. SERVER 如果是`MYSQLBIN1` 是5.7的版本, 则需要数据库连接串(mysqlfrm需要这个信息才能解析出来字符集信息.)
5. MYSQLDB1,MYSQLDB2,MYSQLDB3 分别对应MYSQLBIN1 ,MYSQLBIN2, MYSQLBIN3 的数据库



修改完信息之后, 直接执行脚本即可. 若测试结果均通过, 则打印`测试通过`

```shell
sh test.sh
```



# 测试结果汇总

版本太多了, 就选部分版本做测试.

| 版本           | 是否支持 | 备注                                       |
| ------------ | ---- | ---------------------------------------- |
| mysql-5.6.51 | 是    | mysqlfrm解析datetime,time,timestamp会丢失精度,ENUM解析失败 |
| mysql-5.7.17 | 是    | mysqlfrm解析datetime,time,timestamp会丢失精度   |
| mysql-5.7.27 | 是    | mysqlfrm解析datetime,time,timestamp会丢失精度   |
| mysql-5.7.35 | 是    | mysqlfrm解析datetime,time,timestamp会丢失精度   |
| mysql-5.7.38 | 是    | mysqlfrm解析datetime,time,timestamp会丢失精度   |
| mysql-5.7.41 | 是    | mysqlfrm解析datetime,time,timestamp会丢失精度   |
| mysql-5.7.44 | 是    | mysqlfrm解析datetime,time,timestamp会丢失精度   |
| mysql-8.0.12 | 是    | 不支持子分区(没得元数据信息)                          |
| mysql-8.0.13 | 是    | 不支持子分区(没得元数据信息)                          |
| mysql-8.0.16 | 是    | 不支持子分区(没得元数据信息)                          |
| mysql-8.0.18 | 是    | 不支持子分区(没得元数据信息)                          |
| mysql-8.0.22 | 是    |                                          |
| mysql-8.0.24 | 是    |                                          |
| mysql-8.0.26 | 是    |                                          |
| mysql-8.0.28 | 是    |                                          |
| mysql-8.0.30 | 是    | ONLINE DDL(instant)不完全支持                 |
| mysql-8.0.32 | 是    | ONLINE DDL(instant)不完全支持                 |
| mysql-8.0.33 | 是    | ONLINE DDL(instant)不完全支持                 |
| mysql-8.0.36 | 是    | ONLINE DDL(instant)不完全支持                 |
| mysql-8.0.37 | 是    | ONLINE DDL(instant)不完全支持                 |
| mysql-8.4.0  | 是    | ONLINE DDL(instant)不完全支持                 |



# 测试结果

本次仅做部分版本测试.  其它的请自行测试.

```shell
[root@VM-32-39-centos ibd2sql-main]# sh test.sh 
测试库: MYSQL VERSION 8.0.37
目标库: MYSQL VERSION 8.0.37
<数据类型测试> 初始化数据中...
<ddl if instant> 初始化数据中...
<partition&subpartition> 初始化数据中...
<ascii charset> 初始化数据中...
NO 	DESCRIPTION         	CHECKSUM1 	CHECKSUM2 	STATUS    
1  	ddcw_test_varchar_500	2800928485	2800928485	PASS      
2  	ddcw_test_varchar_16380	4122188419	4122188419	PASS      
3  	ddcw_test_char      	801404664 	801404664 	PASS      
4  	ddcw_test_binary    	102900283 	102900283 	PASS      
5  	ddcw_test_varbinary 	2533025381	2533025381	PASS      
6  	ddcw_test_set       	2800683776	2800683776	PASS      
7  	ddcw_test_enum      	1077517638	1077517638	PASS      
8  	ddcw_test_lob       	2366570167	2366570167	PASS      
9  	ddcw_test_json      	1542118033	1542118033	PASS      
10 	ddcw_test_geom      	4135153503	4135153503	PASS      
11 	ddcw_test_tinyint   	802451637 	802451637 	PASS      
12 	ddcw_test_smallint  	4262932541	4262932541	PASS      
13 	ddcw_test_mediumint 	1186843781	1186843781	PASS      
14 	ddcw_test_int       	2842470026	2842470026	PASS      
15 	ddcw_test_bigint    	959135233 	959135233 	PASS      
16 	ddcw_test_float     	3281838162	3281838162	PASS      
17 	ddcw_test_double    	2975077222	2975077222	PASS      
18 	ddcw_test_decimal   	3357267839	3357267839	PASS      
19 	ddcw_test_year      	992146600 	992146600 	PASS      
20 	ddcw_test_date      	494130839 	494130839 	PASS      
21 	ddcw_test_datetime  	3484197160	3484197160	PASS      
22 	ddcw_test_time      	1109272829	1109272829	PASS      
23 	ddcw_test_timestamp 	3275869004	3275869004	PASS      
24 	ddcw_test_add_col   	1616405144	986349287 	FAILD     
25 	ddcw_test_p_range   	3563129834	3563129834	PASS      
26 	ddcw_test_p_hash    	2703482655	2703482655	PASS      
27 	ddcw_test_p_list    	1975214345	1975214345	PASS      
28 	ddcw_test_sp_rangehash	3784909504	3784909504	PASS      
29 	ddcw_test_ascii     	3965747881	3965747881	PASS      
测试未通过, 失败数量: 1

```



## 5.6 测试结果

不支持5.6的enum数据类型.

对于datetime,time,timestamp数据类型测试失败, 也是精度丢失问题.

`5.6.51`测试结果如下

| NO   | DESCRIPTION            | CHECKSUM1  | CHECKSUM2  | STATUS |
| ---- | ---------------------- | ---------- | ---------- | ------ |
| 1    | ddcw_test_varchar_500  | 2800928485 | 2800928485 | PASS   |
| 2    | ddcw_test_char         | 801404664  | 801404664  | PASS   |
| 3    | ddcw_test_set          | 2800683776 | 2800683776 | PASS   |
| 4    | ddcw_test_enum         | 87634152   | 0          | FAILD  |
| 5    | ddcw_test_tinyint      | 802451637  | 802451637  | PASS   |
| 6    | ddcw_test_smallint     | 4262932541 | 4262932541 | PASS   |
| 7    | ddcw_test_mediumint    | 1186843781 | 1186843781 | PASS   |
| 8    | ddcw_test_int          | 2842470026 | 2842470026 | PASS   |
| 9    | ddcw_test_bigint       | 959135233  | 959135233  | PASS   |
| 10   | ddcw_test_float        | 3281838162 | 3281838162 | PASS   |
| 11   | ddcw_test_double       | 2975077222 | 2975077222 | PASS   |
| 12   | ddcw_test_decimal      | 1288315504 | 1288315504 | PASS   |
| 13   | ddcw_test_year         | 992146600  | 992146600  | PASS   |
| 14   | ddcw_test_date         | 494130839  | 494130839  | PASS   |
| 15   | ddcw_test_datetime     | 689894592  | 439434718  | FAILD  |
| 16   | ddcw_test_time         | 1109272829 | 2806176593 | FAILD  |
| 17   | ddcw_test_timestamp    | 3456636701 | 2875489858 | FAILD  |
| 18   | ddcw_test_add_col      | 1616405144 | 1616405144 | PASS   |
| 19   | ddcw_test_p_range      | 3563129834 | 3563129834 | PASS   |
| 20   | ddcw_test_p_hash       | 2362191188 | 2362191188 | PASS   |
| 21   | ddcw_test_p_list       | 1975214345 | 1975214345 | PASS   |
| 22   | ddcw_test_p_key        | 237814889  | 237814889  | PASS   |
| 23   | ddcw_test_sp_rangehash | 3784909504 | 3784909504 | PASS   |
| 24   | ddcw_test_ascii        | 3965747881 | 3965747881 | PASS   |



## 5.7 测试结果

对于datetime,time,timestamp数据类型测试失败(测试版本: `5.7.38-log`)

失败原因: mysqlfrm解析出来的DDL没得datetime/time/timestamp的毫秒信息(精度丢失). 所以严格来讲是`mysqlfrm`的问题, 而不是ibd2sql的问题. (下一个大版本还是得自己解析frm文件.)

| NO   | DESCRIPTION            | CHECKSUM1  | CHECKSUM2  | STATUS |
| ---- | ---------------------- | ---------- | ---------- | ------ |
| 1    | ddcw_test_varchar_500  | 2800928485 | 2800928485 | PASS   |
| 2    | ddcw_test_char         | 801404664  | 801404664  | PASS   |
| 3    | ddcw_test_set          | 2800683776 | 2800683776 | PASS   |
| 4    | ddcw_test_enum         | 1077517638 | 1077517638 | PASS   |
| 5    | ddcw_test_tinyint      | 802451637  | 802451637  | PASS   |
| 6    | ddcw_test_smallint     | 4262932541 | 4262932541 | PASS   |
| 7    | ddcw_test_mediumint    | 1186843781 | 1186843781 | PASS   |
| 8    | ddcw_test_int          | 2842470026 | 2842470026 | PASS   |
| 9    | ddcw_test_bigint       | 959135233  | 959135233  | PASS   |
| 10   | ddcw_test_float        | 3281838162 | 3281838162 | PASS   |
| 11   | ddcw_test_double       | 2975077222 | 2975077222 | PASS   |
| 12   | ddcw_test_decimal      | 3174813357 | 3174813357 | PASS   |
| 13   | ddcw_test_year         | 992146600  | 992146600  | PASS   |
| 14   | ddcw_test_date         | 494130839  | 494130839  | PASS   |
| 15   | ddcw_test_datetime     | 3004046422 | 1210235633 | FAILD  |
| 16   | ddcw_test_time         | 1109272829 | 2806176593 | FAILD  |
| 17   | ddcw_test_timestamp    | 3275631794 | 2493904769 | FAILD  |
| 18   | ddcw_test_add_col      | 1616405144 | 1616405144 | PASS   |
| 19   | ddcw_test_p_range      | 3563129834 | 3563129834 | PASS   |
| 20   | ddcw_test_p_hash       | 670977355  | 670977355  | PASS   |
| 21   | ddcw_test_p_list       | 1975214345 | 1975214345 | PASS   |
| 22   | ddcw_test_p_key        | 237814889  | 237814889  | PASS   |
| 23   | ddcw_test_sp_rangehash | 3784909504 | 3784909504 | PASS   |
| 24   | ddcw_test_ascii        | 3965747881 | 3965747881 | PASS   |



## 8.0 测试结果

8.0.12  8.0.13  8.0.16  8.0.18 不支持子分区 (没找到元数据信息. 不在ibd里面, 也没得frm文件)

`8.0.28`测试结果如下:

| NO   | DESCRIPTION             | CHECKSUM1  | CHECKSUM2  | STATUS |
| ---- | ----------------------- | ---------- | ---------- | ------ |
| 1    | ddcw_test_varchar_500   | 2800928485 | 2800928485 | PASS   |
| 2    | ddcw_test_char          | 1665573019 | 1665573019 | PASS   |
| 3    | ddcw_test_set           | 2800683776 | 2800683776 | PASS   |
| 4    | ddcw_test_enum          | 1077517638 | 1077517638 | PASS   |
| 5    | ddcw_test_binary        | 102900283  | 102900283  | PASS   |
| 6    | ddcw_test_varbinary     | 2533025381 | 2533025381 | PASS   |
| 7    | ddcw_test_varchar_16380 | 4122188419 | 4122188419 | PASS   |
| 8    | ddcw_test_lob           | 2366570167 | 2366570167 | PASS   |
| 9    | ddcw_test_json          | 1542118033 | 1542118033 | PASS   |
| 10   | ddcw_test_geom          | 4135153503 | 4135153503 | PASS   |
| 11   | ddcw_test_tinyint       | 802451637  | 802451637  | PASS   |
| 12   | ddcw_test_smallint      | 4262932541 | 4262932541 | PASS   |
| 13   | ddcw_test_mediumint     | 1186843781 | 1186843781 | PASS   |
| 14   | ddcw_test_int           | 2842470026 | 2842470026 | PASS   |
| 15   | ddcw_test_bigint        | 959135233  | 959135233  | PASS   |
| 16   | ddcw_test_float         | 3281838162 | 3281838162 | PASS   |
| 17   | ddcw_test_double        | 2975077222 | 2975077222 | PASS   |
| 18   | ddcw_test_decimal       | 2734603572 | 2734603572 | PASS   |
| 19   | ddcw_test_year          | 992146600  | 992146600  | PASS   |
| 20   | ddcw_test_date          | 494130839  | 494130839  | PASS   |
| 21   | ddcw_test_datetime      | 3120277807 | 3120277807 | PASS   |
| 22   | ddcw_test_time          | 1109272829 | 1109272829 | PASS   |
| 23   | ddcw_test_timestamp     | 3275869004 | 3275869004 | PASS   |
| 24   | ddcw_test_add_col       | 1616405144 | 1616405144 | PASS   |
| 25   | ddcw_test_p_range       | 3563129834 | 3563129834 | PASS   |
| 26   | ddcw_test_p_hash        | 1255695099 | 1255695099 | PASS   |
| 27   | ddcw_test_p_list        | 1975214345 | 1975214345 | PASS   |
| 28   | ddcw_test_p_key         | 237814889  | 237814889  | PASS   |
| 29   | ddcw_test_sp_rangehash  | 3784909504 | 3784909504 | PASS   |
| 30   | ddcw_test_ascii         | 3965747881 | 3965747881 | PASS   |





## 8.4 测试结果

`8.4.0`测试结果如下:

做过ONLINE DDL(ddcw_test_add_col)的解析数据存在一定问题. `8.0.37`也存在这个问题. 后面有空了再修复.

| NO   | DESCRIPTION             | CHECKSUM1  | CHECKSUM2  | STATUS |
| ---- | ----------------------- | ---------- | ---------- | ------ |
| 1    | ddcw_test_varchar_500   | 2800928485 | 2800928485 | PASS   |
| 2    | ddcw_test_varchar_16380 | 4122188419 | 4122188419 | PASS   |
| 3    | ddcw_test_char          | 801404664  | 801404664  | PASS   |
| 4    | ddcw_test_binary        | 102900283  | 102900283  | PASS   |
| 5    | ddcw_test_varbinary     | 2533025381 | 2533025381 | PASS   |
| 6    | ddcw_test_set           | 2800683776 | 2800683776 | PASS   |
| 7    | ddcw_test_enum          | 1077517638 | 1077517638 | PASS   |
| 8    | ddcw_test_lob           | 2366570167 | 2366570167 | PASS   |
| 9    | ddcw_test_json          | 1542118033 | 1542118033 | PASS   |
| 10   | ddcw_test_geom          | 4135153503 | 4135153503 | PASS   |
| 11   | ddcw_test_tinyint       | 802451637  | 802451637  | PASS   |
| 12   | ddcw_test_smallint      | 4262932541 | 4262932541 | PASS   |
| 13   | ddcw_test_mediumint     | 1186843781 | 1186843781 | PASS   |
| 14   | ddcw_test_int           | 2842470026 | 2842470026 | PASS   |
| 15   | ddcw_test_bigint        | 959135233  | 959135233  | PASS   |
| 16   | ddcw_test_float         | 3281838162 | 3281838162 | PASS   |
| 17   | ddcw_test_double        | 2975077222 | 2975077222 | PASS   |
| 18   | ddcw_test_decimal       | 3357267839 | 3357267839 | PASS   |
| 19   | ddcw_test_year          | 992146600  | 992146600  | PASS   |
| 20   | ddcw_test_date          | 494130839  | 494130839  | PASS   |
| 21   | ddcw_test_datetime      | 3484197160 | 3484197160 | PASS   |
| 22   | ddcw_test_time          | 1109272829 | 1109272829 | PASS   |
| 23   | ddcw_test_timestamp     | 3275869004 | 3275869004 | PASS   |
| 24   | ddcw_test_add_col       | 1616405144 | 986349287  | FAILD  |
| 25   | ddcw_test_p_range       | 3563129834 | 3563129834 | PASS   |
| 26   | ddcw_test_p_hash        | 2703482655 | 2703482655 | PASS   |
| 27   | ddcw_test_p_list        | 1975214345 | 1975214345 | PASS   |
| 28   | ddcw_test_sp_rangehash  | 3784909504 | 3784909504 | PASS   |
| 29   | ddcw_test_ascii         | 3965747881 | 3965747881 | PASS   |