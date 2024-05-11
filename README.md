# 介绍

​	**ibd2sql**  是使用python3 编写的 提取**mysql 5.7/8.0** innodb存储引擎在磁盘上的 ibd 文件信息为**SQL语句**的工具. 

不需要连接数据库, 只需要对目录ibd文件有可读权限即可. 无第三方依赖包, **纯python3代码**. 使用**GPL-3.0** license.

​	[博客介绍](https://cloud.tencent.com/developer/article/2377921)

​	[视频介绍](https://www.bilibili.com/video/BV1HK411a7DJ)

​	[旧版README](https://github.com/ddcw/ibd2sql/blob/main/README_OLD.md)



# 功能特点:

1. **方便**: 提取表DDL
2. **实用**: 可替换库(--schema)/表(--table)名, 可在sql语句中输出完整的字段(--complete)
3. **简单**: 纯python3代码编写, **无依赖包**.  还可以使用**--debug**查看解析过程
4. **选择性强**: 可以根据条件过滤符合要求的数据 --where , --limit
5. **支持众多数据类型**: 支持**所有mysql数据类型** (比如 int, decimal, date, varchar, char, **json**, binary, enum, set, blob/text, longblob,空间坐标等).
6. **支持复杂的表结构**: 分区表, 注释, 主键, 外键, 约束, 自增, 普通索引, 前缀索引, 主键前缀索引, 唯一索引, 复合索引, 默认值, 符号, 虚拟字段, INSTANT, 无主键等情况的表
7. **数据误删恢复**: 可以输出被标记为deleted的数据
8. **安全**: 离线解析ibd文件, 仅可读权限即可
9. **支持范围广**: 支持mysql 5.7 or 8.x


# 安装下载

最新版: [https://github.com/ddcw/ibd2sql/archive/refs/heads/main.zip](https://github.com/ddcw/ibd2sql/archive/refs/heads/main.zip)

次新版: [https://github.com/ddcw/ibd2sql/archive/refs/tags/v1.2.tar.gz](https://github.com/ddcw/ibd2sql/archive/refs/tags/v1.2.tar.gz)



# 使用例子 (8.0)

可使用 `python3 main.py -h` 查看帮助信息

```shell
SHELL>python3 main.py -h
usage: main.py [--help] [--version] [--ddl] [--sql] [--delete] [--complete-insert] [--force] [--set] [--multi-value]
               [--replace] [--table TABLE_NAME] [--schema SCHEMA_NAME] [--sdi-table SDI_TABLE] [--where-trx WHERE_TRX]
               [--where-rollptr WHERE_ROLLPTR] [--limit LIMIT] [--debug] [--debug-file DEBUG_FILE] [--page-min PAGE_MIN]
               [--page-max PAGE_MAX] [--page-start PAGE_START] [--page-count PAGE_COUNT] [--page-skip PAGE_SKIP]
               [FILENAME]

解析mysql 5.7/8.0的ibd文件 https://github.com/ddcw/ibd2sql

positional arguments:
  FILENAME              ibd filename

options:
  --help, -h            show help
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
Example:
ibd2sql /data/db1/xxx.ibd --ddl --sql
ibd2sql /data/db1/xxx.ibd --delete --sql
ibd2sql /data/db1/xxx#p#p1.ibd --sdi-table /data/db1/xxx#p#p0.ibd --delete --sql
```



## 提取建表语句 DDL

**--ddl** 

```shell
python3 main.py /data/mysql_3314/mysqldata/ibd2sql/ddcw_alltype_table.ibd --ddl
```



## 提取数据 DML/INSERT

**--sql**

```shell
python3 main.py /data/mysql_3314/mysqldata/ibd2sql/ddcw_alltype_table.ibd --sql  
```

binary数据会被转为 base64

set/enum会被替换为实际值(v0.3版本是使用数字表示)



## 提取误删数据 (被标记为delete的数据)

**--sql --delete**

```shell
SHELL> python3 main.py /data/mysql_3314/mysqldata/ibd2sql/ddcw_alltype_table.ibd --sql --delete
```



## 提取分区表数据

**--sdi-table  xxx#p0.ibd**

```shell
SHELL> python3 main.py /data/mysql_3314/mysqldata/ibd2sql/ddcw_partition_hash#p#p3.ibd --sdi-table /data/mysql_3314/mysqldata/ibd2sql/ddcw_partition_hash#p#p0.ibd  --sql
```



## 完整字段信息

**--complete**

```shell
SHELL> python3 main.py /data/mysql_3314/mysqldata/ibd2sql/ddcw_alltype_table.ibd --sql --complete 
```



# 使用例子(5.7)

`--mysql5` 用来标识这是一个mysql5的ibd文件. 不然就不做解析.

由于5.7的ibd文件没得sdi_page, 得解析frm文件获取元数据信息,  虽然也[解析过frm](https://cloud.tencent.com/developer/article/2409341)结构, 但我懒得去写了. 就直接沿用8.0的sdi吧.   故 解析 5.7的ibd文件 需要先使用 `mysqlfrm`提取出DDL, 并插入到8.0的环境里面, 然后再使用本工具来解析5.7的ibd文件

```shell
# 提取出DDL 
mysqlfrm /data/mysql_3308/mysqldata/db1/ddcw_alltype_table.frm --diagnostic 

# 然后导入到8.0环境(以获取SDI信息.)
....

# 就可以使用本工具解析了
python3 main.py --sdi-table /data/mysql_3314/mysqldata/ibd2sql/ddcw_alltype_table.ibd /data/mysql_3308/mysqldata/db1/ddcw_alltype_table.ibd  --sql --mysql5
```





# CHANGE LOG

| 版本   | 变更时间       | 说明                     | 备注                                       |
| ---- | ---------- | ---------------------- | ---------------------------------------- |
| v0.1 | 2023.4.27  | 第一个版本....              |                                          |
| v0.2 | 2023.08.30 | 支持更多数据类型               | 1. 修复year/tinyint的支持<br />2. 符号支持(对于数字类型)<br />3. 更多的数据类型支持<br />4. 更多的表属性支持<br />5. 美化输出<br />6. 支持表名替换<br />7. 支持--complete-insert |
| v0.3 | 2023.10.13 | 支持5.7升级到8.0的ibd文件      | 修复一些BUG                                  |
| v1.0 | 2024.01.05 | 支持debug<br />支持更多类型和功能 | 1. 支持DEBUG<br />2. 支持分区表<br />3. 支持唯一索引<br />4.支持虚拟列<br />5. 支持instant<br />6.支持约束和外键<br />7. 支持限制输出<br />8.支持前缀索引 |
| v1.1 | 2024.04.12 | 修复一些bug                | 1. 8.0.13 默认值时间戳<br />2. 8.0.12 无hidden<br />3. online ddl instant |
| v1.2 | 2024.04.25 | 新增空间坐标的支持              | 支持geometry\[collection\],\[multi\]point,\[multi\]linestring,\[multi\]polygon |
| v1.3 | 2024.05.11 | 支持mysql 5.7            | 本来准备做二级分区支持的,  但看了下, WC, 太复杂了-_- 那就更新个支持5.7的吧(其实结构和8.0是差不多的) (for issue 7) |



# BUG修复

1. [前缀索引](https://www.modb.pro/db/1700402156981538816)支持. 前缀索引完整数据在数据字段而不是KEY
2. [json/blob等大对象](https://www.modb.pro/db/626066)支持:  支持非溢出页的大对象
3. [5.7升级到8.0后找不到SDI](https://github.com/ddcw/ibd2sql/issues/5). :sdi pagno 记录在第一页
4. [bigint类型,注释,表属性](https://github.com/ddcw/ibd2sql/issues/2) : 支持更多数据类型, 和表属性
5. [只有1个主键和其它](https://github.com/ddcw/ibd2sql/issues/4) : 支持只有1个主键的情况, 并新增DEBUG功能
6. [默认值为时间戳](https://github.com/ddcw/ibd2sql/issues/8) : 支持默认值为时间戳, blob等字段的前缀索引
7. [8.0.12 无hidden](https://github.com/ddcw/ibd2sql/issues/10) : 取消hidden检查
8. [ONLINE DDL instant](https://github.com/ddcw/ibd2sql/issues/12) : record 1-2 bit is instant flag





# 支持范围

环境要求:  python3 

对象支持:  mysql 5.7/8.x 所有数据类型

如下情况不支持:

1. DDL二级分区 (不支持)
2. 溢出页 (默认置为null)
3. 不支持一张表存在多个字符集, 其实只支持utf8





# 为什么使用ibdsql

1. 学习python3

   只是单纯的学习python3代码编写. 本工具使用的纯python3编写的, 无第三方依赖包, 适合学习python3

   ​

2.  学习mysql

   学习mysql的底层原理, innodb 各种数据类型在磁盘上的格式. 比如知道page_id为4字节, 就能计算出单个ibd文件的最大为 PAGE_SIZE\*PAGE_ID_MAX = 16KB\*(2^32)=64TB

   直接阅读源码的话, 难度太大. 就可以使用本工具 `--debug` 功能查看ibd解析过程. 还可以搭配`--page-min --page-max --page-start --page-count --page-skip`一起使用 

   ​

3. 数据恢复

   比如不小心删除了某个ibd文件, 但好歹从磁盘上恢复出来了, 但不知道表结构, 就可以使用 --ddl 查看表结构了.

   或者不小心 delete了某些数据, 但又没开启binlog, 就可以使用 `--delete` 查看误删的数据了.

   ​

4.  其它

   ​	想看下第一行数据是啥, 登录数据库太麻烦了, 就可以 `--sql --limit 1`

   ​	想看下在某个事务之后跟新的数据信息, 可以使用 --where-trx=(start_trx, end_trx) 查看在这个限制内更新的数据信息了.

   ​	想导出数据到其它环境, 比如 `python main.py --limit 10 xxx.ibd --schema xxxx | mysql `

   ​	查看表结构 `python main.py --ddl`

   ​
