本文档为ibd2sql 2.x的使用说明.

# 选项说明

ibd2sql 2.x核心用法和1.x版本保持一致, 新增/移除了部分功能,也对部分功能进行了微调. 总体使用方法依然是`python3 main.py FILENAME [options]`



目前支持5.7, 8.0. 8.4, 9.0版本. 对于分区表和frm将自动识别元数据信息,也可以使用`--sdi-table`手动指定.

移除了`--debug`,`--mysql5`选项.



## --help

显示帮助信息.

## --version

显示版本信息

## --ddl (微调)

显示相关表的DDL, 无任何其它选项时,默认依然是打印表的DDL信息. 为了方便使用, 新增了额外功能:

`--ddl history`: 显示DDL的历史情况, 只支持使用instant修改字段的情况, 比如:

```shell
-- create table db1.t20250830_test_ddl(id int, name varchar(200));
-- alter table db1.t20250830_test_ddl add column age int,ALGORITHM=INSTANT;
-- alter table db1.t20250830_test_ddl drop column name ,ALGORITHM=INSTANT;

<ibd2sql_2.x > python3 main.py /data/mysql_3414/mysqldata/db1/t20250830_test_ddl.ibd --ddl history
CREATE TABLE IF NOT EXISTS `db1`.`t20250830_test_ddl` (
  `id` int DEFAULT NULL,
  `name` varchar(200) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;
ALTER TABLE `db1`.`t20250830_test_ddl` ADD COLUMN `age` int DEFAULT NULL;
ALTER TABLE `db1`.`t20250830_test_ddl` DROP COLUMN `name`;
```

`--ddl disable-keys`: ddl中不含非主键的索引信息

`--ddl keys-after`: ddl中的索引将在最后以alter table add的形式添加.



## --sql (微调)

`--sql`依然为打印sql语句的选项, 但考虑到insert的速度问题, 故新增了额外功能:

`--sql data`: 输出不再是sql语句,而是可以使用`LOAD DATA`导入数据的文件格式. 默认字段使用`,`隔开, 行之间使用`\n`隔开, 可以使用`--set`指定为其它字符



## --delete (微调)

`--delete` 依然为打印被删除的数据行, 但是新增了选项功能:

`--delete only`: 仅打印被删除的数据, 也是--delete的默认选项

`--delete with`: 打印数据的同时还包含被标记为删除的数据.



## --complete-insert

INSERT语句包含字段名称信息



## --multi-value

按照每页为一条insert语句进行输出.



## --force

若使用该选项,将强制遍历整个数据文件. (默认为按照btr+叶子节点遍历)



## --replace

使用`REPLACE INTO`代替`INSERT INTO`



## --table

输出的表名替换为这个选项的值. 仅适合一张表的时候



## --schema

输出的表的schema替换为这个选项的值.



## --sdi-table

指定表的元数据信息, 当前版本为默认识别分区表和frm元数据信息, 若未识别到则使用此选项值.



## --limit

输出的数据行数(语句行数而非数据行数, 若使用了`--multi-value`则输出的是n页的数据)



## --keyring-file

指定keyring-file



## --output (新增)

指定输出目录

`--output` 将在当前目录下创建`ibd2sql_auto_dir_`开头的目录作为输出目录. 

`--ouput /tmp` 将在tmp目录创建`ibd2sql_auto_dir_`开头的目录作为输出目录.



## --output-filesize (新增)

输出文件若超过此选项值, 则自动进行轮转.



## --print-sdi (新增)

输出表的元数据信息, 同`ibd2sdi`



## --count

统计表的行数



## --web

启用web功能, 可在浏览器上以btr+的形式查看表的数据. 原`ibd2sql_web.py`的功能. 支持多个数据文件



## --lctn

查看/修改mysql.ibd中的`lower_case_table_names`选项的值.

`--lctn` 查看mysql.ibd中lower_case_table_names的值

`--lctn 1` 修改mysql.ibd中lower_case_table_names的值为1. 可选值为0,1,2

原`modify_lower_case_table_names.py`的功能

## --parallel (新增)

指定并发度, 当解析数据时,可以使用此选项指定并发度. 对于大表来说, 使用此选项可显著增加解析速度. 并发数量建议为cpu空闲数量.



## --log (新增)

输出日志

`--log` 将日志输出到stderr

`--log xxx.log` 将日志输出到xxx.log



## --set (新增)

一部分不那么重要但也不错的选项,就放这里了. 使用方法为:

```shell
--set 'k1=v,k2;k3=v' --set 'k4=v'
```

`--set='hex'` 输出的字段值将以16进制的形式展示.

`--set='leafno=4'` 指定叶子节点为4

`--set='schema=db1'` 对目标数据文件进行schema过滤, 若不为db1则跳过.

`--set='table=t1'` 对目标数据文件进行table过滤, 若不为t1则跳过





# 使用例子

解析数据文件,获取DDL和DML

```shell 
python3 main.py /data/mysql_3314/mysqldata/db1/sbtest2.ibd --sql --ddl
```



解析数据文件,获取DDL和DML, 使用8个进程并发解析

```
python3 main.py /data/mysql_3314/mysqldata/db1/sbtest2.ibd --sql --ddl --parallel 8
```



解析数据文件,获取DDL和DML, 使用8个进程并发解析 并输出到 '/tmp'目录

```shell
python3 main.py /data/mysql_3314/mysqldata/db1/sbtest2.ibd --sql --ddl --parallel 8 --output='/tmp'
```



强制解析目标数据文件

```shell
python3 main.py /data/mysql_3314/mysqldata/db1/sbtest2.ibd --sql --ddl --force
```



解析多个数据文件

