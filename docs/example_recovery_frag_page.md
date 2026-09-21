本文为ibd2sql v2.x版本从碎片页中恢复数据



# 关于碎片页

本文的碎片页是指: 数据页不在完整的btr+中. 

1. 数据文件被部分截断(truncate)了, 比如使用某些工具从磁盘恢复文件的时候只剩文件的部分了.
2. 使用ibd2sql,undrop-for-innodb之类扫描磁盘仅获取数据页.
3. 其它只剩下部分数据页的情况.



# 恢复方法

恢复数据只需要元数据信息和数据页即可,我们默认是根据btr+的叶子节点遍历的,只需要加上`--force`使其变成顺序的一页页扫描即可.

既然目标文件已经存在缺失了, 那么就可能没有元数据信息, 所以可能需要搭配`--sdi-table`来指定使用的元数据信息. 当然起始叶子节点可能也已经丢失了, 所以可能还需要加上`--set leafno`来指定起始叶子节点

> 从起始叶子节点开始遍历btr+,或者从起始叶子节点,一页页往后解析.

```shell
# 从碎片页恢复数据(元数据信息可能不在目标文件中)
python3 main.py /tmp/sbtest2.ibd --sdi /data/mysql_3314/mysqldata/db1/sbtest2.ibd  --sql --force

# 从undrop-for-innodb扫描出来的page中恢复. 
# 为了方便使用,我们对其进行了使用优化,只需要跟上目录即可,然后使用 --set indexid来指定需要解析的page文件.
python3 main.py /PATH/pages-vda1/ --sdi /PATH/t20250912_2.frm --set indexid=22 --sql
```



# 使用例子

```shell
# 准备测试文件
cp -ra /data/mysql_3314/mysqldata/db1/sbtest2.ibd /tmp/sbtest2.ibd

# 对其进行截断来模拟文件不完整(碎片)
truncate -s -70MB /tmp/sbtest2.ibd # 截断了大部分数据,使其btr+严重破坏

# 正常解析ibd文件会遇到报错: 该报错为:未获取到rec_header需要的5字节,即未读取到需要的数据页
python3 main.py /tmp/sbtest2.ibd --sql >/dev/null
Traceback (most recent call last):
  File "/tmp/t20260911/ibd2sql-ibd2sql-v2.x/main.py", line 525, in <module>
    IBD2SQL_SINGLE(table,x,opt,filename_pre,log,parser,FRAGMENT_FILENAME_PRE)
  File "/tmp/t20260911/ibd2sql-ibd2sql-v2.x/ibd2sql/ibd2sql.py", line 452, in IBD2SQL_SINGLE
    row += idx.get_sql(False)
  File "/tmp/t20260911/ibd2sql-ibd2sql-v2.x/ibd2sql/innodb_page/index.py", line 143, in _get_sql_single
    for data in self.get_all_rows(deleted):
  File "/tmp/t20260911/ibd2sql-ibd2sql-v2.x/ibd2sql/innodb_page/index.py", line 173, in get_all_rows
    self._read_rec_header_new()
  File "/tmp/t20260911/ibd2sql-ibd2sql-v2.x/ibd2sql/innodb_page/index.py", line 492, in _read_rec_header_new
    rec1,rec2,rec_next = struct.unpack('>HBh',data)
struct.error: unpack requires a buffer of 5 bytes

# 使用--force强制解析
python3 main.py /tmp/sbtest2.ibd --sql --force

# 使用--force强制解析, 使用指定的ibd作为元数据信息来源(通常是5.7升级到8.0之后,sdi位于文件的后部分,此时才可能需要)
python3 main.py /tmp/sbtest2.ibd --sql --force --sdi /data/mysql_3314/mysqldata/db1/sbtest2.ibd

# 使用--force强制解析,指定起始位置(btr+第一个叶子节点丢失或无法正确识别到)
python3 main.py /tmp/sbtest2.ibd --sql --force --set leafno=4
```

注: 本文的强制解析即为按照一页页的顺序对目标进行解析.