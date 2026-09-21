本文为ibd2sql v2.x恢复被truncate的表

truncate table相当于drop+create

# 恢复被truncate表的原理

ibd2sql解析数据需要的是元数据信息和数据页.

元数据信息: 当表被truncate之后, 5.x版本还会保存原来的信息, 但8.x版本是使用的update,也就看不到update之前的信息了.

数据页: 当表被truncate之后,文件系统层面的文件inode信息会变(因为已经是新文件了), 但一般不会马上对之前的文件的使用空间进行回收.所以我们只需要把整个磁盘当作数据文件来进行扫描就能获取到我们需要的数据页了.

Windows和Linux使用方法一样, 这里就以Linux环境为主了. 但5.7和8.0使用差别较大, 我们分开来演示.



# 5.x 恢复被truncate的表

我们首先还是获取被truncate表的index和表结构.  ibdata1中记录的表结构不全(但是没关系, 我们是truncate,所以还有frm文件在呢)

```shell
# 获取表的tableid (sys_tables的第2个字段)
python3 main.py /data/mysql_5744/mysqldata/ibdata1 --set table=sys_tables --sql | grep t20260920_02 | tail -2 | head -1 | awk -F ',' '{print $2}'


# 根据上一步的tableid(假设是30386)获取indexid (sys_indexes的第2个字段)
python3 main.py /data/mysql_5744/mysqldata/ibdata1 --set table=sys_indexes --sql | grep '(30386' | tail -2 | head -1 | awk -F ',' '{print $2}'

# 根据indexid(假设是30472)扫描磁盘
python3 main.py --scan /dev/mapper/centos-root --set indexid=30472 --output=/tmp --parallel 8

# 根据元数据信息和上面扫描到的page文件进行恢复
python3 main.py /tmp/sql/*0000000000030472.page  --sdi /data/mysql_5744/mysqldata/db1/t20260920_02.frm --set leafno=0 --set rootno=0 --force --sql
```





# 8.x 恢复被truncate的表

在8.x版本中truncate表,系统表是对应的update操作,所以无法在系统表里面看到之前的indexid信息了. 不要怕,任何写操作都会对应redo,我们只需要解析redo获取对应的indexid即可. 很好,我们已经提前写好解析redo的脚本了: https://github.com/ddcw/redo

既然能够解析redo了, 那我们就有2种获取indexid的方法了

有2种方法:

1. 直接查看redo的MLOG_UNDO_INSERT (把update前的内容insert到undo里面去)

   ```shell
   # 根据MLOG_UNDO_INSERT获取index
   python3 redo_reader.py /data/mysql_8037/mysqllog/redolog/#innodb_redo/#ib_redo41 --set name=MLOG_UNDO_INSERT | strings |grep ';space_id'
       data      : b'L\x00\x11\x13\x00\x00\x00\x01\x04g\xc2\x00\x00\x01\xa8.\xe9\x08\x00\x00\x00\x00\x00\x00\x02D\x02\x0e6id=475;root=4;space_id=253;table_id=1315;trx_id=66663;\x0f\x08\x00\x00\x00\x00\x00\x00\x01\x02\x00)\x00\x08\x00\x00\x00\x00\x00\x00\x02D\x03\x08\x00\x00\x00\x00\x00\x00\x02\x89\x04\x07PRIMARY\x0f\x08\x00\x00\x00\x00\x00\x00\x01\x02'
       data      : b"L\x00\x11\x13\x00\x00\x00\x01\x04t\xc1\x00\x00\x01'+i\x08\x00\x00\x00\x00\x00\x00\x02D\x02\x0e6id=476;root=;space_id=254;table_id=1316;trx_id=66676;\x0f\x08\x00\x00\x00\x00\x00\x00\x01\x03\x00)\x00\x08\x00\x00\x00\x00\x00\x00\x02D\x03\x08\x00\x00\x00\x00\x00\x00\x02\x89\x04\x07PRIMARY\x0f\x08\x00\x00\x00\x00\x00\x00\x01\x03"
       data      : b'L\x00\x11\x13\x00\x00\x00\x01\x0e\xa5\xc1\x00\x00\x01\xba+t\x08\x00\x00\x00\x00\x00\x00\x02z\x02\x0e6id=529;root=4;space_id=292;table_id=1354;trx_id=69285;\x0f\x08\x00\x00\x00\x00\x00\x00\x01)\x00)\x00\x08\x00\x00\x00\x00\x00\x00\x02z\x03\x08\x00\x00\x00\x00\x00\x00\x02\xb4\x04\x07PRIMARY\x0f\x08\x00\x00\x00\x00\x00\x00\x01)'
       
   这里需要人工判断哪个是我们需要的
   如果没有其它truncate操作了,那么就是最后一个中的id=529, 这个529就是我们需要的indexid
   如果还有其它truncate操作的话,那就得麻烦点了.
   ```

   

