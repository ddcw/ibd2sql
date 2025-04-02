#!/usr/bin/env python3
#write by ddcw @https://github.com/ddcw/ibd2sql

from ibd2sql import __version__
from ibd2sql.ibd2sql import ibd2sql
from ibd2sql import AES
import argparse
import sys
import os
import struct
from ibd2sql import CRC32C
from ibd2sql import frm2sdi
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'ibd2sql/')))

def _argparse():
	parser = argparse.ArgumentParser(add_help=False, description='解析mysql 5.7/8.0的ibd文件 https://github.com/ddcw/ibd2sql')
	parser.add_argument('--help', '-h', action='store_true', dest="HELP", default=False,  help='show help')
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
	#parser.add_argument('--where', dest="WHERE", help='filter data(TODO)')
	parser.add_argument('--limit', dest="LIMIT", type=int, help='limit rows')

	#DEBUG相关, 方便调试
	parser.add_argument('--debug', '-D', action='store_true', dest="DEBUG", default=False,  help="will DEBUG (it's too big)")
	parser.add_argument('--debug-file', dest="DEBUG_FILE", help='default sys.stdout if DEBUG')
	parser.add_argument('--page-min', action='store', type=int, dest="PAGE_MIN", default=0, help='if PAGE NO less than it, will break')
	parser.add_argument('--page-max', action='store', type=int, dest="PAGE_MAX", default=4294967296, help='if PAGE NO great than it, will break')
	parser.add_argument('--page-start', action='store', type=int, dest="PAGE_START", help='INDEX PAGE START NO')
	parser.add_argument('--page-count', action='store', type=int, dest="PAGE_COUNT", help='page count NO')
	parser.add_argument('--page-skip', action='store', type=int, dest="PAGE_SKIP", help='skip some pages when start parse index page')

	# for mysql 5.7
	parser.add_argument('--mysql5', action='store_true', dest="MYSQL5", default=False,  help='for mysql5.7 flag')

	#TODO
	#parser.add_argument('--parallel','-p', action='store', dest="PARALLEL", default=4,  help='parse to data/sql with N threads.(default 4) TODO')

	# keyring file
	parser.add_argument('--keyring-file','-k', action='store', dest="KEYRING_FILE", default='', help='keyring filename')

	#IBD FILE
	parser.add_argument(dest='FILENAME', help='ibd filename', nargs='?')

	if parser.parse_args().VERSION:
		#print("VERSION: v1.0 only for MySQL 8.0")
		print(f"ibd2sql VERSION: v{__version__} for MySQL 5.7 or 8.0")
		sys.exit(0)

	if parser.parse_args().HELP:
		parser.print_help()
		print("Example:")
		print("ibd2sql /data/db1/xxx.ibd --ddl --sql")
		print("ibd2sql /data/db1/xxx.ibd --delete --sql")
		print("ibd2sql /data/db1/xxx#p#p1.ibd --sdi-table /data/db1/xxx#p#p0.ibd --sql")
		print("ibd2sql /mysql57/db1/xxx.ibd --sdi-table /mysql80/db1/xxx.ibd --sql --mysql5")
		print("")
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
	# 判断keyring file
	kd = {}
	if parser.KEYRING_FILE != '' and os.path.exists(parser.KEYRING_FILE):
		with open(parser.KEYRING_FILE,'rb') as f:
			kd = AES.read_keyring(f.read())
			if len(kd) == 0:
				sys.stderr.write(f"\nkeyring file {parser.KEYRING_FILE} is not correct\n\n")
				sys.exit(11)
	ddcw.MYSQL5 = parser.MYSQL5
	# 自动判断是否为mysql5环境
	if os.path.exists(filename[:-4]+'.frm'):
		AUTOFRM = True
		FRMFILENAME = filename[:-4]+'.frm'
		ddcw.MYSQL5 = True
	elif os.path.exists(filename.split('#')[0]+'.frm'): # 5.7的分区表
		AUTOFRM = True
		FRMFILENAME = filename.split('#')[0]+'.frm'
		ddcw.MYSQL5 = True
	else:
		AUTOFRM = False

	# 读ibd的fsp中的key和iv
	with open(filename,'rb') as f:
		fsp = f.read(16384)
		if len(fsp) != 16384:
			sys.stderr.write(f"\n ibd file {filename} is not correct\n\n")
			sys.exit(12)
		data = fsp[10390:10390+115]
		if data != b'\x00'*115 and len(kd) == 0:
			sys.stderr.write(f"\n ibd file {filename} is ENCRYPTED, please with --keyring-file='xxxxx'\n\n")
			sys.exit(14)
		if data != b'\x00'*115:
			ddcw.ENCRYPTED = True # 表示有加密
			master_id = struct.unpack('>L',data[3:7])[0]
			server_uuid = data[7+4:7+4+36].decode() if ddcw.MYSQL5 else data[7:7+36].decode()
			kid = 'INNODBKey'+'-'+server_uuid+'-'+str(master_id)
			if kid not in kd:
				sys.stderr.write(f"\n ibd'key not in keyring file({parser.KEYRING_FILE})\n\n")
				sys.exit(13)
			master_key = kd['INNODBKey'+'-'+server_uuid+'-'+str(master_id)]['key']
			key_info = AES.aes_ecb256_decrypt(master_key,data[43+4:43+4+32*2]) if ddcw.MYSQL5 else AES.aes_ecb256_decrypt(master_key,data[43:43+32*2])
			# 这个key_info可能不对, 所以我们计算下CRC32C
			_crc32_value = struct.unpack('>L',data[-4:])[0] if ddcw.MYSQL5 else struct.unpack('>L',data[-8:-4])[0]
			if _crc32_value != CRC32C.crc32c(key_info):
				sys.stderr.write(f"\n keyring file({parser.KEYRING_FILE}) 里面确实包含对应的key({kid}), 但TM不对啊. 估计是指定的新/旧的keyring文件了.\n\n")
				sys.exit(15)
			key = key_info[:32]
			iv = key_info[32:48]
			ddcw.KEY = key
			ddcw.IV = iv
			
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
	elif AUTOFRM:
		ddcw.IS_PARTITION = True
		from ibd2sql.innodb_page_sdi import *
		aa = frm2sdi.MYSQLFRM(FRMFILENAME).get_sdi_page()
		ddcw.table = sdi(aa,filename=filename).table
		ddcw._init_table_name()


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
