#!/usr/bin/env python3
#write by ddcw @https://github.com/ddcw/ibd2sql

from ibd2sql import __version__
from ibd2sql.ibd2sql import ibd2sql
import argparse
import sys,os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'ibd2sql/')))

_help = """
--limit 限制行数, 返回指定的行数就退出, 默认-1 表示无限制
--where1  根据字段匹配 比如 --where1="id>1 and id < 10"
--where2  限制TRX范围, 比如 --where2=2,10  #即trx在2(含)到10(含)的事务修改的数据才会输出
--where3  限制rollptr的. 同trx
--force   是否跳过报错的
--set     将set/enum(default) 的int转换为实际表示的字符串. (默认使用逗号隔开)
--ddl     输出信息包含DDL
--deleted 仅输出biao'ji
--debug   调试, 输出的信息较多
--parallel 设置并发数量(默认4)
--debug-filename 调试的输出信息文件, 默认stdout
--multivalue  每页数据使用一个insert
--replace 使用replcae into 替换insert (和multialue冲突)
--replace-table 替换表名(含DDL)
--replcae-schema 替换数据库名
--sdi-table 指定使用该表的sdi作为元数据信息(分区表要)
--sdi-file  指定sdi文件(json)作为元数据信息(可以使用ibd2sdi生成相关信息)

--page-min  设置起始页 (方便调试)
--page-max   设置停止页 
--page-count 限制解析的页数量(方便调试)
--page-skip  跳过的page数量 也是方便调试的

"""

stout = """
输出格式说明:
int等输出为无引号字符串
binary输出为base64
其它均输出为字符串
"""

def _argparse():
	parser = argparse.ArgumentParser(add_help=True, description='解析mysql8.0的ibd文件 https://github.com/ddcw/ibd2sql')
	parser.add_argument('--version', '-v', '-V', action='store_true', dest="VERSION", default=False,  help='show version')
	parser.add_argument('--ddl', '-d', action='store_true', dest="DDL", default=False,  help='print ddl')
	parser.add_argument('--sql', action='store_true', dest="SQL", default=False,  help='print data by sql')
	parser.add_argument('--delete', action='store_true', dest="DELETED", default=False,  help='print data only for flag of deleted')
	parser.add_argument('--complete-insert', action='store_true', dest="COMPLETE_INSERT", default=False,  help='use complete insert statements for sql')
	parser.add_argument('--force','-f', action='store_true', dest="FORCE", default=False,  help='force pasrser file when Error Page')
	parser.add_argument('--set', action='store_true', dest="SET", default=False,  help='set/enum to fill in actual data instead of strings')
	parser.add_argument('--multi-value', action='store_true', dest="MULTI_VALUE", default=False,  help='single sql if data belong to one page')
	parser.add_argument('--replace', action='store_true', dest="REPLACE", default=False,  help='"REPLACE INTO" replace to "INSERT INTO" (default)')
	parser.add_argument('--table', dest="TABLE_NAME", help='replace table name except ddl')
	parser.add_argument('--schema', dest="SCHEMA_NAME", help='replace table name except ddl')
	parser.add_argument('--sdi-table', dest="SDI_TABLE", help='read SDI PAGE from this file(ibd)(partition table)')

	#where条件
	parser.add_argument('--where-trx', dest="WHERE_TRX", help='default (0,281474976710656)')
	parser.add_argument('--where-rollptr', dest="WHERE_ROLLPTR", help='default (0,72057594037927936)')
	parser.add_argument('--where', dest="WHERE", help='filter data(TODO)')
	parser.add_argument('--limit', dest="LIMIT", type=int, help='limit rows')

	#DEBUG相关, 方便调试
	parser.add_argument('--debug', '-D', action='store_true', dest="DEBUG", default=False,  help="will DEBUG (it's too big)")
	parser.add_argument('--debug-file', dest="DEBUG_FILE", help='default sys.stdout if DEBUG')
	parser.add_argument('--page-min', action='store', type=int, dest="PAGE_MIN", default=0, help='if PAGE NO less than it, will break')
	parser.add_argument('--page-max', action='store', type=int, dest="PAGE_MAX", default=4294967296, help='if PAGE NO great than it, will break')
	parser.add_argument('--page-start', action='store', type=int, dest="PAGE_START", help='INDEX PAGE START NO')
	parser.add_argument('--page-count', action='store', type=int, dest="PAGE_COUNT", help='page count NO')
	parser.add_argument('--page-skip', action='store', type=int, dest="PAGE_SKIP", help='skip some pages when start parse index page')

	#TODO
	parser.add_argument('--parallel','-p', action='store', dest="PARALLEL", default=4,  help='parse to data/sql with N threads.(default 4) TODO')

	#IBD FILE
	parser.add_argument(dest='FILENAME', help='ibd filename', nargs='?')

	if parser.parse_args().VERSION:
		#print("VERSION: v1.0 only for MySQL 8.0")
		print(f"ibd2sql VERSION: v{__version__} only for MySQL 8.0")
		sys.exit(0)

	return parser.parse_args()

