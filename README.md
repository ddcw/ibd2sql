# 介绍

解析mysql8.0的数据文件, 生成相关SQL.



## 功能

DDL: 生成建表语句(无法区分唯一索引)

DML: 仅insert语句

DATA: N条list数据

DELETED: 生成被标记为deleted的数据



# 支持范围和限制

仅支持mysql 8.0

Python3写的

支持如下数据类型

| 类型            | 大小(字节) | 是否支持 |
| ------------- | ------ | ---- |
| varchar(n)    |        | 是    |
| char(n)       | n      | 是    |
| int           | 4      | 是    |
| date          | 3      | 是    |
| date/time (n) | 3-6    | 是    |
| datetime      | 5-8    | 是    |
| timestamp     | 4      | 是    |



## 下载

源码:(可以直接使用源码,  **无依赖包**)

```shell
wget https://github.com/ddcw/ibd2sql/archive/refs/heads/main.zip
```



二进制

```shell
wget  https://github.com/ddcw/ibd2sql/releases/download/v0.1/ibd2sql_v0.1_x86.tar.gz
```





# 使用方法

## 查看汇总信息

```shell
python main.py /data/mysql_3314/mysqldata/db1/t20230427_test.ibd
```



## 查看DDL

建表语句

```shell
python main.py /data/mysql_3314/mysqldata/db1/t20230427_test.ibd --ddl
```





## 查看DML

就是数据转换为insert形式

注意是直接print出来的, 数据量多的话, 屏幕显示不下, 建议使用重定向

```shell
python main.py /data/mysql_3314/mysqldata/db1/t20230427_test.ibd --sql
```

python main.py /data/mysql_3314/mysqldata/db1/t20230427_test.ibd --sql > /tmp/t20230427_xx.sql



## 查看deleted

查看被标记为deleted的数据.  就是数据库里面执行了delete之后, 被标记为deleted了

```shell
python main.py /data/mysql_3314/mysqldata/db1/t20230427_test.ibd --delete
```



## 查看数据(列表)

不是拼接的sql了, 是list型数据

```shell
python main.py /data/mysql_3314/mysqldata/db1/t20230427_test.ibd --data
```





# 版本变更说明

| 版本   | 变更时间      | 说明        |
| ---- | --------- | --------- |
| v0.1 | 2023.4.27 | 第一个版本.... |
|      |           |           |



# 使用例子

```shell
SEHLL> #python main.py /data/mysql_3314/mysqldata/db1/t20230427_test.ibd --ddl --sql

 CREATE Table  db1.t20230427_test(
id int NOT NULL  ,
name varchar(20) NOT NULL  ,
cc char(44) NULL  ,
bitthday date NULL  ,
ts timestamp NULL  ,
ti time NULL  ,
PRIMARY KEY(id,name)) ENGINE=InnoDB ; 

insert into db1.t20230427_test values("2","ddcw","aaaa","2023-4-27","2023-4-27 15:47:47","15:47:47");
insert into db1.t20230427_test values("3","666","aaaa","2023-4-27","2023-4-27 15:48:6","15:48:6");
insert into db1.t20230427_test values("4","77777","aaaa","2023-4-27","2023-4-27 16:39:30","16:39:30");
insert into db1.t20230427_test values("5","77777","aaaa","2023-4-27","2023-4-27 16:39:36","16:39:36");
SEHLL> 
SEHLL> #python main.py /data/mysql_3314/mysqldata/db1/t20230427_test.ibd --delete
insert into db1.t20230427_test values("1","ddcw","aaaa","2023-4-27","2023-4-27 15:47:42","15:47:42");
SEHLL> 

```