```shell
python3 main.py /data/mysql_3314/mysqldata/db1/sbtest* --sql --ddl 
```



解析数据文件中被标记为删除的数据

```shell
python3 main.py /data/mysql_3314/mysqldata/db1/sbtest2.ibd --sql --delete
```



解析数据文件并输出为data模式, 方便使用load data导入

```shell
python3 main.py /data/mysql_3314/mysqldata/db1/sbtest2.ibd --sql data
```



查看目标文件的sdi信息

```shell
python3 main.py /data/mysql_3314/mysqldata/db1/sbtest2.ibd --print-sdi
```



查看目标文件指定表的信息

```shell
python3 main.py /data/mysql_3314/mysqldata/mysql.ibd --set='table=user' --ddl --sql
```



以web控制台展示

```shell
python3 main.py /data/mysql_3314/mysqldata/mysql.ibd --web
```



查看mysql.ibd中记录的lower_case_table_names值

```shell
python3 main.py /data/mysql_3314/mysqldata/mysql.ibd --lctn
```

# 碎片页/坏块/ibd文件损坏
对于碎片页,坏块,ibd文件损坏,不完整等各种情况, 我们还可以解析出剩余数据. 只需要使用`--set rootno=0 --set leafno=0 --force`即可,当然大概率也是需要使用`--sdi`指定元数据信息的.
```shell
python3 main.py /tmp/t20250908_test_4_pages.ibd --sdi /data/mysql_3308/mysqldata/db1/sbtest2.frm  --sql --set leafno=0 --set rootno=0 --force
```

当然并发等选项也是可以的
```shell
python3 main.py /tmp/t20250908_test_4_pages.ibd --sdi /data/mysql_3308/mysqldata/db1/sbtest2.frm  --sql --set leafno=0 --set rootno=0 --force --parallel 4
```

如果针对undrop-for-innodb解析的page信息,则可以使用如下方法
```shell
python3 main.py /PATH/pages-vda1/ --sdi /PATH/t20250912_2.frm --set indexid=22 --sql
```
indexid=22 是对应 的/PATH/pages-vda1/FIL_PAGE_INDEX/0000000000000022.page 文件中的22(indexid)

# 强制从坏块中提取数据
对于坏块我们提供了3种选择.
1. `--set bad-pages=fast` 根据page-directory信息尽可能的解析坏块中的数据, 数据可能会多,也可能会少
2. `--set bad-pages=try` 1字节1字节的解析坏块中的数据, 会多出很多数据(表结构越简单,多的数据越多), 但不会差数据(有的都解析了)
3. `--set bad-pages=skip` 跳过坏块中的数据.
例子:
```shell
python3 main.py /tmp/sbtest2.ibd --sql --force --set bad-pages=fast
```
> 由于存在坏块,叶子节点间的指向就不准确了, 故要使用--force来强制遍历整个数据文件. 其它选项请自行组合. 对于bad-pages目前只在单进程中做了判断.


# 恢复被drop的表
主要使用`--scan DEVNAME`扫描磁盘来恢复被drop的数据. 可以先获取元数据信息,再扫盘; 也可以直接获取元数据信息并扫盘.
> 5.7的元数据信息是在ibdata1里面的, 8.0是在mysql.ibd里面的.

例子: 查看/data2/mysql.ibd中被drop的表,并扫描磁盘/dev/vdc,并输出为SQL语句
```shell
python3 main.py /data2/mysql.ibd --scan /dev/vdc --sql
```

如果有多个表被删除, 可以加上`--set table=TBLNAME` 来获取指定的表的信息
```shell
python3 main.py /data2/mysql.ibd --scan /dev/vdc --sql --set table=TBLNAME
```

当然有时候,可能需要先输出为page形式,然后再次解析
```shell
# 扫描目录获取page
python3 main.py /data/mysql_5744/mysqldata/ibdata1 --scan /dev/vdb
# 直接指定扫描上面获取到的目录
python3 main.py /data/mysql_5744/mysqldata/ibdata1 --scan ibd2sql_auto_dir_20260108_142543 --sql
```

还有的时候,我们可能需要全部index page都扫描出来
```shell
python3 main.py --scan /dev/vdb --set indexid=all
```

并发也是支持的
```shell
python3 main.py --scan /dev/vdb --set indexid=all --parallel 4
```

更多组合自己去试吧 -_-

# 恢复被truncate的表
mysql 5.7中truncate表Indexid是不会变的, 我们只需要获取到indexid,然后扫描磁盘的时候指定indexid即可.
```shell
# 扫描ibdata1获取t2表的tableid (第2列)
python3 main.py /data/mysql_5744/mysqldata/ibdata1 --set table=sys_tables --sql | grep t2

# 扫描ibdata1获取t2表主键的indexid (第2列)
python3 main.py /data/mysql_5744/mysqldata/ibdata1 --set table=sys_indexes --sql | grep 55 #这个55是上面看到表的第2列,tableid

# 根据indexid扫描磁盘获取相关的page
python3 main.py --scan /dev/vdb --set indexid=56 # 这个56就是上面获取到的indexid

# 然后指定sdi等元数据信息解析相关的表即可
python3 main.py /tmp/ibd2sql_auto_dir_20260108_145604/index/0_0000000034_0000000000000056.page --sdi /data/mysql_5744/mysqldata/db1/t20260108_02.frm --set leafno=0 --set rootno=0 --force --sql
```

对于mysql 8.0就麻烦点, 因为是使用的update更新的系统表,indexid之类的信息被更新了, 找不到之前的信息了.(redo应该有,后面可以尝试下). 但是我们可以把所有的索引页都扫描出来, 然后一个个试(建议先把系统表记录的表的indexid都排除掉,这样少很多, 基本上就只剩下几个了)