if __name__ == '__main__':
	parser = _argparse()
	#对部分默认值做处理
	if not parser.SQL:
		parser.DDL = True
	filename = parser.FILENAME
	if not os.path.exists(filename):
		#raise f'no file {filename}'
		sys.stderr.write(f"\nno file {filename}\n\n")
		sys.exit(1)
	#不管debug file了
	if parser.DEBUG_FILE is not None and os.path.exists(filename):
		pass

	#初始化一个ibd2sql对象, 然后设置它的属性
	ddcw = ibd2sql()
	ddcw.FILENAME = parser.FILENAME
	if parser.DEBUG:
		ddcw.DEBUG = True
	if parser.SDI_TABLE:
		ddcw.IS_PARTITION = True

	ddcw.COMPLETE_SQL = True if parser.COMPLETE_INSERT else False

	#基础过滤信息
	ddcw.REPLACE = True if parser.REPLACE else False
	if parser.PAGE_COUNT:
		ddcw.PAGE_COUNT = parser.PAGE_COUNT
	if parser.PAGE_MIN:
		ddcw.PAGE_MIN = parser.PAGE_MIN
	if parser.PAGE_MAX:
		ddcw.PAGE_MAX = parser.PAGE_MAX
	if parser.PAGE_START:
		ddcw.PAGE_START = parser.PAGE_START
	if parser.PAGE_SKIP:
		ddcw.PAGE_SKIP = parser.PAGE_SKIP
	if parser.FORCE:
		ddcw.FORCE = parser.FORCE

	#替换分区表的SDI信息
	if parser.SDI_TABLE:
		ddcw.IS_PARTITION = True
		aa = ibd2sql()
		aa.FILENAME = parser.SDI_TABLE
		aa.init()
		ddcw.table = aa.table
		ddcw._init_table_name()
		aa.close()


	if parser.DEBUG_FILE is not None:
		f = open(parser.DEBUG_FILE,'a')
		ddcw.DEBUG = True
		ddcw.DEBUG_FD = f

	if parser.DELETED:
		ddcw.DELETE = True

	if parser.SET:
		ddcw.SET = True
	
	if parser.MULTI_VALUE:
		ddcw.MULTIVALUE = True

	#条件
	if parser.WHERE_TRX:
		_a = [ int(x) for x in parser.WHERE_TRX.split(',')]
		ddcw.WHERE2 = _a[:2]

	if parser.WHERE_ROLLPTR:
		_a = [ int(x) for x in parser.WHERE_ROLLPTR.split(',')]
		ddcw.WHERE3 = _a[:2]


	#初始化, 解析表
	ddcw.init()

	if parser.TABLE_NAME:
		ddcw.replace_name(parser.TABLE_NAME)

	if parser.SCHEMA_NAME:
		ddcw.replace_schema(parser.SCHEMA_NAME)

	if parser.DDL:
		print(ddcw.get_ddl())

	
	ddcw.MULTIVALUE = True if parser.MULTI_VALUE and not parser.REPLACE else False
	ddcw.REPLACE = True if parser.REPLACE else False
	ddcw.LIMIT = parser.LIMIT if parser.LIMIT else -1
	if parser.SQL and ddcw.table.row_format in ['DYNAMIC','COMPACT']:
		ddcw.get_sql()
	elif not ddcw.table.row_format in ['DYNAMIC','COMPACT']:
		sys.stderr.write(f"\nNot support row format. {ddcw.table.row_format}\n\n")


	#记得关闭相关FD
	ddcw.close()
	if parser.DEBUG_FILE is not None:
		try:
			f.close()
		except:
			pass
