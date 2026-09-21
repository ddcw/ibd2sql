本文介绍ibd2sql v2.x支持的范围.



# 操作系统

ibd2sql是使用python3编写的,理论上只要能安装python就能使用. 主要支持Linux,Windows,MacOS



# MySQL版本

支持mysql5.x,8.x,9.x版本, 如下为ibd2sql v.2x版本支持的MySQL版本范围:

| MySQL版本 | 备注                       |
| --------- | -------------------------- |
| 5.x       | 5.0.x, 5.1.x, 5.6.x, 5.7.x |
| 8.0       | 8.0.x                      |
| 8.4       | 8.4.x                      |
| 9.x       | 9.x                        |
| 9.7.x     | 9.7.x                      |
| 26.x      | 26.x                       |



# DDL支持范围

基本上所有DDL都能解析出来,具体支持如下:

| 对象         | 备注   |
| ------------ | ------ |
| table_name   | 表名   |
| column       | 字段   |
| index        | 索引   |
| partition    | 分区   |
| subpartition | 子分区 |
| table_option | 表属性 |

## 表属性

具体支持的表属性(table_option)如下

| 表属性         | 备注             |
| -------------- | ---------------- |
| comment        | 表注释           |
| row_format     | 行格式           |
| compression    | 压缩属性         |
| auto_increment | 自增属性         |
| stats          | 统计信息收集策略 |
| charset        | 字符集           |
| collate        | 排序规则         |

备注: 支持encryption='Y'的表的解析,但ENCRYPTION属性不显示.




## 数据类型

所有数据类型均支持.具体如下:

| 数据类型  | 备注                                                         |
| --------- | ------------------------------------------------------------ |
| 整数      | tinyint,smallint,mediumint,int,bigint                        |
| 浮点数    | float,double                                                 |
| 定点数    | decimal,numeric(同decimal)                                   |
| bit       | bit                                                          |
| 时间日期  | date,time,datetime,timestamp,year,time(50604),datetime(50604) |
| 字符      | char,varchar,tinytext,smalltext,mediumtext,text,longtext     |
| 二进制    | binary,varbinary,tinyblob,smallblob,mediumblob,blob,longblob |
| 枚举&集合 | enum,set                                                     |
| json      | json                                                         |
| 空间坐标  | geometry,point,linestring,polygon,geomcollection,multipoint,multilinestring,multipolygon |
| 向量      | vector                                                       |



## 字段属性

字段属性也基本上都支持, 具体如下:

| 字段属性             | 备注                                                  |
| -------------------- | ----------------------------------------------------- |
| column_name          | 字段名                                                |
| column_type          | 字段类型                                              |
| charset              | 字符集                                                |
| collate              | 排序规则                                              |
| nullable             | 非空约束                                              |
| default              | 默认值                                                |
| visible              | 是否可见                                              |
| comment              | 注释                                                  |
| generated & virtual  | 生成列和是否存储                                      |
| check                | check约束                                             |
| foreign              | 外键约束                                              |
| reference_definition | on update cascade/restrict,on delete cascade/restrict |
| srid                 | 空间坐标的srid                                        |
| signe                | 有无符号(整数类型)                                    |
| zerofill             | 是否填充                                              |



## 索引

支持普通索引,复合索引,前缀索引. 支持几乎所有索引属性:

| 索引属性   | 备注                                                         |
| ---------- | ------------------------------------------------------------ |
| index_name | 索引名字                                                     |
| index_type | 索引类型:KEY, PRIMARY KEY, UNIQUE KEY, SPATIAL KEY, FULLTEXT KEY |
| visiable   | 是否可见                                                     |
| order      | AESC,DESC                                                    |
| comment    | 注释                                                         |






# DML(数据)支持范围

使用mysql创建的innodb表都能解析:

| 对象        | 备注                                                |
| ----------- | --------------------------------------------------- |
| page_size   | 4K,8K,16K,32K,64K                                   |
| row_format  | DYNAMIC,COMPRESSED,REDUNDANT,COMPACT                |
| encryption  | 支持加密表的解析,需要使用--keyring-file指定密钥文件 |
| compression | zlib,lz4                                            |



# 字符集

支持所有mysql字符集,具体如下:

| MySQL字符集 | 对应Python字符集                  |
| ----------- | --------------------------------- |
| binary      | -                                 |
| armscii8    | ibd2sql/utils/charset/armscii8.py |
| ascii       | utf-8                             |
| big5        | big5                              |
| cp1250      | cp1250                            |
| cp1251      | cp1251                            |
| cp1256      | cp1256                            |
| cp1257      | cp1257                            |
| cp850       | cp850                             |
| cp852       | cp852                             |
| cp866       | cp866                             |
| cp932       | cp932                             |
| dec8        | ibd2sql/utils/charset/dec8.py     |
| eucjpms     | euc-jp                            |
| euckr       | euc-kr                            |
| gb18030     | gb18030                           |
| gb2312      | gb2312                            |
| gbk         | gbk                               |
| geostd8     | ibd2sql/utils/charset/geostd8.py  |
| greek       | iso8859-7                         |
| hebrew      | iso8859-8                         |
| hp8         | ibd2sql/utils/charset/hp8.py      |
| keybcs2     | ibd2sql/utils/charset/keybcs2.py  |
| koi8r       | koi8-r                            |
| koi8u       | koi8-u                            |
| latin1      | latin1                            |
| latin2      | iso8859-2                         |
| latin5      | iso8859-9                         |
| latin7      | iso8859-13                        |
| macce       | mac-latin2                        |
| macroman    | macroman                          |
| sjis        | shift-jis                         |
| swe7        | ibd2sql/utils/charset/swe7.py     |
| tis620      | ibd2sql/utils/charset/tis620.py   |
| ucs2        | utf-16-be                         |
| ujis        | euc_jp                            |
| utf16       | utf-16-be                         |
| utf16le     | utf-16-le                         |
| utf32       | utf-32-be                         |
| utf8        | utf-8                             |
| utf8mb4     | utf-8                             |



# 支持解析的对象

支持mysql的innodb存储引擎的数据文件:

支持正常的ibd文件解析.

支持ibd文件"不完整"的解析.

支持ibd文件坏块的解析.

支持delete数据的恢复.

支持磁盘级别的扫描, 即支持drop,truncate等数据的恢复, 也支持操作系统层面rm数据文件/目录的恢复.