2. 根据redo记录的MLOG_REC_UPDATE_IN_PLACE的rollptr去找undo信息(undo解析脚本:https://github.com/ddcw/ddcw/tree/master/python/undo_reader)

   ```shell
   # 根据MLOG_REC_UPDATE_IN_PLACE获取对应事务的roolptr
   python3 redo_reader.py /data/mysql_8037/mysqllog/redolog/#innodb_redo/#ib_redo41 --set name=MLOG_REC_UPDATE_IN_PLACE | strings |grep ';space_id' -B 17
   - [S] file:#ib_redo41 gblockno:1343346 lsn:687792704 cblockno:9 offset:064 name:MLOG_REC_UPDATE_IN_PLACE(70)
       spaceno   : 4294967294
       pageno    : 1154
       index_version: 1
       index_flags: 1
       cols      : 19
       inst_cols : None
       n_uniq    : 1
       index_fields: [32776, 32774, 32775, 32776, 32768, 32769, 32769, 32769, 32769, 32769, 32769, 32772, 65535, 32767, 32767, 8, 32768, 32767, 32767]
       index_versioned_fields: None
       flags     : 2
       pos       : 1
       roll_ptr  : 281474996054889
       trx_id    : 66676
       rec_offset: 8232
       info_bits : 0
       n_fields  : 2
       fields    : [{'field_no': 14, 'field_len': 54, 'field_value': b'id=476;root=4;space_id=254;table_id=1316;trx_id=66676;'}, {'field_no': 15, 'field_len': 8, 'field_value': b'\x00\x00\x00\x00\x00\x00\x01\x03'}]
   --
   - [S] file:#ib_redo41 gblockno:1343374 lsn:687807466 cblockno:37 offset:490 name:MLOG_REC_UPDATE_IN_PLACE(70)
       spaceno   : 4294967294
       pageno    : 1154
       index_version: 1
       index_flags: 1
       cols      : 19
       inst_cols : None
       n_uniq    : 1
       index_fields: [32776, 32774, 32775, 32776, 32768, 32769, 32769, 32769, 32769, 32769, 32769, 32772, 65535, 32767, 32767, 8, 32768, 32767, 32767]
       index_versioned_fields: None
       flags     : 2
       pos       : 1
       roll_ptr  : 281475005296200
       trx_id    : 66697
       rec_offset: 8232
       info_bits : 0
       n_fields  : 2
       fields    : [{'field_no': 14, 'field_len': 54, 'field_value': b'id=477;root=4;space_id=255;table_id=1317;trx_id=66697;'}, {'field_no': 15, 'field_len': 8, 'field_value': b'\x00\x00\x00\x00\x00\x00\x01\x04'}]
   --
   - [S] file:#ib_redo41 gblockno:1345833 lsn:689066428 cblockno:2496 offset:444 name:MLOG_REC_UPDATE_IN_PLACE(70)
       spaceno   : 4294967294
       pageno    : 1154
       index_version: 1
       index_flags: 1
       cols      : 19
       inst_cols : None
       n_uniq    : 1
       index_fields: [32776, 32774, 32775, 32776, 32768, 32769, 32769, 32769, 32769, 32769, 32769, 32772, 65535, 32767, 32767, 8, 32768, 32767, 32767]
       index_versioned_fields: None
       flags     : 2
       pos       : 1
       roll_ptr  : 562949973419447
       trx_id    : 69302
       rec_offset: 15620
       info_bits : 0
       n_fields  : 2
       fields    : [{'field_no': 14, 'field_len': 54, 'field_value': b'id=530;root=4;space_id=293;table_id=1355;trx_id=69302;'}, {'field_no': 15, 'field_len': 8, 'field_value': b'\x00\x00\x00\x00\x00\x00\x01*'}]
       
   这里需要人工判断哪个roll_ptr是我们需要的,如果没有其它truncate操作了,那么就是最后一个中的roll_ptr=562949973419447就是我们需要的rollptr
   
   
   # 然后根据rollptr去对应的undo中获取相关的indexid
   python3 undo_reader.py /data/mysql_8037/mysqldata/undo_002 -r 562949973419447
   
   PAGENO:305  OFFSET:9655 --> 9793  rseg_id:2  is_insert:False
   DATA: b'L\x00\x11\x13\x00\x00\x00\x01\x0e\xa5\xc1\x00\x00\x01\xba+t\x08\x00\x00\x00\x00\x00\x00\x02z\x02\x0e6id=529;root=4;space_id=292;table_id=1354;trx_id=69285;\x0f\x08\x00\x00\x00\x00\x00\x00\x01)\x00)\x00\x08\x00\x00\x00\x00\x00\x00\x02z\x03\x08\x00\x00\x00\x00\x00\x00\x02\xb4\x04\x07PRIMARY\x0f\x08\x00\x00\x00\x00\x00\x00\x01)'
   我们再次找到了id=529,这个529就是我们需要的indexid
   ```

   

获取到indexid之后,后续的步骤和5.7就一样了.

```shell
# 根据indexid(假设是529)扫描磁盘
python3 main.py --scan /dev/mapper/centos-root --set indexid=529 --output=/tmp --parallel 8

# 根据元数据信息和上面扫描到的page文件进行恢复
python3 main.py /tmp/sql/*0000000000000529.page  --sdi /data/mysql_8037/mysqldata/db1/t20260920_03.ibd --set leafno=0 --set rootno=0 --force --sql
```

