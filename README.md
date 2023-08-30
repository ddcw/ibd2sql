# 介绍

解析mysql8.0的数据文件, 并生成相关SQL.



# 功能

| 选项                | 说明                    | 备注                    |
| ----------------- | --------------------- | --------------------- |
| --sql             | 打印解析出来的数据的insert语句    |                       |
| --ddl             | 打印相关DDL               |                       |
| --data            | 打印解析出来的数据的LIST格式      |                       |
| --delete          | 打印被标记为deleted的数据      | 全看运气                  |
| --complete-insert | insert语句包含列名字         |                       |
| --table-name      | 替换insert语句的表名         | 不含DDL的,这是特性,不是BUG -_- |
| -h                | 打印帮助信息                |                       |
| -f                | 对于包含有限支持和不支持的数据类型强制解析 | 我也不知道会发生啥...          |



# 使用方法

推荐使用源码, 毕竟没得依赖

## 查看DDL

```shell
python main.py --ddl /data/mysql_3314/mysqldata/db1/t20230830.ibd
```



## 查看数据(INSERT)

```shell
python main.py --sql /data/mysql_3314/mysqldata/db1/t20230830.ibd
```



## 查看数据(含列名)

对于某些数据库,可能需要列名字(比如某些分布式数据库)

```shell
python main.py --sql --complete-insert /data/mysql_3314/mysqldata/db1/t20230830.ibd
```



## 查看数据(LIST)

```shell
python main.py --data /data/mysql_3314/mysqldata/db1/t20230830.ibd
```



## 查看被标记为deleted的数据

```shell
python main.py --delete /data/mysql_3314/mysqldata/db1/t20230830.ibd
```





# 支持

支持几乎所有mysql 8.0的数据类型(除了json). 对lob对象也是有限支持.

支持 大部分表/字段属性

## DDL支持

| 对象            | 是否支持 | 备注         |
| ------------- | ---- | ---------- |
| IF NOT EXISTS | 支持   | 默认都是这个     |
| 自增            | 支持   |            |
| 默认值           | 支持   |            |
| 字段和表的注释       | 支持   |            |
| 索引            | 支持   | 主键索引, 普通索引 |
| 外键            | 支持   |            |
| 约束            | 支持   |            |
| 存储引擎          | 支持   | 只支持innodb  |
| 分区            | 不支持  | 不支持        |




## 支持的数据类型

参考:https://dev.mysql.com/doc/refman/8.0/en/storage-requirements.html

### 数字类型

| 类型              | 大小(字节)                                   | 有无符号 | 备注   |
| --------------- | ---------------------------------------- | ---- | ---- |
| tinyint         | 1 bytes                                  | 可选   |      |
| smallint        | 2 bytes                                  | 可选   |      |
| mediumint       | 3 bytes                                  | 可选   |      |
| int             | 4 bytes                                  | 可选   |      |
| bigint          | 8 bytes                                  | 可选   |      |
| float(p)        | 4 bytes if *p* is None,<br />4 bytes if 0 <= *p* <= 24, <br />8 bytes if 25 <= *p* <= 53 (就是double) | 有    |      |
| double          | 8 bytes                                  | 有    |      |
| DECIMAL/NUMERIC | 变长                                       | 有    |      |
| bit(M)          | (*M*+7)/8                                | 有    |      |



int/tinyint/smallint/mediumint/bigint计算方式:

```python
_t = int.from_bytes(bdata,'big')

# 第一位(bit)为符号位, 1:正数,  0:负数
# is_unsigned  无符号: True  有符号:False
# n 大小,单位:字节
# bdata 为原始数据
# _t 为临时数据
return (_t&((1<<(2**n-1)))-1))-2**(2**n-1) if _t < 2**(2**n-1) and not is_unsigned else (_t&((1<<(2**n-1))-1))
```



float/double/real

```python
return struct.unpack('f',bdata)[0]
return struct.unpack('d',bdata)[0]
```



decimal

整数部分和小数部分是分开的

每部分 的每9位10进制数占4字节,  剩余的就按 1-2 为1字节, 这样算

比如 

(5,2)   整数就是2字节, 小数也是1字节

(10,3) 整数就是4+1字节, 小数就是2字节



### 时间类型

