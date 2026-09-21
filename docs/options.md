本文介绍ibd2sql v2.x各选项含义.

各选项可按照自己的需求搭配使用.

使用的python3中的argparse实现的选项功能,所以是支持简写的. 比如`--scan-device`可以简写为`--scan`

# 核心选项

核心选项主要是控制输出内容的.

## --ddl

控制是否输出DDL语句. 可选值有: history,disable-keys,keys-after

```txt
--ddl               完整的建表语句
--ddl history       显示ddl历史执行情况(only instant)
--ddl disable-keys  不显示DDL中的索引信息(排除主键)
--ddl keys-after    将单独使用alter table tblname add key的形式出现(若搭配--sql,则在insert语句之后)
```



## --sql

控制是否输出DML(数据),可选值有:sql,data

```txt
--sql      输出insert语句
--sql sql  输出insert语句
--sql data 输出按照指定字符分割的数据, 方便使用load data导入
```



## --delete

控制是否输出被标记为deleted的数据(默认启用`--sql sql`,即固定输出为insert格式).

> mysql中delete表,只是打上一个deleted标记,而不会马上删除,所以我们是可以输出这部分数据的.

可选值有:only,with

```txt
--delete      仅输出被标记为deleted的数据
--delete only 仅输出被标记为deleted的数据
--delete with 先输出被标记为deleted的数据,再输出未被标记为deleted的数据.
```





# 优化选项

优化选项可以使输出内容更"友好".

## --complete-insert

当使用`--sql`时,控制输出的insert语句是否包含字段名.



## --multi-value

当使用`--sql`时,控制将多条数据放入一条insert语句中.



## --replace

当使用`--sql`时,控制是否使用`replace into`代替`insert into`语句.  与`--multi-value`冲突



## --force

默认遍历btr+,使用此选项则遍历整个数据文件.

当解析ibd文件的时候,默认按照叶子节点的FIL_PAGE_NEXT进行遍历; 若使用此选项则从起始位置往后完整遍历整个数据文件.

比如: 当前页号为4(PAGEID=4),下一页为12(FIL_PAGE_NEXT=12), 则不使用此选项时,此页解析完成后,会解析页号为12的页; 若使用此选项(--force),则会解析页号为5的页.

使用场景: 

1. 当delete数据时,若该页数据全部被标记为deleted,则该页会被移除btr+,即正常遍历btr+无法找到该页, 此时就可以使用--force遍历完整的ibd文件.
2. 当ibd文件不是按照btr+构成的(可能文件不完整,损坏,或者仅有索引页,或者其它工具恢复的部分文件),则可以使用此选项遍历数据文件.



## --schema

使用此选项指定的库名替换DDL和DML中的库名.

```txt
--schema db1 使用db1替换原本的库名
```



## --table

使用此选项指定的表名替换DDL和DML中的表名.

```txt
--table t1 使用t1替换原本的表名
```



## --sdi-table

指定需要使用的元数据信息来源, 支持ibd,frm,sdi格式.

若解析的对象无元数据信息,也未能自动识别到元数据信息, 则可以使用此选项指定元数据信息来源(无元数据信息则无法解析ibd文件)

由于mysql 5.x版本使用frm存储ibd的元数据信息, 所以本工具(ibd2sql)会自动(在同目录下)寻找同名的frm文件作为元数据信息来源,优先级高于--sdi-table选项.

分区表的元数据信息在第一个分区,默认是能自动识别的.

```txt
--sdi-table t1.ibd 使用t1.ibd中的元数据信息替换原本的元数据信息.
```



## --limit

控制输出的行数. 

```txt
--limit 10 输出前10行数据
```



## --keyring-file

若使用了加密,则需要使用此选项指定密钥文件.

```txt
--keyring-file /usr/local/mysql/keyring/keyring
```



## --output

控制输出目录.

```txt
--output           在当前目录生成ibd2sql_auto_dir_开头的目录用于存放输出的sql/ddl文件
--output /tmp/test 在指定目录(/tmp/test)生成schema.table{_p}_pid_sql.sql文件
```



