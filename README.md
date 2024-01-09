# 介绍

  ibd2sql 可以提取innodb ibd文件的元数据信息, 并拼接为 DDL , 还可以根据元数据信息解析ibd文件中的数据insert/replace SQL语句.

  仅支持**mysql 8.0** .



# 功能特点

1. 提取DDL
2. 提取SQL为insert/replace语句
3. 提取标记为delete的数据
4. 根据条件过滤相关数据行
5. 可使用DEBUG来查看解析过程
6. 无第三方依赖包, 纯python3代码写的.
7. 支持分区表,前缀索引等





# 下载和使用方法

## 下载

## 源码下载:

```shell
wget https://github.com/ddcw/ibd2sql/archive/refs/heads/main.zip
```

## 二进制下载:

github : https://github.com/ddcw/ibd2sql/releases





## 使用

由于无第三方依赖包, 建议使用源码

```shell
SHELL> python3 main.py --help
usage: main.py [-h] [--version] [--ddl] [--sql] [--delete] [--complete-insert]
               [--force] [--set] [--multi-value] [--replace]
               [--table TABLE_NAME] [--schema SCHEMA_NAME]
               [--sdi-table SDI_TABLE] [--where-trx WHERE_TRX]
               [--where-rollptr WHERE_ROLLPTR] [--where WHERE] [--limit LIMIT]
               [--debug] [--debug-file DEBUG_FILE] [--page-min PAGE_MIN]
               [--page-max PAGE_MAX] [--page-start PAGE_START]
               [--page-count PAGE_COUNT] [--page-skip PAGE_SKIP]
               [--parallel PARALLEL]
               FILENAME

解析mysql8.0的ibd文件 https://github.com/ddcw/ibd2sql

positional arguments:
  FILENAME              ibd filename

optional arguments:
  -h, --help            show this help message and exit
  --version, -v, -V     show version
  --ddl, -d             print ddl
  --sql                 print data by sql
  --delete              print data only for flag of deleted
  --complete-insert     use complete insert statements for sql
  --force, -f           force pasrser file when Error Page
  --set                 set/enum to fill in actual data instead of strings
  --multi-value         single sql if data belong to one page
  --replace             "REPLACE INTO" replace to "INSERT INTO" (default)
  --table TABLE_NAME    replace table name except ddl
  --schema SCHEMA_NAME  replace table name except ddl
  --sdi-table SDI_TABLE
                        read SDI PAGE from this file(ibd)(partition table)
  --where-trx WHERE_TRX
                        default (0,281474976710656)
  --where-rollptr WHERE_ROLLPTR
                        default (0,72057594037927936)
  --where WHERE         filter data(TODO)
  --limit LIMIT         limit rows
  --debug, -D           will DEBUG (it's too big)
  --debug-file DEBUG_FILE
                        default sys.stdout if DEBUG
  --page-min PAGE_MIN   if PAGE NO less than it, will break
  --page-max PAGE_MAX   if PAGE NO great than it, will break
  --page-start PAGE_START
                        INDEX PAGE START NO
  --page-count PAGE_COUNT
                        page count NO
  --page-skip PAGE_SKIP
                        skip some pages when start parse index page
  --parallel PARALLEL, -p PARALLEL
                        parse to data/sql with N threads.(default 4) TODO

```





# 使用例子

## 提取DDL

说明: DDL不包含row_format

```shell
SHELL> python main.py /data/mysql_3314/mysqldata/ibd2sql/t20240102_js.ibd --ddl
CREATE TABLE IF NOT EXISTS `ibd2sql`.`t20240102_js`(
    `id` int NOT NULL,
    `name` varchar(200) NULL,
    `aa` json NULL,
    PRIMARY KEY  (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ;

```



## 提取SQL

如果有溢出页, 就将溢出页字段置为Null

binary类型默认为 base64

```shell
SHELL> python main.py /data/mysql_3314/mysqldata/ibd2sql/AllTypesExample.ibd --sql
REPLACE INTO `ibd2sql`.`AllTypesExample` VALUES (3, 0, 0, 0, 0, 0, 0.0, 0.0, 0.0, '2000-2-29', '2000-2-29 0:0:0', '2023-8-30 14:32:35.', '0:0:0', 2001, '00000', 'Zero', 0x3030303030, '00000', 0, C, X,Z, '{"AA": {"BB": true, "CC": [{"dd": null}]}}');
```



## 提取被标记为deleted的行

