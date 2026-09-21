本文为使用ibd2sql v2.x恢复被drop的表.



# 恢复理论

ibd2sql解析数据需要的是元数据信息和数据页.

元数据信息: 当表被drop之后,系统表只是对其元数据信息进行delete而已; 而delete的数据我们是可以恢复的.

数据页: 当表被drop之后,文件系统层面无法直接看到相关文件了, 但一般不会马上对其使用空间进行回收.所以我们只需要把整个磁盘当作数据文件来进行扫描就能获取到我们需要的数据页了.

我们需要做的就是扫描系统表获取被drop表的元数据信息,再扫描磁盘(`--scan-device`)对其进行解析即可.

> 由于delete的元数据信息或者磁盘上的数据页都是可能被回收的, 所以恢复drop的表不一定百分百成功.



MySQL 5.x和8.x使用方法是一样的, 只不过mysql 5.x版本的元数据信息是存储在ibdata1中的, mysql 8.x版本的元数据信息是放在mysql.ibd中的. 除此之外使用上并没有区别.

Windows和Linux使用一样,只不过将磁盘文件换成了对应的盘符而已,比如: `\\.\E:`表示E盘. 

本文主要以8.x版本为主, 如果使用者使用的是5.x版本,只需要将mysql.ibd换成ibdata1即可.



# 恢复drop表的操作

被drop的表, 本质上是**delete系统表**对应的记录,然后**unlink文件**.

我们的恢复逻辑是:

1. 找到被删除表的indexid.
2. 根据indexid扫描磁盘获取数据页
3. 根据表结构解析数据页



## 获取被删除表的indexid

indexid是在系统表里面的, 所以我们可以解析系统表来获取

```shell
# 扫描系统表获取被删除表的indexid和表结构
python3 main.py mysql.ibd --scan
python3 main.py mysql.ibd --scan --set table=yourtablename # 如果很多的话, 可以过滤下你的[表]名字
python3 main.py mysql.ibd --scan --ddl # 也可以输出表结构信息, 5.7的decimal之类的看不到... 建议找开发提供表结构
```

但是运气不好的话, 可能就回收了, 咋办呢? 不要慌, 我们还可以解析redo获取indexid,可参考truncate恢复数据



## 根据indexid扫描磁盘获取数据页

```shell
# 扫描磁盘
python3 main.py --scan /dev/vdb --set indexid=156 # linux
python3 main.py --scan \\.\E: --set indexid=156   # windows

python3 main.py --scan /dev/vdb --set indexid=156 --output /tmp/xxx # 指定输出目录, 默认是当前目录.
python3 main.py --scan /dev/vdb --set indexid=156 --parallel 8 # 指定并发, 默认1个并发. 
```



## 根据表结构解析数据页

表结构可以从系统表获取,也可以找开发要. 反正你得要有, 我是没办法提供的...

```shell
python3 main.py xxxx.page --sdi yourtable.ibd --set leafno=0 --set rootno=0 --force
```

因为我们只提取了主键叶子节点的页, 所以我们得告诉ibd2sql, 叶子节点是第0个(`--set leafno=0`),要遍历解析(`--force`)





# 恢复drop表的使用例子

为了方便使用, 我们可以把上面3步合并一起(不方便控制)

## 一步到位

一条命令就恢复需要的数据,操作非常简单.