## --output-filesize

控制输出文件的大小(单位:字节). 需要和`--output`搭配使用.

若输出文件太大,不方便查看或者转移等,则可以使用此选项限制输出文件的大小. 同时也方便并行导入.

```txt
shell> python3 main.py /data/mysql_3314/mysqldata/db1/sbtest4.ibd --ddl --sql --output --output-filesize=10485760
output dir: ibd2sql_auto_dir_20260917_150136
DDL filename: ibd2sql_auto_dir_20260917_150136/db1.sbtest4_22436_ddl.sql
SQL filename, ibd2sql_auto_dir_20260917_150136/db1.sbtest4_22436_sql.sql

shell> ls -l ibd2sql_auto_dir_20260917_150136
total 42088
-rw-r--r-- 1 root root      346 Sep 17 15:01 db1.sbtest4_22436_ddl.sql
-rw-r--r-- 1 root root 10485955 Sep 17 15:01 db1.sbtest4_22436_sql.sql.p00000000
-rw-r--r-- 1 root root 10485791 Sep 17 15:01 db1.sbtest4_22436_sql.sql.p00000001
-rw-r--r-- 1 root root 10485832 Sep 17 15:01 db1.sbtest4_22436_sql.sql.p00000002
-rw-r--r-- 1 root root 10485886 Sep 17 15:01 db1.sbtest4_22436_sql.sql.p00000003
-rw-r--r-- 1 root root  1130761 Sep 17 15:01 db1.sbtest4_22436_sql.sql.p00000004
```



## --parallel

指定并发数量.

默认是单进程解析ibd文件,如果遇到大文件/磁盘,则速度可能会比较慢,此时就可以使用并发来提高速度(基本上满足线下提升)

```txt
--parallel 8 使用8个进程来解析数据
```



## --log

控制是否输出日志.

```txt
--log         输出日志到当前屏幕
--log xxx.log 输出日志到xxx.log中
```



# 扩展选项

为了方便使用,我们还支持很多扩展选项. 均使用--set来实现. 格式为: `--set K=V` 不同的set可以搭配使用.

此选项的k非常非常非常非常多(有些甚至都忘记实现/传参了).我们逐一介绍:

## --set table

表名过滤.

如果输入有多张表(多个ibd文件,或者一个ibd文件里面有多张表), 则可以使用此选项匹配需要的表.

```txt
# 只输出mysql.ibd中的user表信息
python3 main.py mysql.ibd --set table=user 
```



## --set leafno

指定起始的叶子节点. 即第一行数据的pageno. 如果ibd文件不正常,则需要使用此选项指定第一个叶子节点的pageno.

默认会自动从root节点开始寻找第一个叶子节点

```txt
python3 main.py xx.ibd --set leafno=4
```



## --set rootno

指定第一个root节点.btr+的最上层的第一个节点.

```txt
python3 main.py xx.ibd --set rootno=4
```



## --set hex

输出的数据不做解码,直接将二进制数据转为16进制的形式输出.(二进制类型的字段(比如blob)固定为16进制格式输出) 

```txt
python3 main.py xx.ibd --set hex
```



## --set foreign-keys-after

输出的DDL中外键约束以alter table add constraint的形式添加

```txt
python3 main.py xx.ibd --set foreign-keys-after
```



## --set disable-foreign-keys

输出的DDL中,禁用外键约束

```txt
python3 main.py xx.ibd --set disable-foreign-keys
```



## --set host

当使用--web时, 可以使用此选项指定监听的IP.



## --set port

当使用--web时, 可以使用此选项指定监听的端口.



## --set bad-pages

当遇到坏块时的处理方式. 有3种:skip,try,fast

```txt
--set bad-pages=fast 根据page-directory信息尽可能的解析坏块中的数据, 数据可能会多,也可能会少
--set bad-pages=try  一字节一字节的解析坏块中的数据, 会多出很多数据(表结构越简单,多的数据越多), 但不会差数据(有的都解析了)
--set bad-pages=skip 跳过坏块中的数据
```



