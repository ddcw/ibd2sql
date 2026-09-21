本文为ibd2sql的一些基础使用方法. 不含恢复drop/truncate/rm/delete等数据的方法, 主要为帮助读者理解ibd2sql各选项的使用及其搭配.



# DDL

我们知道表的元数据信息存储在ibd文件或者frm(5.x)文件中,根据元数据信息就可以拼接为对应的DDL.

获取表的DDL主要使用`--ddl`选项. 使用可参考如下:

```shell
# 查看DDL(什么选项都没有的时候就默认查看DDL)
python3 main.py /data/mysql_8037/mysqldata/db1/t20260920.ibd

# 查看DDL
python3 main.py /data/mysql_8037/mysqldata/db1/t20260920.ibd --ddl

# 获取DDL并查看历史DDL
python3 main.py /data/mysql_8037/mysqldata/db1/t20260920.ibd --ddl history

# 获取DDL但不显示索引信息
python3 main.py /data/mysql_8037/mysqldata/db1/t20260920.ibd --ddl disable-keys

# 获取DDL并单独输出创建索引的语句
python3 main.py /data/mysql_8037/mysqldata/db1/t20260920.ibd --ddl keys-after

# 获取DDL但不显示外键信息
python3 main.py /data/mysql_8037/mysqldata/db1/t20260920.ibd --ddl --set disable-foreign-keys

# 获取DDL并单独输出alter约束语句
python3 main.py /data/mysql_8037/mysqldata/db1/t20260920.ibd --ddl --set foreign-keys-after

# 获取DDL,并单独输出创建索引和外键约束的语句
python3 main.py /data/mysql_8037/mysqldata/db1/t20260920.ibd --ddl keys-after --set foreign-keys-after
```



## 元数据信息位于ibd文件中

对于mysql 8.x,9.x版本元数据位于ibd文件中,直接跟上数据文件(ibd)和`--ddl`即可:

```shell
# 解析mysql 8.x版本的数据文件并生成DDL
python3 main.py /data/mysql_8037/mysqldata/db1/t20260920.ibd --ddl
```



## 元数据信息位于frm中

对于mysql 5.x版本的元数据信息位于frm文件中,为了方便使用,我们是自动识别的. 故使用方法还是一样的.

```shell
# 获取5.x版本的DDL(要求同目录下有同名的frm文件,否则需要使用--sdi指定)
python3 main.py /data/mysql_5744/mysqldata/db1/t20260920.ibd --ddl
```



## 手动指定元数据信息

如果未能自动识别元数据信息或者元数据信息不存在于目标文件中, 则可以手动指定需要使用的元数据信息文件.

```shell
python3 main.py t20260920.ibd --sdi-table /data/mysql_8037/mysqldata/db1/t20260920.ibd
```

> 注意: 会优先使用目标文件同目录下的同名frm文件,即使使用了--sdi



## 元数据文件位于系统表中

系统表(5.x使用ibdata1,8.x使用mysql.ibd)也记录了表的元数据信息, 所以我们也可以从系统表中获取业务表的DDL.

```shell
# --set deleted=only   (默认)系统表中仅包含被deleted的行信息,即只考虑被drop的表
# --set deleted=with   系统表中包含未被delete和被deleted行信息,即同时考虑未被drop和被drop的表
# --set deleted=except 排除系统表中未被delete的表, 即不考虑被drop的表
# 由于系统表中记录的业务表很多, 所以建议使用--set table=tblname来过滤指定的表名
# 8.x 从系统表获取业务表的DDL
python3 main.py /data/mysql_8037/mysqldata/mysql.ibd --scan --set deleted=with --ddl --set table=t20260920

# 8.x drop业务表之后,从系统表中恢复业务表的DDL
python3 main.py /data/mysql_8037/mysqldata/mysql.ibd --scan --set deleted=only --ddl --set table=t20260920

# 5.x 从系统表获取业务表的DDL
python3 main.py /data/mysql_5744/mysqldata/ibdata1 --scan --set deleted=with --ddl --set table=t20260920

# 5.x drop业务表之后,从系统表中恢复业务表的DDL
python3 main.py /data/mysql_5744/mysqldata/ibdata1 --scan --set deleted=only --ddl --set table=t20260920
```



## 分区表

5.x版本元数据是放在frm中的,所以无需关心. 但8.x版本是元数据信息是放在ibd文件中的,每个分区都是一个ibd文件,元数据信息是放在第一个ibd文件中的.默认自动识别使用第一个ibd文件,使用者无需关心.

```shell
python3 main.py /data/mysql_8037/mysqldata/db1/k1#p#p1.ibd --ddl
```



# DML(SQL)

有了元数据信息之后,我们就可以解析数据文件了.主要使用`--sql`选项, 输出可以是sql语句,也可以是data格式(方便load). 5.x和8.x使用是一样的,所以我们就以8.x版本为例来介绍了.