| 类型           | 大小(字节) | 备注    | 范围                                       |
| ------------ | ------ | ----- | ---------------------------------------- |
| year         | 1      | +1901 | '1901' to '2115'                         |
| date         | 3      |       | '1000-01-01' to '9999-12-31'             |
| time(n)      | 3+N    |       | '-838:59:59.000000' to '838:59:59.000000' |
| datetime(n)  | 5+N    |       | '1000-01-01 00:00:00.000000' to '9999-12-31 23:59:59.999999' |
| timestamp(n) | 4+N    |       | '1000-01-01' to '9999-12-31'             |

N计算方式

```python
N = int((n+1)/2)
```





### 字符串类型

M表示字符大小

W表示每个字符所用字节数(解析的时候并不关心字符集)

L 表示 M*W 也就是数据长度

| 类型                       | 大小(字节)                                   | 范围        | 备注     |
| ------------------------ | ---------------------------------------- | --------- | ------ |
| char(M)                  | L                                        | <=255 字符  |        |
| BINARY(M)                | M                                        | <=255 字节  |        |
| VARCHAR(M), VARBINARY(M) | 1 字节长度 + L: 当 L < 128<br />2 字节长度 + L: 当L >=128 | <=65535字节 |        |
| TINYBLOB, TINYTEXT       | L + 1 bytes, where L < 256               | < 256 B   |        |
| BLOB, TEXT               | L + 2 bytes, where L < 2**16             | <=65535字节 |        |
| MEDIUMBLOB, MEDIUMTEXT   | L + 3 bytes, where L < 2**24             | 16M       | 有限支持   |
| LONGBLOB, LONGTEXT       | L + 4 bytes, where L < 2**32             | 4G        | 有限支持   |
| ENUM                     | 1 or 2 bytes, depending on the number of enumeration values (65,535 values maximum) |           | 使用数字表示 |
| SET                      | 1, 2, 3, 4, or 8 bytes, depending on the number of set members (64 members maximum) |           | 使用数字表示 |
| JSON                     |                                          |           | 不支持    |

char 虽然大小是固定的, 但还是要每行数据都记录char大小.... (解析的时候注意是个小坑....)

enum 只能取一个值 所以1字节可以表示255种, 2字节表示65535

set 可以取多个值, 所以还得表示位置, 即1字节最多表示8个值, 类似null bit mask

enum和set就使用数字来表示, 主要是节省空间.... 感兴趣的可以字节替换. 相关变量

```python
columns[x]['list'] 记录每个列的enum/set 的具体选项
```





# 版本变化

| 版本   | 变更时间       | 说明        | 备注                                       |
| ---- | ---------- | --------- | ---------------------------------------- |
| v0.1 | 2023.4.27  | 第一个版本.... |                                          |
| v0.2 | 2023.08.30 | 支持更多数据类型  | 1. 修复year/tinyint的支持<br />2. 符号支持(对于数字类型)<br />3. 更多的数据类型支持<br />4. 更多的表属性支持<br />5. 美化输出<br />6. 支持表名替换<br />7. 支持--complete-insert |
|      |            |           |                                          |



# 使用例子

本次测试的版本为

MySQL 8.0.28

innodb_default_row_format = dynamic

准备数据

```mysql
CREATE TABLE AllTypesExample (
    id INT AUTO_INCREMENT PRIMARY KEY,
    int_col INT,
    tinyint_col TINYINT,
    smallint_col SMALLINT,
    mediumint_col MEDIUMINT,
    bigint_col BIGINT,
    float_col FLOAT,
    double_col DOUBLE,
    decimal_col DECIMAL(10, 2),
    date_col DATE,
    datetime_col DATETIME,
    timestamp_col TIMESTAMP,
    time_col TIME,
    year_col YEAR,
    char_col CHAR(5),
    varchar_col VARCHAR(20),
    binary_col BINARY(5),
    varbinary_col VARBINARY(20),
    bit_col BIT(4),
    enum_col ENUM('A', 'B', 'C'),
    set_col SET('X', 'Y', 'Z')
);

-- 插入数据
INSERT INTO AllTypesExample (
    int_col, tinyint_col, smallint_col, mediumint_col, bigint_col,
    float_col, double_col, decimal_col, date_col, datetime_col,
    timestamp_col, time_col, year_col, char_col, varchar_col,
    binary_col, varbinary_col, bit_col, enum_col, set_col
)
VALUES (
    2147483647, 127, 32767, 8388607, 9223372036854775807,
    3.14159, 2.71828, 12345.67, '2023-01-01', '2023-01-01 12:34:56',
    NOW(), '12:34:56', 2023, 'ABCDE', 'HelloWorld',
    BINARY '12345', BINARY 'abcdef', 15, 'A', 'X,Y'
);

-- 插入第二条数据
INSERT INTO AllTypesExample (
    int_col, tinyint_col, smallint_col, mediumint_col, bigint_col,
    float_col, double_col, decimal_col, date_col, datetime_col,
    timestamp_col, time_col, year_col, char_col, varchar_col,
    binary_col, varbinary_col, bit_col, enum_col, set_col
)
VALUES (
    -2147483648, -128, -32768, -8388608, -9223372036854775808,
    -3.14, -2.71, -12345.67, '1990-12-31', '1990-12-31 23:59:59',
    NOW(), '23:59:59', 1990, '12345', 'Negative',
    BINARY '54321', BINARY 'ghijkl', 0, 'B', 'Y,Z'
);

-- 插入第三条数据
INSERT INTO AllTypesExample (
    int_col, tinyint_col, smallint_col, mediumint_col, bigint_col,
    float_col, double_col, decimal_col, date_col, datetime_col,
    timestamp_col, time_col, year_col, char_col, varchar_col,
    binary_col, varbinary_col, bit_col, enum_col, set_col
)
VALUES (
    0, 0, 0, 0, 0,
    0, 0, 0, '2000-02-29', '2000-02-29 00:00:00',
    NOW(), '00:00:00', 2000, '00000', 'Zero',
    BINARY '00000', BINARY '00000', 0, 'C', 'X,Z'
);

-- 随机删除一条数据
DELETE FROM AllTypesExample LIMIT 1;
```