```shell
SHELL> python main.py /data/mysql_3314/mysqldata/ibd2sql/AllTypesExample.ibd --sql --delete --complete
REPLACE INTO `ibd2sql`.`AllTypesExample`(`id`,`int_col`,`tinyint_col`,`smallint_col`,`mediumint_col`,`bigint_col`,`float_col`,`double_col`,`decimal_col`,`date_col`,`datetime_col`,`timestamp_col`,`time_col`,`year_col`,`char_col`,`varchar_col`,`binary_col`,`varbinary_col`,`bit_col`,`enum_col`,`set_col`,`josn_type`) VALUES (4, 0, 0, 0, 0, 0, 0.0, 0.0, 0.0, '2000-2-29', '2000-2-29 0:0:0', '2023-8-30 14:32:35.', '0:0:0', 2001, '00000', 'Zero', 0x3030303030, '00000', 0, 'C', 'X,Z', '{"AA": {"BB": true, "CC": [{"dd": null}]}}');


```



## 解析分区表

要使用--sdi-table指定元数据信息所在的第一个分区

```shell
SHELL> python main.py /data/mysql_3314/mysqldata/ibd2sql/t20240105_hash#p#p2.ibd --sdi-table /data/mysql_3314/mysqldata/ibd2sql/t20240105_hash#p#p0.ibd --sql --ddl
CREATE TABLE IF NOT EXISTS `ibd2sql`.`t20240105_hash`(
    `id` int NULL,
    `name` varchar(20) NULL,
    `bt` date NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci 
/*!50100 PARTITION BY HASH (year(`bt`))
PARTITIONS 4 */;
INSERT INTO `ibd2sql`.`t20240105_hash` VALUES (1, 'aa', '1998-1-1');
```





# 支持内容

## 表属性

| 对象           | 是否支持 | 描述                      |
| ------------ | ---- | ----------------------- |
| 存储引擎         | 支持   | 仅支持innodb               |
| 字符集          | 支持   |                         |
| 排序规则         | 支持   |                         |
| 分区表(仅一级分区)   | 支持   |                         |
| 表和schema名字替换 | 支持   |                         |
| 注释           | 支持   |                         |
| row_format   | 不支持  | only DYNAMIC or COMPACT |



## 字段属性

| 对象   | 是否支持 | 描述        |
| ---- | ---- | --------- |
| 是否为空 | 支持   |           |
| 虚拟列  | 支持   | 虚拟列不参与行解析 |
| 默认值  | 支持   |           |
| 自增   | 支持   |           |
| 注释   | 支持   |           |
| 符号   | 支持   | 数字类型存在符号  |



## 索引相关

| 对象     | 是否支持 | 描述            |
| ------ | ---- | ------------- |
| 主键索引   | 支持   |               |
| 唯一索引   | 支持   |               |
| 普通索引   | 支持   |               |
| 虚拟列的索引 | 支持   |               |
| 前缀索引   | 支持   | 前缀索引KEY数据不完整. |
| 复合索引   | 支持   |               |



## 数据类型

基本上除了空间类型外, 都支持, 但对于blob等大对象, 仅支持非溢出页的情况

参考:https://dev.mysql.com/doc/refman/8.0/en/storage-requirements.html

### 数据类型

整型均支持符号, 第一bit位为符号位(如果有符号的话) 取值方式为:

```python3
_t 是数据
_s 是字节数
(_t&((1<<_s)-1))-2**_s if _t < 2**_s and not is_unsigned else (_t&((1<<_s)-1))
```

| 对象           | 存储占用空间(字节)                   | 存储方式   | 范围(仅考虑有符号的情况)          |
| ------------ | ---------------------------- | ------ | ---------------------- |
| tinyint      | 1                            |        | -128-128               |
| smallint     | 2                            | 大端字节序  | -32768-32768           |
| int          | 4                            | 大端字节序  | -2147483648-2147483648 |
| float(n)     | size = 4 if ext <= 24 else 8 | float  |                        |
| double       | 8                            | double |                        |
| bigint       | 8                            | 大端字节序  |                        |
| mediumint    | 3                            | 大端字节序  | -8388608-8388608       |
| decimal(m,n) |                              |        |                        |
|              |                              |        |                        |

### 时间类型

| 对象           | 存储空间(字节) | 描述    | 取值范围                                     |
| ------------ | -------- | ----- | ---------------------------------------- |
| date         | 3        |       | '1000-01-01' to '9999-12-31'             |
| datetime(n)  | 5+N      |       | '1000-01-01 00:00:00.000000' to '9999-12-31 23:59:59.999999' |
| time(n)      | 3+N      |       | '-838:59:59.000000' to '838:59:59.000000' |
| timestamp(n) | 4+N      |       | '1000-01-01' to '9999-12-31'             |
| year         | 1        | +1900 | '1901' to '2115'                         |