## --set check-table-old

当需要校验是否坏块的时候,如果mysql版本较老的话,则需要使用此选项来启用老版本的块校验.

```txt
--set check-table-old
```

扫描磁盘和`--set bad-pages`时才会使用到.



## --set deleted

当扫描ibdata1/mysql.ibd的时候,是否需要考虑被标记为deleted的数据,有3种选择:only(default), except, with



## 扫描磁盘时才需要使用的参数

为了方便快速扫描磁盘, 我们提供了众多参数.

```txt
--set chunk-size   默认16777216,切片大小
--set buffer-size  默认1048576,缓存大小(每次读取的数据)
--set page-size    默认16384,innode页大小
--set block-size   默认4096,磁盘块大小,为了快速扫描,每次偏移按照块为单位
--set offset-start 默认0,起始位置
--set offset-stop  默认2**63,结束位置
--set with-sdi     默认False,即启用该功能
--set with-frm     默认False,即启用该功能 
```





# 其它选项

## --help

控制是否仅输出帮助信息



## --version

控制是否仅输出版本信息



## --print-sdi

控制是否仅输出sdi(存储元数据)信息. 对于frm文件也会转成sdi输出. 建议搭配jq等格式化工具使用.

```txt
--print-sdi 仅输出目标的sdi信息
```



## --count

控制是否仅输出ibd中的数据行数等信息.

```txt
python3 main.py sbtest1.ibd --count # 输入内容如下:
sbtest1.ibd	sbtest1	ROWS:1889945	ROWS(with deleted):1889965	TIME:0.1 seconds     FILE SIZE:940.0 MB
```



## --web

控制是否启用web控制台. 使用此选项后即可使用浏览器查看ibd文件的结构. 默认监听所有网段的8080端口.

```txt
--web                                            监听所有网段的8080端口,然后使用浏览器访问即可
--web --set host=127.0.0.1                       监听127.0.0.1的8080端口,然后使用浏览器访问即可
--web --set port=8000                            监听所有网段的8000端口,然后使用浏览器访问即可
--web --web --set host=127.0.0.1,port=8000       监听127.0.0.1的8000端口,然后使用浏览器访问即可
--web --web --set host=127.0.0.1 --set port=8000 监听127.0.0.1的8000端口,然后使用浏览器访问即可
```



## --lctn

控制是否输出/修改mysql.ibd中记录的lower_case_table_name值. 只能和mysql.ibd一起使用.

查看:

```txt
SHELL> python3 main.py /data/mysql_8030/mysqldata/mysql.ibd --lctn
current lower_case_table_name = 0
pageno: 330 offset: 735
```

我们还支持修改mysql.ibd中记录的lower_case_table_name的值:

```txt
SHELL> python3 main.py /data/mysql_8030/mysqldata/mysql.ibd --lctn 1
current lower_case_table_name = 0
pageno: 330 offset: 735
set lower_case_table_name = 1 success

SHELL> python3 main.py /data/mysql_8030/mysqldata/mysql.ibd --lctn
current lower_case_table_name = 1
pageno: 330 offset: 735
```



## --scan-device

指定扫描的磁盘设备. 此功能主要是用来进行磁盘级别的数据扫描,从而恢复数据的.. 建议和`--parallel`一起使用. 和不同的选项搭配能恢复不同层面的数据.

```txt
# 扫描/dev/vdb设备,恢复所有的mysql数据(page)
python3 main.py --scan /dev/vdb

# 查看/data2/mysql.ibd中被drop的表,并扫描磁盘/dev/vdc,并输出为SQL语句
python3 main.py /data2/mysql.ibd --scan /dev/vdc --sql

# 查看/data2/mysql.ibd中被drop的tblname表,并扫描磁盘/dev/vdc,并输出为SQL语句
python3 main.py /data2/mysql.ibd --scan /dev/vdc --sql --set table=tblname
```

此选项使用较为复杂, 请根据使用场景中的使用方法使用.

