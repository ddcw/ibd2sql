本文为ibd2sql v2.x恢复磁盘rm的文件.

windows环境通常有回收站,所以本文主要以Linux为主.



# 恢复rm数据的原理

如果数据库未停的话, rm只是引用减1,并不会删除文件,只需要根据fd重定向即可. 该操作较为简单, 不在本次讨论范围内.

```shell
ll /proc/`pidof mysqld`/fd | grep deleted
```



所以本次讨论的环境主要以离线环境误删mysql文件的恢复.

1. 误删系统表:  可能只是删除了系统表,也可能是都删除了,只剩下一个数据目录/文件
2. 误删业务表: 业务表被rm了
3. 系统表业务表都误删了: 全部都被rm了.



如果已经学会了前面的drop/truncate表的恢复,那么本章就会非常简单了. 

ibd2sql解析数据需要的是元数据信息和数据页. 所以我们还是想办法获取到这两样就行.



# 误删系统表

如果frm和ibd文件都存在的话(8.x只需要ibd),我们并不关心系统表,直接初始化实例并导入数据即可.



# 误删业务表

我们连drop/truncate的都能恢复了, 恢复rm的业务表就更简单了.(5.7只需要将mysql.ibd换成ibdata1即可)

```shell
# 一步到位 (和drop表的恢复的区别只是多了个--set delete=with 表示未被drop的表也要考虑)
python3 main.py /data/mysql_8037/mysqldata/mysql.ibd --scan-device /dev/mapper/centos-root --set table=t20260920_04 --ddl --sql --output /tmp/t20260920_04 --parallel 8 --set delete=with

# 也可以分步骤来. 我这里就省略了
```



# 系统表业务表都误删了

如果业务表和系统表都没了的话, 我们还是有机会恢复的. 毕竟我们扫描磁盘的时候还会考虑frm/sdi之类的元数据信息.

```shell
# 恢复所有的数据页
python3 main.py --scan-device /dev/mapper/centos-root --set indexid=all --set with-sdi --set with-frm --output /tmp/t20260920_all --parallel 8 

# 然后找到需要的frm/sdi相关的信息去解析对应的文件.
```