```shell
# 准备数据
create table db1.t20260920_02(id int, name varchar(20));
insert into db1.t20260920_02 values(1,'ddcw'),(2,'ddcw 2');

# 删除表
drop table db1.t20260920_02;

# 开始恢复
python3 main.py /data/mysql_8037/mysqldata/mysql.ibd --scan-device /dev/mapper/centos-root --set table=t20260920_02 --ddl --sql --output /tmp --parallel 8
# 我们这里是8.x版本,所以是mysql.ibd文件
# 我这里的数据是放在lv里面的,所以是--scan-device /dev/mapper/centos-root
# 指定需要恢复的表 --set table=t20260920_02
# 输出表结构与数据 --ddl --sql 
# 建议指定输出目录,不要和数据目录放一起,不然可能也会被扫描到,那样数据就重复了. --output /tmp
# 建议加上并发 --parallel 8 

19:33:23 [root@ddcw21 ibd2sql-ibd2sql-v2.x]#python3 main.py /data/mysql_8037/mysqldata/mysql.ibd --scan-device /dev/mapper/centos-root --set table=t20260920_02 --ddl --sql --output /tmp --parallel 8

-- db1.t20260920_02 table_id:691 index_id:528
CREATE TABLE IF NOT EXISTS `db1`.`t20260920_02` (
  `id` int NULL,
  `name` varchar(20) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

-- OUTPUT DIR: /tmp
[0] START
[1] START
[2] START
[3] START
[4] START
[5] START
[6] START
[7] START
[2] 1.58 %
[3] 1.62 %
[6] 1.64 %
[5] 1.65 %
[0] 1.66 %
[4] 1.67 %
[7] 1.68 %
[1] 1.69 %
[2] 3.45 %
[3] 3.47 %
[7] 3.48 %
[5] 3.46 %
[1] 3.49 %
[6] 3.5 %
[0] 3.51 %
[4] 3.52 %
[0] 5.29 %
[6] 5.3 %
[4] 5.31 %
[2] 5.33 %
[3] 5.34 %
...........
[6] 30.33 %
[7] 30.34 %
[1] WRITE BUFFER DATA 1
[1] NEW FILE /tmp/sql/1_db1.t20260920_02.sql
[7] 32.06 %
[5] 32.07 %
[6] 32.08 %
..........
[2] 37.6 %
[6] WRITE BUFFER DATA 1
[6] NEW FILE /tmp/sql/6_db1.t20260920_02.sql
[7] 39.38 %
[2] 39.39 %
[0] 39.4 %
.......
[3] 54.09 %
[7] WRITE BUFFER DATA 1
[7] NEW FILE /tmp/sql/7_db1.t20260920_02.sql
[6] 55.84 %
[7] 55.85 %
....
[6] 61.36 %
[2] WRITE BUFFER DATA 1
[2] NEW FILE /tmp/sql/2_db1.t20260920_02.sql
[0] 63.17 %
[4] 63.18 %
[7] 63.16 %
......
[6] 99.24 %
[3] 99.26 %
[4] 99.27 %
[7] 99.25 %
[1] 99.28 %
[1] FINISH
[4] FINISH
[7] FINISH
[2] FINISH
[5] FINISH
[6] FINISH
[3] FINISH
[0] FINISH
SCAN FINISHED. /tmp


19:45:33 [root@ddcw21 ibd2sql-ibd2sql-v2.x]#cat /tmp/sql/2_db1.t20260920_02.sql
INSERT INTO `db1`.`t20260920_02` VALUES (1,'ddcw');
INSERT INTO `db1`.`t20260920_02` VALUES (2,'ddcw 2');
```

速度还算很不错的:

虚拟机环境,150GB的lv,8线程耗时大概11分钟.



## 步步为营

一步步的操作才能更好的理解恢复原理: 这里我们以Windows环境为例

