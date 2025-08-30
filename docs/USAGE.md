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

