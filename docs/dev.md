本文主要记录ibd2sql v2.x版本的接口.(基于v2.4版本)

# 基础

如果要解析一行数据, 那么我们就需要知道各字段的数据类型,大小等信息,即元数据信息. 元数据信息可以来自ibd,frm,sdi

# 接口介绍

我们主要将接口分为3类:

ibd2sql:负责提取元数据信息,并发之类的偏向于外部的接口.

innodb_page: 解析元数据信息,解析各种页.属于核心部分.

utiles: 工具类,校验,解压缩,解密,解码等通用类.



## ibd2sql

主要包含两个文件: ibd2sql/ibd2sql.py和ibd2sql/frm/frm2sdi.py

我们先来看看ibd2sql/ibd2sql.py

| 函数名                      | 输入                                        | 输出      | 备注                             |
| --------------------------- | ------------------------------------------- | --------- | -------------------------------- |
| GET_LEAF_PAGE_NO_FROM_SDI   | PAGE_READER,pageid                          | pageid    | 返回sdi segment的第一个叶子节点  |
| IBDBASE                     | filename,log,kd                             | sdi       | 解析文件获取SDI信息              |
| GET_PARTITION_TABLE_SDIDATA | filename_t,log,kd                           | -         | 获取分区表的SDI信息              |
| FORMAT_IBD_FILE             | filename_list,sdi_file,keyring_file,log     | file_list | 含有sdi等基础信息的文件列表      |
| FIND_LEAF_PAGE_FROM_ROOT    | pg,pageid,table,page_type                   | pageid    | 从root节点寻找btr+第一个叶子节点 |
| ROTAED_FILE                 | f,log                                       | f         | 轮转文件的                       |
| IBD2SQL_SINGLE              | table,file_base,opt,filename_pre,log,parser | sql/文件  | 通过INDEX获取数据                |
| IBD2SQL_WORKER              | -                                           | sql/文件  | 工作进程                         |

ibd2sql/frm/frm2sdi.py主要是将frm文件转为sdi的

直接看例子吧:

```python
from ibd2sql.frm.frm2sdi import MYSQLFRM
aa = MYSQLFRM('/data/mysql_5744/mysqldata/db1/t1.frm')
sdi = aa._get_sdi_json() # 这就是json格式的sdi信息了.
```



## innodb_page

位于ibd2sql/innodb_page目录下,这玩意有点多. 我们一个个文件的看



column_type.py: 记录各数据类型是否是变量



fsp.py: 解析FIL_PAGE_TYPE_FSP_HDR的.

```txt
GET_FSP_STATUS_FROM_FLAGS 解析FIL_PAGE_TYPE_FSP_HDR中的STATUS,比如: 页大小,压缩等信息
PARSE_ENCRYPTION_INFO 加密相关的解析,获取key和iv
FSP 解析FIL_PAGE_TYPE_FSP_HDR
```



index.py: 核心模块,解析btr+的,只有一个class,即INDEX. 各函数作用如下:

```txt
init_index 初始化index对象的,负责预先处理一些参数的.
init_data  某个页解析完了,不需要新建对象,只需要调用此方法,更新新的page即可.

get_data   调用get_all_rows处理数据的(instant默认值),返回data格式数据

get_sql    虚拟接口,方便统一调用的,返回sql格式数据
_get_sql_single 对get_sql的实现,一条insert一行数据
_get_sql_multi  对get_sql的实现,一条insert多行数据

get_all_rows 获取一页的所有数据(dict)
get_all_rows_fast 解析坏块时,参考page directory的方式,返回dict格式数据
get_all_rows_try  解析坏块时,尽可能的获取数据,返回dict格式数据
_get_all_rows_compressed 如果是压缩页,则使用此函数替换get_all_rows

_read_nullbitmask_varsize_old 解析record header前面的nullbitmask和varsize的(REDUNDANT)
_read_nullbitmask_varsize_new 解析record header前面的nullbitmask和varsize的

_read_trx_id_rollptr 解析record中的trxid和rollptr
_read_trx_id_format  格式化trxid和rollptr
_read_trx_id_rollptr_compressed 解析record中的trxid和rollptr(compresse)

_read_row 虚拟接口,读取一行数据
_read_row_pk_leaf      实现_read_row,解析主键叶子节点数据
_read_row_pk_non_leaf  实现_read_row,解析主键非叶子节点数据
_read_row_key_leaf     实现_read_row,解析二级索引叶子节点数据
_read_row_key_non_leaf 实现_read_row,解析二级索引非叶子节点数据

_read_field 读取一个字段

_read_row_version 读取row_version(instant)
_read_row_count  读取row_count(instant) <=8.0.28

_read_rec_header_old 读取一行数据的record header(REDUNDANT)
_read_rec_header_new 读取一行数据的record header

_read_extra_column_with_768 读取字段溢出页部分数据(REDUNDANT,COMPACT)
_read_extra_column 读取字段溢出页部分数据
_read_extra_column_1 读取溢出页数据
_read_extra_20  读取业内记录的溢出页信息20字节
_read_extra_20_compressed 读取业内记录的溢出页信息20字节(compressed)
_read_compressed_start 压缩页读取,前->后
_read_compressed_end  压缩页读取,后->前
```