```shell
# 获取表结构和indexid
E:\ibd2sql-ibd2sql-v2.x\ibd2sql-ibd2sql-v2.x>python3 main.py E:\mysql-8.0.44-winx64\mysql-8.0.44-winx64\data\mysql.ibd --scan --set table=t20260313_fordrop --ddl

-- db1.t20260313_fordrop table_id:367 index_id:157
CREATE TABLE IF NOT EXISTS `db1`.`t20260313_fordrop` (
  `id` int NULL,
  `name` varchar(200) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


# 扫描磁盘获取数据页
E:\ibd2sql-ibd2sql-v2.x\ibd2sql-ibd2sql-v2.x>python3 main.py E:\mysql-8.0.44-winx64\mysql-8.0.44-winx64\data\mysql.ibd --scan \\.\E: --set indexid=157 --output C:\ibd2sql_recovery --parallel 8

-- db1.t20260313_fordrop table_id:367 index_id:157

-- OUTPUT DIR: C:\ibd2sql_recovery
[1] START
[0] START
[3] START
[2] START
[6] START
[5] START
[4] START
[7] START
[5] WRITE BUFFER DATA 1
[5] NEW FILE C:\ibd2sql_recovery\index\5_0000000005_0000000000000157.page
[6] 10.87 %
[1] 11.02 %
......
[0] 97.74 %
[1] 97.89 %
[7] 99.22 %
[4] 99.3 %
[2] FINISH
[1] FINISH
[6] FINISH
[3] FINISH
[0] FINISH
[7] FINISH
[4] FINISH
[5] FINISH
SCAN FINISHED. C:\ibd2sql_recovery

# 根据元数据信息(可以根据第一步获取的表结构创建空表从而拿到对应的ibd文件)和数据页进行恢复
E:\ibd2sql-ibd2sql-v2.x\ibd2sql-ibd2sql-v2.x>python3 main.py C:\ibd2sql_recovery\index\5_0000000005_0000000000000157.page --sdi E:\mysql-8.0.44-winx64\mysql-8.0.44-winx64\data\db1\t20260313_02.ibd --set leafno=0 --set rootno=0 --force --sql
INSERT INTO `db1`.`t20260313_02` VALUES (1,'ddcw');
INSERT INTO `db1`.`t20260313_02` VALUES (2,'https://github.com/ddcw/ibd2sql');
```



## 保险起见

有时候不能马上确定indexid, 那就全部都保存, 后面再来慢慢分析. 免得被覆盖了. 输出内容会非常多. 每张表都一个文件