```shell
# 获取SQL,并输出到屏幕
python3 main.py /data/mysql_8037/mysqldata/db1/t20260920.ibd --sql

# 获取SQL和DDL,并输出到屏幕
python3 main.py /data/mysql_8037/mysqldata/db1/t20260920.ibd --sql --ddl

# 获取SQL,并输出到指定文件
python3 main.py /data/mysql_8037/mysqldata/db1/t20260920.ibd --sql > /tmp/xxx.sql

# 获取SQL,并自动输出到文件
python3 main.py /data/mysql_8037/mysqldata/db1/t20260920.ibd --sql --output

# 获取SQL,并输出到指定目录
python3 main.py /data/mysql_8037/mysqldata/db1/t20260920.ibd --sql --output /tmp

# 获取SQL,并输出到指定目录,并限制单个文件的大小(字节)
python3 main.py /data/mysql_8037/mysqldata/db1/t20260920.ibd --sql --output /tmp --output-filesize=1000000

# 使用8个进程并发解析,获取SQL,并输出到指定目录
python3 main.py /data/mysql_8037/mysqldata/db1/t20260920.ibd --sql --output /tmp --parallel 8

# 获取数据
python3 main.py /data/mysql_8037/mysqldata/db1/t20260920.ibd --sql data

# 获取数据,并指定字段分隔符
python3 main.py /data/mysql_8037/mysqldata/db1/t20260920.ibd --sql data --set fields-terminated-by='|'

# 获取数据,并输出到目录(会额外生成对应的load参考语句)
python3 main.py /data/mysql_8037/mysqldata/db1/t20260920.ibd --sql data --set fields-terminated-by='|' --output

# 获取SQL,并使用replace语句替换insert
python3 main.py /data/mysql_8037/mysqldata/db1/t20260920.ibd --sql --replace

# 获取SQL,并使用replace语句替换insert,且包含字段名
python3 main.py /data/mysql_8037/mysqldata/db1/t20260920.ibd --sql --replace --complete-insert

# 获取SQL,仅输出被delete的数据
python3 main.py /data/mysql_8037/mysqldata/db1/t20260920.ibd --sql --delete

# 获取SQL,仅输出被delete的数据,且包含不在btr+但在ibd中的数据页
python3 main.py /data/mysql_8037/mysqldata/db1/t20260920.ibd --sql --delete --force

# 获取SQL,输出未被delete和被delete的数据
python3 main.py /data/mysql_8037/mysqldata/db1/t20260920.ibd --sql --delete with

# 获取SQL,输出未被delete和被delete的数据,使用replace代替insert
python3 main.py /data/mysql_8037/mysqldata/db1/t20260920.ibd --sql --delete with --replace

# 获取SQL,合并多行数据为一行(insert value,value)
python3 main.py /data/mysql_8037/mysqldata/db1/t20260920.ibd --sql --multi-value

# 获取mysql.ibd中的系统表mysql.user数据
python3 main.py /data/mysql_8037/mysqldata/mysql.ibd --sql --set table=user

# 获取mysql.ibd中的系统表mysql.user中被delete的数据.(就是被drop的user)
python3 main.py /data/mysql_8037/mysqldata/mysql.ibd --sql --set table=user --delete

# 获取ibdata1中的系统表sys_tables中被delete的数据(被drop的表的信息)
python3 main.py /data/mysql_5744/mysqldata/ibdata1 --sql --set table=sys_tables --delete
```

搭配方式非常多,请使用者根据自己需求自行搭配.



# WEB

生成web服务,可使用浏览器查看对应的btr+

```shell
# 使用web查看指定表
python3 main.py /data/mysql_8037/mysqldata/db1/t20260920.ibd --web

# 使用web查看多张表
python3 main.py /data/mysql_8037/mysqldata/db1/* --web

# 使用web查看系统表(8.x)
python3 main.py /data/mysql_8037/mysqldata/mysql.ibd --web

# 使用web查看系统表(5.x)
python3 main.py /data/mysql_5744/mysqldata/ibdata1 --web

# 生成web的时候指定ip和端口
python3 main.py /data/mysql_8037/mysqldata/db1/t20260920.ibd --web --set host=192.168.101.21 --set port=8000
```





# 查看修改lower_case_table_name参数

mysql 8.x版本中lower_case_table_name参数在系统表文件mysql.ibd中存在相关记录, 我们可以使用本工具对其进行查看与修改

```shell
# 查看lower_case_table_name
python3 main.py /data/mysql_8037/mysqldata/mysql.ibd --lctn

# 设置lower_case_table_name.
python3 main.py /data/mysql_8037/mysqldata/mysql.ibd --lctn 1
# 这里只是修改系统表中的lower_case_table_name, 实际使用还需要修改配置文件中的lower_case_table_name并重启,在此之前还需要检查当前环境的表是否满足修改之后的要求. 请谨慎修改!!!
```









