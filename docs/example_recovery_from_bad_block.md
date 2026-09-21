本文主要记录ibd2sql恢复坏块的数据.

# 坏块判断逻辑

我们使用FIL_HEADER中的FIL_PAGE_SPACE_OR_CHECKSUM和FIL_TRAILER中的CHECKSUM以及使用crc32c计算校验值,比较三者是否相等.若不等则存在坏块, 但哪部分坏了, 是无法区分的....



# 坏块恢复理论

我们知道数据页结构如下:

| 对象           | 大小 | 描述                                 |
| -------------- | ---- | ------------------------------------ |
| FIL_HEADER     | 38   | FIL_HEADER                           |
| PAGE_HEADER    | 56   | 一些页头信息, INDEX PAGE的时候再细看 |
| INFIMUM        | 13   | 最小的行(虚拟的)                     |
| SUPEREMUM      | 13   | 最大的行(虚拟的)                     |
| USER RECORD    | x    | 实际的用户数据                       |
| FREE           | y    | 未使用的部分                         |
| PAGE_DIRECTORY | z    | 方便页内快速查找数据的. (页内目录)   |
| FIL_TRAILER    | 8    | FIL_TRAILER                          |

每个结构都可能存在坏块, 不同的结构坏块之后产生的效果是不一样的. 

如果FIL_HEADER中FIL_PAGE_TYPE有问题,则无法自动判断是否为数据页,可能会被跳过; 如果FREE部分有问题,则无所谓.



但我们并不需要关心那么多, 我们直接强行解析:即根据元数据信息对其进行解析,如果解析失败,则跳过该部分,继续解析后续数据.

跳过策略有3种:

skip: 整个坏块全部跳过.优点是非常快,缺点是:该页的数据都丢了.

fast: 根据page directory记录的信息来跳过. 优点是快,缺点是可能会丢数据.

try: 每次解析成功或者失败后,向后位移1字节,继续解析. 所以优点是:能最大层度的恢复数据. 缺点是:可能存在多余的数据



# 坏块恢复实际操作

实际操作,就只是多了`--set bad-pages`选项而已.其它用法不变:

```shell
# skip模式: 跳过坏块
python3 main.py /tmp/sbtest2.ibd --ddl --sql --force --set bad-pages=skip

# fast模式: 快速解析坏块
python3 main.py /tmp/sbtest2.ibd --ddl --sql --force --set bad-pages=fast

# try模式: 尽可能的从坏块中恢复数据
python3 main.py /tmp/sbtest2.ibd --ddl --sql --force --set bad-pages=try


# 对于较老的mysql版本(比如50173),需要额外加上 --set check-table-old 表示使用老版本的校验算法.
python3 main.py /tmp/sbtest2.ibd --ddl --sql --force --set bad-pages=try --set check-table-old
```



我们来看一个实际例子吧:

```shell
# 准备需要测试的数据文件
cp -ra /data/mysql_3314/mysqldata/db1/sbtest2.ibd /tmp/sbtest2.ibd

# 记录下正常的数据(方便后续对比)
python3 main.py /tmp/sbtest2.ibd --ddl --sql > /tmp/sbtest2.sql

# 随机破坏下(可以多整几次, 怕万一没坏到关键处.)
python3 mysql_ibd_corruption_danger.py /tmp/sbtest2.ibd --set random
python3 mysql_ibd_corruption_danger.py /tmp/sbtest2.ibd --set random
python3 mysql_ibd_corruption_danger.py /tmp/sbtest2.ibd --set random
17:23:25 [root@ddcw21 ibd2sql-ibd2sql-v2.x]#python3 mysql_ibd_corruption_danger.py /tmp/sbtest2.ibd --set random
输入如下数字表示开始破坏文件xxx 5099 
我的输入: 5099
既然你已求死, 那便整起!
BAD PAGE: 1067
17:23:29 [root@ddcw21 ibd2sql-ibd2sql-v2.x]#python3 mysql_ibd_corruption_danger.py /tmp/sbtest2.ibd --set random
输入如下数字表示开始破坏文件xxx 3676 
我的输入: 3676
既然你已求死, 那便整起!
BAD PAGE: 1532
17:23:33 [root@ddcw21 ibd2sql-ibd2sql-v2.x]#innochecksum /tmp/sbtest2.ibd # innochecksum遇到第一个坏块就退出所以看不到其它几个坏块....
Fail: page 1067 invalid
Exceeded the maximum allowed checksum mismatch count::0

# 我们先使用skip模式,看下实际上坏块部分丢了多少数据
python3 main.py /tmp/sbtest2.ibd --ddl --sql --force --set bad-pages=skip > /tmp/sbtest2_skip.sql
# 我们使用diff发现实际上少了292条数据.
17:27:28 [root@ddcw21 ibd2sql-ibd2sql-v2.x]#diff /tmp/sbtest2_skip.sql /tmp/sbtest2.sql | grep '^>' | wc -l
292


# 我们再使用fast模式看下能恢复多少数据
python3 main.py /tmp/sbtest2.ibd --ddl --sql --force --set bad-pages=fast > /tmp/sbtest2_fast.sql
# 对比数据,我们发现少了219条数据, 即从坏块里面恢复了73条数据
17:28:41 [root@ddcw21 ibd2sql-ibd2sql-v2.x]#diff /tmp/sbtest2_fast.sql /tmp/sbtest2.sql | grep '^>' | wc -l
219

# 我们最后使用下try模式看下能恢复多少数据
python3 main.py /tmp/sbtest2.ibd --ddl --sql --force --set bad-pages=try > /tmp/sbtest2_fast.sql
# 对比数据,我们发现少了75条数据, 即从坏块里面恢复了217条数据. 运气已经是非常好了
17:30:19 [root@ddcw21 ibd2sql-ibd2sql-v2.x]#diff /tmp/sbtest2_try.sql /tmp/sbtest2.sql | grep '^>' | wc -l
75
```

备注: mysql_ibd_corruption_danger.py脚本非常危险,仅限测试使用,脚本可见: https://cloud.tencent.com/developer/article/2579960