N计算方式

```
N = int((n+1)/2)
```



### 字符类型

| 类型                       | 大小(字节)                                   | 范围        | 备注    |
| ------------------------ | ---------------------------------------- | --------- | ----- |
| char(M)                  | L                                        | <=255 字符  |       |
| BINARY(M)                | M                                        | <=255 字节  |       |
| VARCHAR(M), VARBINARY(M) | 1 字节长度 + L: 当 L < 1282 字节长度 + L: 当L >=128 | <=65535字节 |       |
| TINYBLOB, TINYTEXT       | L + 1 bytes, where L < 256               | < 256 B   |       |
| BLOB, TEXT               | L + 2 bytes, where L < 2**16             | <=65535字节 | 仅非溢出页 |
| MEDIUMBLOB, MEDIUMTEXT   | L + 3 bytes, where L < 2**24             | 16M       | 仅非溢出页 |
| LONGBLOB, LONGTEXT       | L + 4 bytes, where L < 2**32             | 4G        | 仅非溢出页 |
|                          |                                          |           |       |



### 其它类型

| 类型   | 大小                                       | 范围   | 备注         |
| ---- | ---------------------------------------- | ---- | ---------- |
| ENUM | 1 or 2 bytes, depending on the number of enumeration values (65,535 values maximum) |      | 使用数字表示     |
| SET  | 1, 2, 3, 4, or 8 bytes, depending on the number of set members (64 members maximum) |      | 使用数字表示     |
| JSON | 仅非溢出页                                    |      | mysql二进制化的 |
| 空间坐标 |                                          |      | 不支持        |





# CHANGE LOG

| 版本   | 变更时间       | 说明                     | 备注                                       |
| ---- | ---------- | ---------------------- | ---------------------------------------- |
| v0.1 | 2023.4.27  | 第一个版本....              |                                          |
| v0.2 | 2023.08.30 | 支持更多数据类型               | 1. 修复year/tinyint的支持<br />2. 符号支持(对于数字类型)<br />3. 更多的数据类型支持<br />4. 更多的表属性支持<br />5. 美化输出<br />6. 支持表名替换<br />7. 支持--complete-insert |
| v0.3 | 2023.10.13 | 支持5.7升级到8.0的ibd文件      | 修复一些BUG                                  |
| v1.0 | 2024.01.05 | 支持debug<br />支持更多类型和功能 | 1. 支持DEBUG<br />2. 支持分区表<br />3. 支持唯一索引<br />4.支持虚拟列<br />5. 支持instant<br />6.支持约束和外键<br />7. 支持限制输出<br />8.支持前缀索引 |



# 修复已知问题

