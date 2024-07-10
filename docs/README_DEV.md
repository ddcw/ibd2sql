本文主要系统的介绍 ibd 文件结构, 数据类型等.算是对[ibd2sql](https://github.com/ddcw/ibd2sql)的总结吧.  文本较长长长长长长.

作者: [DDCW](https://github.com/ddcw)

项目地址: https://github.com/ddcw/ibd2sql

更新时间: 2024-05-16 (ibd2sql v1.4)



# IBD FILE

我们知道 mysql的表 由一个ibd文件组成, 如果是5.7的, 还有一个frm文件.

ibd文件被 按照PAGE_SIZE(16KB)分为若干个页.   为了方便管理页, 又整了个区(extent). 每个区固定1MB. 区多了之后,就有专门的 PAGE (XDES)来描述区信息.  对于数据/主键和(二级)索引 都是使用BTREE+来存的,  叶子节点(LEAF-PAGE)和非叶子节点(Non LEAF-PAGE) 是独立的链表, 也叫做段(segment), 所以每个索引都有2个段, 通常记录段的起始位置即可.  非叶子节点的起始页 叫做ROOT PAGE (传说的开始.)



ibd文件里面包含了多个索引(主键和普通索引), 每个索引由2个segment组成, 分别为 非叶子节点 和叶子节点. 每次空间申请以extent (通常1MB)为单位, 每个extent由若干个PAGE(16384)组成.

```
                        INDEX1
                        INDEX2      SEGMENT (none leaf page)     EXTENT      PAGE      HEADER
TABLE --> IBD FILE -->  PK       -->                         --> EXTENT  --> PAGE  --> DATA
                        INDEX3      SEGMENT (leaf page)          EXTENT      PAGE      TRAILER
                        INDEX4
```

 ```
page size | FSP_EXTENT_SIZE  | Initial Size | Pages
----------+------------------+--------------+-------
    4 KB  | 256 pages = 1 MB |   16 MB      | 4096
    8 KB  | 128 pages = 1 MB |   16 MB      | 2048
   16 KB  |  64 pages = 1 MB |   16 MB      | 1024
   32 KB  |  64 pages = 2 MB |   16 MB      | 512
   64 KB  |  64 pages = 4 MB |   16 MB      | 256  
 ```

注: 未特殊说明, 均为大端字节序



## PAGE

看起来那么多东西, 实际上都是由页组成的. 页都有固定构成,  

1. FIL_HEADER, 
2. PAGE_DATA(数据, 每种页都不一样), 
3. FIL_TRAILER

### FIL_HEADER

每个页开头的部分, 记录校验值, 上一页,下一页之类的信息

| 对象                         | 大小   | 描述                             |
| -------------------------- | ---- | ------------------------------ |
| FIL_PAGE_SPACE_OR_CHECKSUM | 4    | 校验值, 和fil_trailer里的checksum做比较 |
| FIL_PAGE_OFFSET            | 4    | page offset inside space       |
| FIL_PAGE_PREV              | 4    | 上一页的PAGENO                     |
| FIL_PAGE_NEXT              | 4    | 下一页的PAGENO                     |
| FIL_PAGE_LSN               | 8    | LSN                            |
| FIL_PAGE_TYPE              | 2    | 页类型                            |
| FIL_PAGE_FILE_FLUSH_LSN    | 8    | FLUSH LSN                      |
| FIL_PAGE_SPACE_ID          | 4    | 表空间ID                          |

对于第一页FIL_PAGE_TYPE_FSP_HDR, FIL_PAGE_PREV是mysql server版本(花里胡哨的)

`On page 0 of the tablespace, this is the server version ID `



一共有 34 种PAGE. 本文只介绍一部分. 够用就行.

```
FIL_PAGE_INDEX = 17855;
FIL_PAGE_RTREE = 17854;
FIL_PAGE_SDI = 17853;
FIL_PAGE_TYPE_UNUSED = 1;
FIL_PAGE_UNDO_LOG = 2;
FIL_PAGE_INODE = 3;
FIL_PAGE_IBUF_FREE_LIST = 4;
FIL_PAGE_TYPE_ALLOCATED = 0;
FIL_PAGE_IBUF_BITMAP = 5;
FIL_PAGE_TYPE_SYS = 6;
FIL_PAGE_TYPE_TRX_SYS = 7;
FIL_PAGE_TYPE_FSP_HDR = 8;
FIL_PAGE_TYPE_XDES = 9;
FIL_PAGE_TYPE_BLOB = 10;
FIL_PAGE_TYPE_ZBLOB = 11;
FIL_PAGE_TYPE_ZBLOB2 = 12;
FIL_PAGE_TYPE_UNKNOWN = 13;
FIL_PAGE_COMPRESSED = 14;
FIL_PAGE_ENCRYPTED = 15;
FIL_PAGE_COMPRESSED_AND_ENCRYPTED = 16;
FIL_PAGE_ENCRYPTED_RTREE = 17;
FIL_PAGE_SDI_BLOB = 18;
FIL_PAGE_SDI_ZBLOB = 19;
FIL_PAGE_TYPE_LEGACY_DBLWR = 20;
FIL_PAGE_TYPE_RSEG_ARRAY = 21;
FIL_PAGE_TYPE_LOB_INDEX = 22;
FIL_PAGE_TYPE_LOB_DATA = 23;
FIL_PAGE_TYPE_LOB_FIRST = 24;
FIL_PAGE_TYPE_ZLOB_FIRST = 25;
FIL_PAGE_TYPE_ZLOB_DATA = 26;
FIL_PAGE_TYPE_ZLOB_INDEX = 27;
FIL_PAGE_TYPE_ZLOB_FRAG = 28;
FIL_PAGE_TYPE_ZLOB_FRAG_ENTRY = 29;
FIL_PAGE_TYPE_LAST = FIL_PAGE_TYPE_ZLOB_FRAG_ENTRY;
```





### FIL_TRAILER

这个比较简单, 就结尾8字节, 4字节校验值, 4字节lsn.  校验值和FIL_HEADER做对比的

`the low 4 bytes of this are used to store the page checksum, the last 4 bytes should be identical to the last 4 bytes of FIL_PAGE_LSN`

| 对象       | 大小   | 描述   |
| -------- | ---- | ---- |
| CHECKSUM | 4    | 校验值  |
| LSN      | 4    | LSN  |



## FIL_PAGE_TYPE_FSP_HDR

先来看看第一页 (虽然编号是8). 这一页记录这个表空间/ibd的基础信息的. 基础结构如下

| 对象           | 大小   | 描述                         |
| ------------ | ---- | -------------------------- |
| FIL_HEADER   | 38   | 页头                         |
| SPACE_HEADER | 112  | FIL_PAGE_TYPE_FSP_HDR的专属页头 |
| XDES 0       | 40   | extent描述页                  |
| XDES 1       | 40   | 第一页比较闲, 所以也顺便当当XDES_PAGE   |
| XDES ...     | ...  |                            |
| XDES 255     | 40   |                            |
| SDI VERSION  | 4    | 只有8.0才有 偏移量(10505)         |
| SDI PAGE NO  | 4    | 只有8.0才有                    |
| FIL_TRAILER  | 8    | 页尾                         |

如果是 5.7 升级到8.0的, SDI_PAGE就不固定位置了, 所以要在FIL_PAGE_TYPE_FSP_HDR里面记录.

```
#MAGIC_SIZE=3  KEY_LEN=32  SERVER_UUID_LEN=36
#(MAGIC_SIZE + sizeof(uint32) + (KEY_LEN * 2) + SERVER_UUID_LEN + sizeof(uint32))
INFO_SIZE = 3+4+32*2+36+4
INFO_MAX_SIZE = INFO_SIZE + 4
SDI_OFFSET = 38+112+40*256 + INFO_MAX_SIZE
SDI_VERSION = 1
```



XDES信息等到FIL_PAGE_TYPE_XDES了再讲, 不然FIL_PAGE_TYPE_XDES就没啥讲的了.



## FIL_PAGE_IBUF_BITMAP

第二页是insert buffer 页. 对解析数据没得帮助, 就跳过咯.



## FIL_PAGE_INODE

第三页是 INODE 页, 就是记录有哪些segment的. segment对应索引.

也只有这上面三页是固定的.

| 对象                   | 大小       | 描述                      |
| -------------------- | -------- | ----------------------- |
| FIL_HEADER           | 38       |                         |
| INODE INFO           | 12       | pre and next inode page |
| FSEG (SDI PAGE)      | 192      | 仅8.0有                   |
| FSEG (SDI PAGE)      | 192      | 仅8.0有                   |
| FSEG (PK)            | 192      | 主键非叶子节点                 |
| FSEG (PK)            | 192      | 主键    叶子节点              |
| FSEG (INDEX)         | 192      | 二级索引 非叶子节点              |
| FSEG (INDEX)         | 192      | 二级索引     叶子节点           |
| FSEG (INDEX)   ..... | 192 .... | 剩余的索引                   |
| FIL_TRAILER          | 8        |                         |

如果一个inode page不够, 那就再来一个, 毕竟innodb 支持64个二级索引, 每个 192*2 字节就是24576字节了, 超过一般的16384了.  但我们这里不做普通索引的解析, 所以下一个INODE在哪就不关心了.



FSEG 就是前面说的段, 2个段对应一个索引(非叶子节点和叶子节点), 通常非叶子节点是准确的, 但叶子节点信息就不对了. 所以需要我们通过 非叶子节点去寻找 叶子节点.  等后面讲INDEX_PAGE的时候再细谈.

| 对象                   | 大小   | 描述              |
| -------------------- | ---- | --------------- |
| FSEG_ID              | 8    | 段ID             |
| FSEG_NOT_FULL_N_USED | 4    | FSEG_NOT_FULL数量 |
| FSEG_FREE            | 16   | 未使用的区           |
| FSEG_NOT_FULL        | 16   | 用了,但未使用完的区      |
| FSEG_FULL            | 16   | 使用完了的区          |
| FSEG_MAGIC           | 4    | 97937874        |
| FSEG_FRAG_ARR        | 4*32 | 碎片区             |



## FIL_PAGE_SDI

SDI PAGE是记录元数据信息的页, 8.0才有的(所以没了frm文件).  基本上和INDEX PAGE 一样(编号也接近). 

结构如下:

| 对象             | 大小   | 描述              |
| -------------- | ---- | --------------- |
| FIL_HEADER     | 38   |                 |
| PAGE_HEADER    | 56   | 见FIL_PAGE_INDEX |
| INFIMUM        | 13   | 最小记录            |
| SUPEREMUM      | 13   | 最大记录            |
| SDI_DATA       | xx   | 使用zip压缩的json对象  |
| PAGE_DIRECTORY | xx   | 见FIL_PAGE_INDEX |
| FIL_TRAILER    | 8    |                 |

我们可以使用官方的 `ibd2sdi`解析ibd文件得到元数据信息, 美化过的JSON数据. 我们也可以自己解析.

参考代码: https://cloud.tencent.com/developer/article/2272631

```python
offset = struct.unpack('>H',self.bdata[PAGE_NEW_INFIMUM-2:PAGE_NEW_INFIMUM])[0] + PAGE_NEW_INFIMUM
dtype,did = struct.unpack('>LQ',self.bdata[offset:offset+12])
dtrx = int.from_bytes(self.bdata[offset+12:offset+12+6],'big')
dundo = int.from_bytes(self.bdata[offset+12+6:offset+12+6+7],'big')
dunzip_len,dzip_len = struct.unpack('>LL',self.bdata[offset+33-8:offset+33])
unzbdata = zlib.decompress(self.bdata[offset+33:offset+33+dzip_len])
dic_info = json.loads(unzbdata.decode())
return dic_info if len(unzbdata) == dunzip_len else {}
```

解析出来之后可以人工拼接为DDL, 但是太麻烦了(属性太多了, ibd2sql也是最近才支持的子分区). 可以使用`ibd2sql` 将其转化为DDL.



前缀索引判断条件:

```
indexes[x]['elements'][x]['length'] < col['char_length'] 
```



索引类型判断

```
index[x]['type']如下值:
1: PRIMARY
2: UNIQUE
3: NORMAL
```



虚拟列无实际数据, 解析的时候要注意下.



8.0.12 及其之前 字段无 hidden属性

8.0.13 及其之前, 时间字段默认函数, 不能有括号



对于使用类似如下DDL 添加字段默认ALGORITHM是 INSTANT

```
ALTER TABLE tbl_name ADD COLUMN column_name column_definition, ALGORITHM=INSTANT;
```

为了快速添加字段, 会在元数据信息记录相关信息

```
dd_object:  "se_private_data": "instant_col=1;"
column:     "se_private_data": "default=636363;table_id=2041;"
```



## FIL_PAGE_TYPE_XDES

这个PAGE对解析ibd文件其实没啥帮助的. 也就不细看了.

| 对象          | 大小     | 描述   |
| ----------- | ------ | ---- |
| FIL_HEADER  | 38     |      |
| XDES 0      | 40     |      |
| XDES 1      | 40     |      |
| XDES ...    | 40 ... |      |
| XDES 255    | 40     |      |
| FIL_TRAILER | 8      |      |

XDES格式如下:

| 对象             | 大小   | 描述        |
| -------------- | ---- | --------- |
| XDES_ID        | 8    | xdes id   |
| XDES_FLST_NODE | 12   | data list |
| XDES_STATE     | 4    | extent状态  |
| XDES_BITMAP    | 16   |           |



## FIL_PAGE_INDEX

INDEX PAGE就是记录数据的页, 也是本文的重点之一, 会花费较多的篇幅来介绍.

结构如下:

| 对象             | 大小   | 描述                |
| -------------- | ---- | ----------------- |
| FIL_HEADER     | 38   |                   |
| PAGE_HEADER    | 56   | INDEX PAGE HEADER |
| INFIMUM        | 13   | 最小记录              |
| SUPEREMUM      | 13   | 最大记录              |
| RECORD DATA    | xx   | 具体的数据行            |
| PAGE_DIRECTORY | n*2  | 页内目录(方便数据查找的)     |
| FIL_TRAILER    | 8    |                   |

PAGE_HEADER 结构如下,:

基本上都是对数据查询有帮助的(各种链表), 我们解析ibd文件并不需要这么多信息.

为了后面解析 ROW, 我这里就还是称它为RECORD 

| 对象                | 大小   | 描述                           |
| ----------------- | ---- | ---------------------------- |
| PAGE_N_DIR_SLOTS  | 2    | PAGE_DIRECTORY槽的数量           |
| PAGE_HEAP_TOP     | 2    | 第一条record位置                  |
| PAGE_N_HEAP       | 2    | 堆中的record数                   |
| PAGE_FREE         | 2    | 空闲record位置                   |
| PAGE_GARBAGE      | 2    | 被删除的record位置                 |
| PAGE_LAST_INSERT  | 2    | 最新插入的record                  |
| PAGE_DIRECTION    | 2    | 最新插入的record方向?               |
| PAGE_N_DIRECTION  | 2    | 相同方向连续插入record数量             |
| PAGE_N_RECS       | 2    | record 数量, (行数)              |
| PAGE_MAX_TRX_ID   | 8    | 最大事务ID, 二级索引和insert buffer用的 |
| PAGE_LEVEL        | 2    | 在btr+的深度                     |
| PAGE_INDEX_ID     | 8    | index id                     |
| PAGE_BTR_SEG_LEAF | 10   | 叶子节点(只有root_page才有.)         |
| PAGE_BTR_SEG_TOP  | 10   | 非叶子节点(只有root_page才有.)        |



INFIMUM 和 SUPEREMUM 分别表示最小字段和最大字段.



RECORD DATA 要分多种情况, 叶子节点/非叶子节点 下的 主键索引和二级索引. 

| 对象                  | 大小               | 描述                                       |
| ------------------- | ---------------- | ---------------------------------------- |
| variabels of length | 每个可变字段使用1-2字节    | 可变字段的长度记录. 如果超过页大小,则为溢出页, 只读取20字节.       |
| null bitmask        | 每个可为空的字段使用1bit表示 | 可为空的字段                                   |
| record_header       | 5                | record类型,下一个record相对位置等信息                |
| KEY/ROW_ID          |                  | 如果没得主键, 就是6字节的row id                     |
| TRX_ID              | 6                | 叶子节点才有事务ID                               |
| ROLL_PTR            | 7                | 叶子节点才有回滚指针                               |
| Non-KEY FILEDS      |                  | 如果是非叶子节点, 就是4字节的PAGE ID; 如果是叶子节点,就是非索引字段的数据. |
| INSTANT DATA        |                  | 如果做过ONLINE DDL, 则记录放在record最后面.          |

主要是instant data这里比较坑, 数据是放在普通字段的后面的. 读取的时候要注意下.  怎么知道是否有做过instant呢? 这就是我们马上要讲的 record_header

record_header 结构如下:

| 对象           | 大小     | 描述                                      |
| ------------ | ------ | --------------------------------------- |
| instant flag | 2 bit  | 标记是否有instant字段                          |
| deleted      | 1 bit  | 表明这行数据是否被删除                             |
| min_rec      | 1 bit  | 是否是最小record                             |
| owned        | 4 bit  | page directory记录的就是这个                   |
| heap number  | 13 bit | 堆号(递增) 0:INFIMUM  max:SUPREMUM (不一定准..) |
| record_type  | 3 bit  | 0:rec  1:no-leaf  2:min  3:max          |
| next_record  | 16 bit | 下一个字段的相对偏移量(有符合哦)                       |

这个next_record是指向的  下一个字段的record_header和key中间. 所以对于 var-length,null-bitmask,record_header都得反向读.



PAGE_DIRECTORY 只是查找数据方便, 使用2字节表示每个slot. 对于我们全量解析数据没用. 就不看了.



有了这些信息, 还不能解析数据, 因为对于非varchar类 的数据类型 存储方式千奇百怪(固定+metadata). 得等`COLUMN TYPE`讲完了来.



## FIL_PAGE_TYPE_LOB_FIRST

参考: https://cloud.tencent.com/developer/article/2417124

当某行数据在1页里面记录不下的时候, 就放到溢出页里面, index_page只记录基础信息20字节, 格式如下:

| 对象          | 大小(字节) | 描述                     |
| ----------- | ------ | ---------------------- |
| SPACE_ID    | 4      | 表空间ID                  |
| PAGENO      | 4      | 表空间里的页号                |
| BLOB_HEADER | 4      | BLOB_HEADER的大小, 固定 为 1 |
| REAL_SIZE   | 8      | 这行数据中这个字段的大小           |

这个SPACE_ID指向的就是 lob_first. 我们这里就先不看压缩页了.

FIL_PAGE_TYPE_LOB_FIRST 格式如下:

| 对象                      | 大小(字节)                  | 描述                                 |
| ----------------------- | ----------------------- | ---------------------------------- |
| FIL_PAGE_DATA           | 38                      | FILE头, PAGE都有的那玩意.之前讲过             |
| OFFSET_VERSION          | 1                       | 版本,为1                              |
| OFFSET_FLAGS            | 1                       | flag, 目前就用了1bit,先不用管               |
| OFFSET_LOB_VERSION      | 4                       | BLOB版本                             |
| OFFSET_LAST_TRX_ID      | 6                       | 最新修改的事务ID                          |
| OFFSET_LAST_UNDO_NO     | 4                       | 对应的undo no                         |
| OFFSET_DATA_LEN         | 4                       | 数据大小                               |
| OFFSET_TRX_ID           | 6                       | 创建时的事务ID                           |
| OFFSET_INDEX_LIST       | FLST_BASE_NODE_SIZE(16) | INDEX信息,                           |
| OFFSET_INDEX_FREE_NODES | LST_BASE_NODE_SIZE(16)  | 空闲的entry(就是羡慕的LOB_PAGE_DATA),      |
| LOB_PAGE_DATA           | 10*index_entry_t=600    | index信息, 第一页只放10个, 不够再由LOB_INDEX来放 |
| DATA                    | n                       | 剩余的空间可以用来放数据                       |

FLST_BASE_NODE_SIZE 这种结构, 之前讲过, 就是 4+6+6  也就是 LEN, PRE_PAGENO,PRE_OFFSET    NEXT_PAGENO, NEXT_OFFSET.  

如果是0/4294967295就表示没得上/下节点了

| 对象          | 大小(bytes) | 描述                 |
| ----------- | --------- | ------------------ |
| LEN         | 4         | 数据大小               |
| PRE_PAGENO  | 4         | 上一节点(LOB_INDEX)的页号 |
| PRE_OFFSET  | 2         | 上一节点的页内偏移量         |
| NEXT_PAGENO | 4         | 下一节点的页号            |
| NEXT_OFFSET | 2         | 下一节点的页内偏移量         |



再来看看这个 LOB_PAGE_DATA, 就是ENTRY, 每个60字节, 第一页10个`constexpr static ulint node_count() {return (10);}` 参考: storage/innobase/include/lob0index.h :: index_entry_t

这里面就是记录 实际的值了, 全部加起来就是这行数据这个字段的 值了. 直接上表:

**ENTRY**:

| 对象                          | 大小                      | 描述                 |
| --------------------------- | ----------------------- | ------------------ |
| OFFSET_PREV                 | FIL_ADDR_SIZE(6)        | 上一个entry的信息        |
| OFFSET_NEXT                 | FIL_ADDR_SIZE(6)        | 下一个entry的信息        |
| OFFSET_VERSIONS             | FLST_BASE_NODE_SIZE(16) | 大小, 起止entry信息      |
| OFFSET_TRXID                | 6                       | 创建时的事务ID           |
| OFFSET_TRXID_MODIFIER       | 6                       | 修改时的事务ID           |
| OFFSET_TRX_UNDO_NO          | 4                       | 创建时事务时候的UNDO NO    |
| OFFSET_TRX_UNDO_NO_MODIFIER | 4                       | 修改时事务时候的UNDO NO    |
| OFFSET_PAGE_NO              | 4                       | PAGE NO (LOB_DATA) |
| OFFSET_DATA_LEN             | 4                       | 大小(实际上就前2个字节)      |
| OFFSET_LOB_VERSION          | 4                       | LOB VERSION        |

OFFSET_PAGE_NO  就是指的LOB DATA的页号, OFFSET_DATA_LEN 就是lOB DATA页里面存储的数据大小(虽然是4字节, 实际只使用2字节).



## FIL_PAGE_TYPE_LOB_INDEX

记录索引信息, 就是ENTRY, 比较简单.结构如下:

参考: storage/innobase/include/lob0index.h

| 对象              | 大小    | 描述                       |
| --------------- | ----- | ------------------------ |
| FIL_PAGE_DATA   | 38    | FIL_PAGE_DATA            |
| OFFSET_VERSION  | 1     | LOB VERSION              |
| OFFSET_DATA_LEN | 4     | 数据长度                     |
| OFFSET_TRX_ID   | 6     | 事务ID                     |
| LOB_PAGE_DATA   | entry | 一个个entry, 每个60字节, 结构见上面的 |

## FIL_PAGE_TYPE_LOB_DATA

存放LOB数据的, 结构同FIL_PAGE_TYPE_LOB_INDEX  就把entry换成 data就是了.

参考: storage/innobase/include/lob0pages.h



# FRM FILE

mysql 5.7没得sdi page, 但是有frm文件, 这里面也是记录的元数据信息.  

结构如下:

| 对象            | 大小   | 描述                       |
| ------------- | ---- | ------------------------ |
| frm_type      | 2    | frm类型, 510 是表  22868 是视图 |
| HEADER_FORMAT | 64   | 文件头,                     |
| KEY           |      | 索引信息                     |
| default       |      | 默认值                      |
| engine        |      | 存储引擎(HEADER_FORMAT也有)    |
| comment       |      | 表的注释                     |
| record        |      | 字段信息                     |

看起来还是比较简单的. 接下来我们来看看详情.

frm_type就不看了, 没啥好说的, 就2字节, **510 是表  22868 是视图** .

不细看了, 感兴趣的自己去看: https://cloud.tencent.com/developer/article/2409341

参考: mysqlfrm



# COLUMN TYPE

这一章主要讲mysql的数据类型.  严格来说是innodb的数据类型. 除了JSON,均为大端字节序

## 数字类型

数字类型, 存在符号. 符号使用第一bit位.

| 对象        | 大小                           | 描述                     |
| --------- | ---------------------------- | ---------------------- |
| tinyint   | 1                            |                        |
| smallint  | 2                            |                        |
| mediumint | 3                            |                        |
| int       | 4                            |                        |
| float(n)  | size = 4 if ext <= 24 else 8 | 如果metadata超过24就是double |
| double    | 8                            |                        |
| bigint    | 8                            |                        |

通用取值方式参考:

```python
#_t 是数据
#_s 是字节数
(_t&((1<<_s)-1))-2**_s if _t < 2**_s and not is_unsigned else (_t&((1<<_s)-1))
```



decimal 这个类型比较特殊,  分为整数部分和小数部分存储, 9位10进制数占4字节. 剩余的就按 1-2 为1字节, 这样算. 比如:

```
(5,2)   整数就是2字节, 小数也是1字节
(10,3) 整数就是4+1字节, 小数就是2字节
```



## 日期类型

date

```
固定3字节 1bit符号,  14bit年  4bit月  5bit日
-----------------------------------
|     signed   |     1  bit       |
-----------------------------------
|      year    |     14 bit       |
-----------------------------------
|     month    |     4  bit       |
-----------------------------------
|      day     |     5  bit       |
-----------------------------------
```



datetime

```
5 bytes + fractional seconds storage
1bit符号  year_month:17bit  day:5  hour:5  minute:6  second:6
---------------------------------------------------------------------
|             signed                 |          1  bit              |     
|--------------------------------------------------------------------
|         year and month             |          17 bit              |
|--------------------------------------------------------------------
|             day                    |          5  bit              |
|--------------------------------------------------------------------
|             hour                   |          5  bit              |
|--------------------------------------------------------------------
|            minute                  |          6  bit              |
|--------------------------------------------------------------------
|            second                  |          6  bit              |
---------------------------------------------------------------------
|      fractional seconds storage    |each 2 digits is stored 1 byte|
---------------------------------------------------------------------


```



time

```
1bit符号  hour:11bit    minute:6bit  second:6bit  精度1-3bytes
-------------------------------------------------------------------
|            signed            |              1  bit              |
-------------------------------------------------------------------
|             hour             |              11 bit              |
-------------------------------------------------------------------
|            minute            |              6  bit              |
-------------------------------------------------------------------
|            second            |              6  bit              |
-------------------------------------------------------------------
|  fractional seconds storage  |  each 2 digits is stored 1 byte  |
-------------------------------------------------------------------

```



timestamp

```
4 bytes + fraction
```



year

```
year 使用1字节存储, 值+1900 即表示年	 范围: '1901' to '2115'
```





## 字符类型

1. 如果是 CHAR类型, 且字符集为ascii, 则不用使用var-length去记录数据长度, 直接使用metadata长度.
2. char/varchar/lob/text/json/binary/GIS等均有var-length记录长度,  规则为: 第一字节小于等于 128 字节时, 就1字节.  否则就第一字节超过128字节的部分 *256 再加上第二字节部分来表示总大
   小 就是256*256 =  65536.

| 类型                       | 大小(字节)                                   | 范围        | 备注   |
| ------------------------ | ---------------------------------------- | --------- | ---- |
| char(M)                  | L                                        | <=255 字符  |      |
| BINARY(M)                | M                                        | <=255 字节  |      |
| VARCHAR(M), VARBINARY(M) | 1 字节长度 + L: 当 L < 1282 字节长度 + L: 当L >=128 | <=65535字节 |      |
| TINYBLOB, TINYTEXT       | L + 1 bytes, where L < 256               | < 256 B   |      |
| BLOB, TEXT               | L + 2 bytes, where L < 2**16             | <=65535字节 |      |
| MEDIUMBLOB, MEDIUMTEXT   | L + 3 bytes, where L < 2**24             | 16M       |      |
| LONGBLOB, LONGTEXT       | L + 4 bytes, where L < 2**32             | 4G        |      |

3. enum/set

| 类型   | 大小                                       |
| ---- | ---------------------------------------- |
| ENUM | 1 or 2 bytes, depending on the number of enumeration values (65,535 values maximum) |
| SET  | 1, 2, 3, 4, or 8 bytes, depending on the number of set members (64 members maximum) |



## GEOM

mysql支持直接hex格式数据, 故直接做hex即可. 如果没得srsid开头, 则需要补齐. 用得不多, 就不研究了.



## JSON

json是mysql对其二进制化的, 对于innodb只是普通的二进制而已.所以对于数字的存储是使用的小端, 对于可变长字符串存储是使用的256*128这种.  存储方式就是套娃(递归)

```
如果第一bit是1 就表示要使用2字节表示:
后面1字节表示 使用有多少个128字节, 然后加上前面1字节(除了第一bit)的数据(0-127) 就是最终数据
-----------------------------------------------------
| 1 bit flag | 7 bit data | if flag, 8 bit data*128 |
-----------------------------------------------------

                                                               - -----------------
                                                              | JSON OBJECT/ARRAY |
                                                               - -----------------
                                                                      |
 -------------------------------------------------------------------------
| TYPE | ELEMENT_COUNT | KEY-ENTRY(if object) | VALUE-ENTRY | KEY | VALUE |
 -------------------------------------------------------------------------
                               |                    |          |
                               |                    |     --------------
                   --------------------------       |    | UTF8MB4 DATA |
                  | KEY-OFFSET |  KEY-LENGTH |      |     --------------
                   --------------------------       |
                                                    |
                                         --------------------------------
                                         | TYPE | OFFSET/VALUE(if small) |
                                         --------------------------------


```