```shell
E:\ibd2sql-ibd2sql-v2.x\ibd2sql-ibd2sql-v2.x>python3 main.py E:\mysql-8.0.44-winx64\mysql-8.0.44-winx64\data\mysql.ibd --scan \\.\E: --set indexid=all --output C:\ibd2sql_recovery --parallel 8

-- db1.t20260313_fordrop table_id:367 index_id:157

-- OUTPUT DIR: C:\ibd2sql_recovery
[0] START
[1] START
[2] START
[3] START
[4] START
[5] START
[6] START
[1] WRITE BUFFER DATA 1
[1] NEW FILE C:\ibd2sql_recovery\index\1_0000000004_0000000000000156.page
[7] START
[6] WRITE BUFFER DATA 1
[6] NEW FILE C:\ibd2sql_recovery\index\6_0000000002_0000000000000154.page
[5] WRITE BUFFER DATA 1
[5] NEW FILE C:\ibd2sql_recovery\index\5_0000000002_0000000000000154.page
[7] WRITE BUFFER DATA 1
[7] NEW FILE C:\ibd2sql_recovery\index\7_0000000003_0000000000000155.page
[3] WRITE BUFFER DATA 8
[3] NEW FILE C:\ibd2sql_recovery\index\3_0000000002_0000000000000154.page
[6] WRITE BUFFER DATA 3
[6] NEW FILE C:\ibd2sql_recovery\index\6_0000000004_0000000000000156.page
[0] WRITE BUFFER DATA 1
[0] NEW FILE C:\ibd2sql_recovery\index\0_0000000000_18446744069414584320.page
[6] WRITE BUFFER DATA 3
[6] NEW FILE C:\ibd2sql_recovery\index\6_0000000005_0000000000000157.page
[6] WRITE BUFFER DATA 1
[6] WRITE BUFFER DATA 3
[1] WRITE BUFFER DATA 63
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000045.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000046.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000047.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000048.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000049.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000050.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000051.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000052.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000053.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000054.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000055.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000056.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000057.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000058.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000059.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000060.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000061.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000062.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000063.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000064.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000065.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000066.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000067.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000068.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000069.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000070.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000071.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000072.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000073.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000074.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000075.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000076.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000077.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000078.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000079.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000080.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000081.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000082.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000083.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000084.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000085.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000086.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000087.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000088.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000089.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000090.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000091.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000092.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000093.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000094.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000095.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000096.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000097.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000098.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000099.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000100.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000101.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000102.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000022.page
[5] WRITE BUFFER DATA 44
[5] NEW FILE C:\ibd2sql_recovery\index\5_4294967294_0000000000000056.page
[5] NEW FILE C:\ibd2sql_recovery\index\5_4294967294_0000000000000146.page
[5] NEW FILE C:\ibd2sql_recovery\index\5_4294967294_0000000000000147.page
[1] WRITE BUFFER DATA 39
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000040.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000015.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000025.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000024.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000023.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000026.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000021.page
[5] WRITE BUFFER DATA 18
[5] NEW FILE C:\ibd2sql_recovery\index\5_4294967294_0000000000000078.page
[1] WRITE BUFFER DATA 12
[4] WRITE BUFFER DATA 44
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000001.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000002.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000003.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000004.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000005.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000006.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000007.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000008.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000009.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000010.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000011.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000012.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000013.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000014.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000015.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000016.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000017.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000018.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000019.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000020.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000021.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000022.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000023.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000024.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000025.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000026.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000027.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000028.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000029.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000030.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000031.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000032.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000033.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000034.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000035.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000036.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000037.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000038.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000039.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000040.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000041.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000042.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000043.page
[4] NEW FILE C:\ibd2sql_recovery\index\4_4294967294_0000000000000044.page
[5] WRITE BUFFER DATA 1
[5] NEW FILE C:\ibd2sql_recovery\index\5_0000000001_0000000000000153.page
[1] WRITE BUFFER DATA 48
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000041.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000042.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000103.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000104.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000105.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000106.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000107.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000108.page
[1] WRITE BUFFER DATA 37
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000109.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000110.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000111.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000112.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000113.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000114.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000115.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000116.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000117.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000118.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000119.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000120.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000121.page
[1] WRITE BUFFER DATA 46
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000122.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000123.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000124.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000125.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000126.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000127.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000128.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000129.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000130.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000131.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000132.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000133.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000134.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000135.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000136.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000137.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000138.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000139.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000140.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000141.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000142.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000143.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000144.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000145.page
[1] WRITE BUFFER DATA 64
[1] WRITE BUFFER DATA 64
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000146.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000147.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000148.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000149.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000150.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000151.page
[1] NEW FILE C:\ibd2sql_recovery\index\1_4294967294_0000000000000152.page
[1] WRITE BUFFER DATA 62
[1] WRITE BUFFER DATA 64
[1] WRITE BUFFER DATA 64
[1] WRITE BUFFER DATA 56
[1] WRITE BUFFER DATA 46
[1] 10.87 %
[0] 10.95 %
[2] 11.1 %
[3] 11.34 %
[6] 12.12 %
[4] 12.43 %
[7] 12.35 %
[5] 12.59 %
[2] 23.14 %
[3] 23.22 %
[0] 23.38 %
[1] 23.69 %
[7] 24.55 %
[4] 24.63 %
[5] 24.79 %
[6] 24.94 %
[2] 35.81 %
[0] 35.89 %
[3] 35.97 %
[1] 36.05 %
[5] 36.83 %
[4] 36.91 %
[6] 36.98 %
[7] 37.37 %
[2] 47.93 %
[3] 48.01 %
[1] 48.24 %
[0] 48.4 %
[7] 49.34 %
[6] 49.49 %
[4] 49.57 %
[5] 49.65 %
[0] 60.36 %
[3] 60.52 %
[1] 60.75 %
[2] 60.68 %
[4] 61.61 %
[5] 61.93 %
[7] 62.08 %
[6] 62.16 %
[2] 72.72 %
[0] 72.95 %
[1] 73.11 %
[3] 73.19 %
[7] 74.05 %
[5] 74.12 %
[6] 74.36 %
[4] 74.44 %
[1] 85.31 %
[3] 85.38 %
[2] 85.46 %
[0] 85.54 %
[4] 86.4 %
[5] 86.48 %
[6] 86.56 %
[7] 86.87 %
[0] 97.97 %
[1] 98.21 %
[2] 98.05 %
[3] 98.13 %
[6] 98.91 %
[7] 98.99 %
[4] 99.07 %
[5] 99.14 %
[3] FINISH
[6] FINISH
[4] FINISH
[7] FINISH
[1] FINISH
[5] FINISH
[2] FINISH
[0] FINISH
SCAN FINISHED. C:\ibd2sql_recovery
```