1. [前缀索引](https://www.modb.pro/db/1700402156981538816)支持. 前缀索引完整数据在数据字段而不是KEY
2. [json/blob等大对象](https://www.modb.pro/db/626066)支持:  支持非溢出页的大对象
3. [5.7升级到8.0后找不到SDI](https://github.com/ddcw/ibd2sql/issues/5). :sdi pagno 记录在第一页
4. [bigint类型,注释,表属性](https://github.com/ddcw/ibd2sql/issues/2) : 支持更多数据类型, 和表属性
5. [只有1个主键和其它](https://github.com/ddcw/ibd2sql/issues/4) : 支持只有1个主键的情况, 并新增DEBUG功能



# 其它

比较杂, 基本上就是解析Ibd文件的时候遇到的不平坦的路



## JSON格式

json是mysql对其二进制化的, 所以对于数字的存储是使用的小端, 对于可变长字符串存储是使用的256*128这种

```
                如果第一bit是1 就表示要使用2字节表示:
                        后面1字节表示 使用有多少个128字节, 然后加上前面1字节(除了第一bit)的数据(0-127) 就是最终数据
-----------------------------------------------------
| 1 bit flag | 7 bit data | if flag, 8 bit data*128 |
-----------------------------------------------------
```

```
                                                               - -----------------
                                                              | JSON OBJECT/ARRAY |
                                                               - -----------------
                                                                      |
 -------------------------------------------------------------------------
| TYPE | ELEMENT_COUNT | KEY-ENTRY(if object) | VALUE-ENTRY | KEY | VALUE |
 -------------------------------------------------------------------------
                               |                    |          |
                               |                    |     --------------
                   --------------------------       |    | UTF8MB4 DATA |
                  | KEY-OFFSET |  KEY-LENGTH |      |     --------------
                   --------------------------       |
                                                    |
                                         --------------------------------
                                         | TYPE | OFFSET/VALUE(if small) |
                                         --------------------------------

```





## 分区表

分区表的元数据信息都放在第一个分区的.

`dd['object']['partitions']`



## 前缀索引,唯一索引

前缀索引判断条件:

```
indexes[x]['elements'][x]['length'] < col['char_length'] 
```

如果是前缀索引, KEY位置存储的数据就不是完整的(主键为前缀索引的情况), 后面读剩余字段的时候还要包含前缀索引



唯一索引:

```
index[x]['type']如下值:
1: PRIMARY
2: UNIQUE
3: NORMAL
```





## innodb varchar长度计算

innodb的varchar存储长度计算

```
第一字节小于等于 128 字节时, 就1字节.  否则就第一字节超过128字节的部分 *256 再加上第二字节部分来表示总大小 就是256*256 =  65536
 _size = self.readreverse(1)
 size = struct.unpack('>B',_size)[0]
 if size > REC_N_FIELDS_ONE_BYTE_MAX:
 	size = struct.unpack('>B',self.readreverse(1))[0] + (size-128)*256
 return size
```





## decimal计算

```
整数部分和小数部分是分开的

每部分 的每9位10进制数占4字节,  剩余的就按 1-2 为1字节, 这样算

比如 

(5,2)   整数就是2字节, 小数也是1字节
(10,3) 整数就是4+1字节, 小数就是2字节


```

计算方式参考:

```python3
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

size = total_size #decimal占用大小
```





## 时间类型计算

date

```
固定3字节 1bit符号,  14bit年  4bit月  5bit日
-----------------------------------
|     signed   |     1  bit       |
-----------------------------------
|      year    |     14 bit       |
-----------------------------------
|     month    |     4  bit       |
-----------------------------------
|      day     |     5  bit       |
-----------------------------------
```



datetime

```
5 bytes + fractional seconds storage
1bit符号  year_month:17bit  day:5  hour:5  minute:6  second:6
---------------------------------------------------------------------
|             signed                 |          1  bit              |     
|--------------------------------------------------------------------
|         year and month             |          17 bit              |
|--------------------------------------------------------------------
|             day                    |          5  bit              |
|--------------------------------------------------------------------
|             hour                   |          5  bit              |
|--------------------------------------------------------------------
|            minute                  |          6  bit              |
|--------------------------------------------------------------------
|            second                  |          6  bit              |
---------------------------------------------------------------------
|      fractional seconds storage    |each 2 digits is stored 1 byte|
---------------------------------------------------------------------

```



time

```
1bit符号  hour:11bit    minute:6bit  second:6bit  精度1-3bytes
-------------------------------------------------------------------
|            signed            |              1  bit              |
-------------------------------------------------------------------
|             hour             |              11 bit              |
-------------------------------------------------------------------
|            minute            |              6  bit              |
-------------------------------------------------------------------
|            second            |              6  bit              |
-------------------------------------------------------------------
|  fractional seconds storage  |  each 2 digits is stored 1 byte  |
-------------------------------------------------------------------

```



timestamp

```
4 bytes + fraction
```







## ONLINE DDL

对于使用类似如下DDL  添加字段默认ALGORITHM是 INSTANT

```
ALTER TABLE tbl_name ADD COLUMN column_name column_definition, ALGORITHM=INSTANT;
```

为了快速添加字段, 会在元数据信息记录相关信息

```
dd_object:  "se_private_data": "instant_col=1;"
column:     "se_private_data": "default=636363;table_id=2041;"
```

对于某行数据而言, 如果 record header中instant标记位为True, 则表示这行数据新增字段不是默认值, 而是要从数据位置读取(放在其它字段数据后面)

```
if recorde_header.instant and col['instant']:
	read key
	raed filed
	read filed with instant
	
if not recorde_header.instant  and col['instant']:
	rad key
	read field   新增字段取默认值
	
```

新增了多个字段之后, 需要注意下不是每行数据的字段数量都相等, 这时候就要使用到有instant之后在null bitmask和recored header之间记录的行数量了(含trx&rollptr).脚本对应变量为`_icc`



## 寻找first leaf page

有时候inode里面记录的不准... 这时候就要从root page开始往后面找leaf page了.  注意non-leaf page 是不需要trx和rollptr的, innodb的这些信息是记录在leaf page的.