inode.py 解析ibd中的Inode信息(一个索引2个segment,root一个,叶子节点一个)



lob.py: 溢出页的读取,分为FIRST_BLOB(非压缩页)和FIRST_ZBLOB(压缩页)两个方法.



page.py 页内操作的基础方法

```txt
PAGE_READER 业内读取数据(可能需要解密或者解压缩)
PAGE 页的基础操作类
```



sdi.py 解析FIL_PAGE_SDI 的



subpartition.py 子分区ddl的拼接



table.py 将sdi转为TABLE对象, 方便生成DDL与数据解析.

```txt
TABLE 输出只有一个sdi, 可调用的方法有:
	get_ddl 获取DDL语句
	get_ddl_reference 获取DDL语句,不含外键
	get_ddl_key 返回alter的加索引语句
	get_ddl_history 获取历史DDL执行情况
```



xdes.py 解析FIL_PAGE_TYPE_XDES的



## utiles

一些通用类, 位于ibd2sql/utils/目录下

aes.py 解析加盟的mysql数据文件的时候使用的,实现了aes_ecb256_decrypt和aes_cbc256_decrypt



b2data.py 将各类型的二进制数据解码.



check_table_old.py 块校验(老版本)



collations.py 记录各字符集的信息



crc32c.py 坏块校验(CHECK_PAGE)与更新(REPACK_PAGE)块校验信息



keyring_file.py 解析kering文件的,返回dict形式的kv



lz4.py 解析使用lz4压缩的mysql数据.



mysql_json.py 解码mysql中二进制的json数据



## 其它

ibd2sql/web.py 提供web接口访问ibd数据文件的

ibd2sql/scan_drop_table.py 通过扫描磁盘恢复mysql数据的





# 例子

百看不如一练, 我们来瞅瞅几个例子. 

为了方便理解, 我们使用尽可能简单的代码来演示



## 获取DDL

从ibd(8.0及其以上版本没有frm)中获取ddl

```python
from ibd2sql.ibd2sql import FORMAT_IBD_FILE
from ibd2sql.innodb_page.table import TABLE
# 日志系统是必选参数...
class LOG():
    	def info(self,*args):
            	pass

log = LOG()
from ibd2sql.ibd2sql import FORMAT_IBD_FILE
filename = '/data/mysql_8037/mysqldata/db1/t1.ibd'
fobj = FORMAT_IBD_FILE([filename],None,None,log)[0]

table = TABLE(fobj['sdi'])
print(table.get_ddl())
```



从frm中获取ddl

```txt
from ibd2sql.ibd2sql import FORMAT_IBD_FILE
from ibd2sql.innodb_page.table import TABLE
# 日志系统是必选参数...
class LOG():
    	def info(self,*args):
            	pass

log = LOG()
from ibd2sql.ibd2sql import FORMAT_IBD_FILE
filename = '/data/mysql_5744/mysqldata/db1/t1.ibd' # 会自动识别同名frm文件
fobj = FORMAT_IBD_FILE([filename],None,None,log)[0]

table = TABLE(fobj['sdi'])
print(table.get_ddl())
```



## 获取SQL

```python
import argparse
from ibd2sql.ibd2sql import FORMAT_IBD_FILE
from ibd2sql.ibd2sql import IBD2SQL_SINGLE
from ibd2sql.innodb_page.table import TABLE
# 日志系统是必选参数...
class LOG():
    	def info(self,*args):
            	pass

log = LOG()
# 初始化一些必要参数(貌似有点多...)
parser = argparse.ArgumentParser()
parser.SQL = 'SQL'
parser.LIMIT = 17592186044416
parser.OUTPUT_FILESIZE = 17592186044416
parser.FORCE = False
parser.DELETED = False  # 改为True,即获取被删除的数据
parser.PARALLEL = 1
parser.REPLACE = False
parser.COMPLETE_INSERT = False
parser.MULTI_VALUE = False

filename = '/data/mysql_8037/mysqldata/db1/t1.ibd'
fobj = FORMAT_IBD_FILE([filename],None,None,log)[0]
table = TABLE(fobj['sdi'])
#print(table.get_ddl())

# 输出SQL
IBD2SQL_SINGLE(table,fobj,{},'',log,parser,None)
```