使用ibd2sql解析数据

```shell
(venv) 11:00:23 [root@ddcw21 ibd2sql_v0.2]#python main.py --ddl --sql /data/mysql_3314/mysqldata/db1/AllTypesExample.ibd 

 CREATE Table IF NOT EXISTS `db1`.`AllTypesExample`(
`id` int NOT NULL AUTO_INCREMENT ,
`int_col` int DEFAULT NULL ,
`tinyint_col` tinyint DEFAULT NULL ,
`smallint_col` smallint DEFAULT NULL ,
`mediumint_col` mediumint DEFAULT NULL ,
`bigint_col` bigint DEFAULT NULL ,
`float_col` float DEFAULT NULL ,
`double_col` double DEFAULT NULL ,
`decimal_col` decimal(10,2) DEFAULT NULL ,
`date_col` date DEFAULT NULL ,
`datetime_col` datetime DEFAULT NULL ,
`timestamp_col` timestamp DEFAULT NULL ,
`time_col` time DEFAULT NULL ,
`year_col` year DEFAULT NULL ,
`char_col` char(5) DEFAULT NULL ,
`varchar_col` varchar(20) DEFAULT NULL ,
`binary_col` binary(5) DEFAULT NULL ,
`varbinary_col` varbinary(20) DEFAULT NULL ,
`bit_col` bit(4) DEFAULT NULL ,
`enum_col` enum('A','B','C') DEFAULT NULL ,
`set_col` set('X','Y','Z') DEFAULT NULL ,
PRIMARY KEY (`id`)
)ENGINE=InnoDB ; 

INSERT INTO `db1`.`AllTypesExample` VALUES(2, -2147483648, -128, -32768, -8388608, -9223372036854775808, -3.140000104904175, -2.71, -12345.67, '1990-12-31', '1990-12-31 23:59:59', '2023-8-30 10:58:41', '23:59:59', '1990', '12345', 'Negative', '54321', 'ghijkl', 0, 2, 6);
INSERT INTO `db1`.`AllTypesExample` VALUES(3, 0, 0, 0, 0, 0, 0.0, 0.0, 0.0, '2000-2-29', '2000-2-29 0:0:0', '2023-8-30 10:58:41', '0:0:0', '2000', '00000', 'Zero', '00000', '00000', 0, 3, 5);

(venv) 11:00:29 [root@ddcw21 ibd2sql_v0.2]#python main.py --delete /data/mysql_3314/mysqldata/db1/AllTypesExample.ibd 
INSERT INTO `db1`.`AllTypesExample` VALUES(1, 2147483647, 127, 32767, 8388607, 9223372036854775807, 3.141590118408203, 2.71828, 12345.67, '2023-1-1', '2023-1-1 12:34:56', '2023-8-30 10:58:41', '12:34:56', '2023', 'ABCDE', 'HelloWorld', '12345', 'abcdef', 15, 1, 3);
(venv) 11:00:35 [root@ddcw21 ibd2sql_v0.2]#
```

