本文为[ibd2sql](https://github.com/ddcw/ibd2sql)的完整使用方法



# 参数

```shell
SHELL>python3 main.py --help
usage: main.py [--help] [--version] [--ddl] [--sql] [--delete]
               [--complete-insert] [--force] [--set] [--multi-value]
               [--replace] [--table TABLE_NAME] [--schema SCHEMA_NAME]
               [--sdi-table SDI_TABLE] [--where-trx WHERE_TRX]
               [--where-rollptr WHERE_ROLLPTR] [--limit LIMIT] [--debug]
               [--debug-file DEBUG_FILE] [--page-min PAGE_MIN]
               [--page-max PAGE_MAX] [--page-start PAGE_START]
               [--page-count PAGE_COUNT] [--page-skip PAGE_SKIP] [--mysql5]
               [FILENAME]

解析mysql 5.7/8.0的ibd文件 https://github.com/ddcw/ibd2sql

positional arguments:
  FILENAME              ibd filename

optional arguments:
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
  --mysql5              for mysql5.7 flag
Example:
ibd2sql /data/db1/xxx.ibd --ddl --sql
ibd2sql /data/db1/xxx.ibd --delete --sql
ibd2sql /data/db1/xxx#p#p1.ibd --sdi-table /data/db1/xxx#p#p0.ibd --sql
ibd2sql /mysql57/db1/xxx.ibd --sdi-table /mysql80/db1/xxx.ibd --sql --mysql5
```

FILENAME 目标文件, 即要解析的ibd文件

`--help` 仅打印帮助信息,不做任何操作

`--version` 仅展示版本信息, 不做任何操作

`--ddl` 打印目标文件的DDL信息.

`--sql` 打印目标文件的数据, 并拼接为SQL语句

`--delete` 打印目标文件被标记为deleted的数据, 需要和`--sql`联合使用.

`--complete-insert ` 打印的SQL语句更完整, 即增加字段信息(某些数据库需要字段信息)

`--force` 对于某些可能报错的场景可以使用此选项跳过. 目前无实际使用场景.

`--set` 本来是对set/enum的值取int还是实际值, 现默认启用. 故此参数无效

`--multi-value` 对于生成的INSERT语句, 按照每页作为一个SQL语句. 即insert into table values(),(),();

`--replace` 使用replace语句代替insert语句. 和`--multi-value`冲突

`--table` 使用指定的表名替代元数据信息中的表名.

`--schema` 使用指定的库名替代元数据中的库名.

`--sdi-table` 指定元数据表文件. 对于5.x和分区表这种元数据信息不在指定的目标文件中, 则需要单独指定元数据文件.

`--where-trx` 指定事务范围. 默认(0,281474976710656)

`--where-rollptr` 指定回滚指针范围. 默认(0,72057594037927936)

`--limit` 仅打印N行数据.  同DML中的limit.

`--debug` 使用DEBUG功能, 会生成大量的解析日志信息. 

`--debug-file` 当启用debug功能时, 可使用此选项指定debug日志文件. 默认stdout

`--page-min` 如果正在解析的页号小于这个值, 则跳过该页.

`--page-max` 如果正在解析的页号大于这个值, 则跳过.

`--page-start` 指定第一个数据页(叶子节点). 方便跳过坏块.

`--page-count` 解析的页数量. 通常和`--page-start`联合使用.

`--page-skip` 跳过的页数量.

`--mysql5` 如果是mysql 5.6/5.7 除了指定`--sdi-table`选项外, 还应指定这个选项, 方便ibd2sql失败为mysql5的数据文件.

`--keyring-file` 指定keyring file文件(如果ibd文件加密了的话,就使用该选项)



# 使用例子

为了方便展示, 如下使用xxx.ibd文件来代替实际的ibd文件, 实际解析的时候需要 `相对`/`绝对`路径.

未特别说明的场景, 均是指mysql 8.x环境.

## 解析出表结构(DDL)

```shell
python3 main.py xxx.ibd --ddl
```



## 解析出数据(DML)

```shell
python3 main.py xxx.ibd --sql
```



## 解析表数据(DDL+DML)

```shell
python3 main.py xxx.ibd --ddl --sql
```



## 解析被误删的数据

```shell
python3 main.py xxx.ibd --sql --delete
```



## 分区表解析

分区表需要指定元数据信息

```shell
python3 main.py /data/mysql_3314/mysqldata/ibd2sql/ddcw_partition_range#p#p1.ibd --sql --sdi-table /data/mysql_3314/mysqldata/ibd2sql/ddcw_partition_range#p#p0.ibd
```




## ibd文件损坏的场景

ibd文件损坏(有坏块), ibd文件不完整, delete_flag的整个页都不在btree+中等情况, 可以使用`--force`解析数据

```shell
python3 main.py /data/xxx.ibd --ddl --sql --force
```


## 恢复drop的表
**目前只支持xfs文件系统的恢复**, 当不小心drop表之后, 应尽可能减少数据的写入. 文件/inode被重写了就无法恢复了.
**drop表之后,尽量不要马上又创建一样的表,可能存在inode复用的问题.**
用法如下:
```shell
# 扫描被删除的表 (/dev/sdb为数据文件所在文件系统, 如果是lv,则应该类似:/dev/mapper/centos-root)
python3 xfs_recovery_v0.2.py /dev/vdb  # `df /data/mysql_3306/mysqldata/db1` 可查看某目录对应的文件系统

# 查看对应inode的信息(可选,用来辅助判断的,indoeno来自上1条命令)
python3 xfs_recovery_v0.2.py /dev/vdb 123456

# 恢复某inode的数据到/tmp/new_table.ibd
python3 xfs_recovery_v0.2.py /dev/vdb 123456 /tmp/new_table.ibd

# 解析出相关DDL (5.7的话,就没法了... 除非应用有相关DDL)
python3 main.py /tmp/new_table.ibd --ddl

# 创建一样的表并导入数据库alter table import tablespace  (2选1)
# 或者解析出sql语句导入数据库 (2选1)
```

例子: (我这里没啥IO,刷盘慢,所以执行了partprobe, 实际情况建议先别跑,不然inode可能会被回收)
```shell
[root@VM-32-12-centos ibd2sql-main]# mysql -h127.0.0.1 -p123456 -e 'drop table db1.sbtest1111'
mysql: [Warning] Using a password on the command line interface can be insecure.
[root@VM-32-12-centos ibd2sql-main]# partprobe /dev/vdb
[root@VM-32-12-centos ibd2sql-main]# python3 xfs_recovery_v0.2.py /dev/vdb
inode: 50331714
inode: 50331715
inode: 50331716
inode: 50331718
inode: 50331719
inode: 50331720
inode: 50331723
inode: 67108945
inode: 83886157
inode: 83886158
inode: 83886159
inode: 150995009
inode:234924935 filename:db1.sbtest100.ibd
inode:235747986 filename:db1.sbtest1234.ibd
[root@VM-32-12-centos ibd2sql-main]# python3 xfs_recovery_v0.2.py /dev/vdb 235747986 /tmp/sbtest1234.ibd
[root@VM-32-12-centos ibd2sql-main]# python3 main.py /tmp/sbtest1234.ibd --ddl
CREATE TABLE IF NOT EXISTS `db1`.`sbtest1234`(
    `id` int NOT NULL AUTO_INCREMENT,
    `k` int NOT NULL DEFAULT '0',
    `c` char(120) NOT NULL DEFAULT '',
    `pad` char(60) NOT NULL DEFAULT '',
    PRIMARY KEY  (`id`),
    KEY `k_1234` (`k`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci ;
[root@VM-32-12-centos ibd2sql-main]# 

```









# 修改lower_case_table_names 参数
```shell
# 查看
python3 modify_lower_case_table_names.py /data/mysql_3314/mysqldata/mysql.ibd

# 修改 lower_case_table_names为1 并保存到/tmp/new_mysql.ibd
python3 modify_lower_case_table_names.py /data/mysql_3314/mysqldata/mysql.ibd /tmp/new_mysql.ibd 1
# 然后就是停库并更换mysql.ibd文件, 并启动(同时得修改参数文件里面的值, 不然会报错不一致... MY-011087)
```
