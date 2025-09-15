#!/usr/bin/env python3
# writen by ddcw  @https://github.com/ddcw/ibd2sql
# ibd2sql: parse ibd file to sql

from ibd2sql.ibd2sql import FORMAT_IBD_FILE
from ibd2sql.ibd2sql import IBD2SQL_SINGLE
from ibd2sql.ibd2sql import IBD2SQL_MULTI
from ibd2sql.ibd2sql import FIND_LEAF_PAGE_FROM_ROOT
from ibd2sql.innodb_page.lob import FIRST_BLOB
from ibd2sql.utils.crc32c import REPACK_PAGE
from ibd2sql.utils.crc32c import CHECK_PAGE
from ibd2sql.web import RUN_IBD2SQL_WEB
import datetime
import argparse
import time
import json
import glob
import sys
import os

def print_error_and_exit(msg,exit_code=1):
	msg += "\n"
	sys.stdout.write(msg)
	sys.exit(exit_code)

def MODIFY_PAGE_INPLACE(filename,pageno,pagesize,offset,new_value):
	with open(filename,'r+b') as f:
		f.seek(pageno*pagesize,0)
		data = f.read(pagesize)
		newdata = data[:offset] + new_value + data[offset+len(new_value):]
		data = REPACK_PAGE(newdata)
		f.seek(pageno*pagesize,0)
		f.write(data)
	return True

def _argparse():
	parser = argparse.ArgumentParser(add_help=False,description="parse mysql ibd file. https://github.com/ddcw/ibd2sql")
	parser.add_argument(
		"--help", "-h", "-H",
		action="store_true", 
		dest="HELP", 
		default=False,
		help="show help"
	)
	parser.add_argument(
		"--version", "-v", "-V",
		action="store_true", 
		dest="VERSION", 
		default=False,  
		help="show version"
	)
	parser.add_argument(
		"--ddl", 
		nargs='?',
		choices=['history','disable-keys','keys-after'],
		const=True,
		dest="DDL", 
		default=False,  
		help="print ddl"
	)
#	parser.add_argument(
#		"--disable-extra-pages", 
#		action="store_true", 
#		dest="DISABLE_EXTRA_PAGES",  # 禁用溢出页
#		default=False,  
#		help="disable extra pages(overflow page)"
#	)
	parser.add_argument(
		"--sql", 
		nargs='?',
		choices=['sql','data'],
		const=True,
		dest="SQL", 
		default=False, 
		help="print data(default sql)"
	)
#	parser.add_argument(
#		"--fields-terminated",
#		dest="FIELD_TERMINATED", 
#		help="fields terminated by"
#	)
#	parser.add_argument(
#		"--fields-enclosed",
#		dest="FIELD_ENCLOSED", 
#		help="fields enclosed by"
#	)
#	parser.add_argument(
#		"--lines-terminated",
#		dest="LINES_TERMINATED", 
#		help="lines terminated by"
#	)
	parser.add_argument(
		"--delete", 
		nargs='?',
		choices=['only','with'],
		const=True, # only
		dest="DELETED", 
		default=False, 
		help="deleted flag(default only)"
	)
	parser.add_argument(
		"--complete-insert", 
		action="store_true", 
		dest="COMPLETE_INSERT", 
		default=False, 
		help="sql with column name"
	)
	parser.add_argument(
		"--multi-value", 
		action="store_true", 
		dest="MULTI_VALUE", 
		default=False, 
		help="single sql if data belong to the page"
	)
	parser.add_argument(
		"--force","-f", 
		action="store_true", 
		dest="FORCE", 
		default=False,  
		help="force pasrse all cluster index"
	)
	parser.add_argument(
		"--replace", 
		action="store_true", 
		dest="REPLACE", # replace会覆盖掉multi
		default=False, 
		help='"REPLACE INTO" replace to "INSERT INTO"'
	)
	parser.add_argument(
		"--table",
		dest="TABLE_NAME", 
		help="replace table name"
	)
	parser.add_argument(
		"--schema", 
		dest="SCHEMA_NAME", 
		help="replace schema name"
	)
	parser.add_argument(
		'--sdi-table', # for compatibility
		'--sdi',
		'--sdi-file',
		dest="SDI_FILE", 
		help='read SDI from this file(ibd/sdi/frm)'
	)
#	parser.add_argument(
#		"--filter-table", 
#		dest="FILTER_TABLE", 
#		help="filter table name if general tablespace or multi-ibd-file"
#	)
#	parser.add_argument(
#		"--filter-schema", 
#		dest="FILTER_SCHEMA", 
#		help="filter schema name if general tablespace or multi-ibd-file"
#	)
	parser.add_argument(
		"--limit", 
		dest="LIMIT", 
		type=int, 
		default=17592186044416,
		help="limit rows"
	)
	parser.add_argument(
		"--keyring-file", 
		action="store", 
		dest="KEYRING_FILE", 
		help="keyring filename"
	)
#	parser.add_argument(
#		"--page-start", 
#		action="store", 
#		type=int, 
#		dest="PAGE_START", 
#		help="INDEX PAGE START NO(with)"
#	)
#	parser.add_argument(
#		"--page-count", 
#		action="store", 
#		type=int, 
#		dest="PAGE_COUNT", 
#		help="will be parse pages"
#	)
	parser.add_argument(
		"--output",#"-o","-O",
		nargs='?',
                const=True,
		dest="OUTPUT_FILEDIR",
		help="output dir(auto create), stdout if Not" # {schema}.{table}{_partition_}{pid}_{rotateno}{_gen}.sql
	)
	parser.add_argument(
		"--output-filesize",
		action="store",
		type=int,
		dest="OUTPUT_FILESIZE",
		default=17592186044416,
		help="rotate output filename if size(bytes) greate to this"
	)
	parser.add_argument(
		"--print-sdi", 
		action="store_true", 
		dest="PRINT_SDI", 
		help="only print sdi info(json)"
	)
	parser.add_argument(
		"--count", 
		action="store_true", 
		dest="SUPER_FAST_COUNT", 
		help="print total rows of cluster index(super_fast)"
	)
#	parser.add_argument(
#		"--check", 
#		action="store_true", 
#		dest="CHECK", 
#		help="check and print bad-block page-no if bad"
#	)
	parser.add_argument(
		"--checksum", 
		action="store_true", 
		dest="CHECKSUM", 
		help="like: CHECKSUM TABLE tablename"
	)
	parser.add_argument(
		"--web", 
		action="store_true", 
		dest="WEB", 
		help="web console to browse data in ibd file"
	)
	parser.add_argument(
		"--lctn", 
		nargs='?',
		const=True,
		type=int,
		dest="LCTN", 
		choices=[0,1,2],
		help="show/set lower_case_table_name in mysql.ibd "
	)
	parser.add_argument(
		"--parallel", 
		type=int,
		dest="PARALLEL", 
		default=1,
		help="run multi-process to parse ibd file"
	)

	parser.add_argument(
		"--log",
		nargs='?',
		const=True,
		dest="LOG_FILE", 
		help="log file"
	)


	# fields-terminated-by/fields-enclosed-by/lines-terminated-by for --sql=data
	# table/schema: 	filter table/schema
	# disable-extra-pages: 	disable extra pages
	# leafno/rootno: 	pk leaf/root pageno
	# trim_trailing_space: 	trim trailing space for CHAR
	# hex: 			show fields data in hex
	# foreign-keys-after:   alter table add foreign-keys after insert
	# disable-foreign-keys: ddl without foreign-keys
	# host:			listen host for WEB, default '0.0.0.0'
	# port:			listen port for WEB, default '8080'
	parser.add_argument(
		"--set",
		dest="SET_OPTIONS", 
		action='append',
		help="set some options:fields-terminated-by,fields-enclosed-by,lines-terminated-by,schema(filter),table,disable-extra-pages,leafno,rootno,trim_trailing_space(only for char),hex,foreign-keys-after,disable-foreign-keys,host,port\n example:--set='rootno=4;hex'"
	)
#	parser.add_argument(
#		"--verbose",'-v'
#		action='count',
#		dest="LOG_LEVEL", 
#		help="log level"
#	)
	

#	parser.add_argument(
#		"--raed-pages",
#		type=int,
#		dest="READ_PAGES",
#		default=100,
#		help="pages per read(only for --force), default 100 pages"
#	)


	#parser.add_argument(dest='FILENAME', help='ibd filename or dirname with ibd file', nargs='?')
	parser.add_argument(dest='FILENAME', help='ibd filename or dirname with ibd file', nargs='*')

	if parser.parse_args().VERSION:
		print('ibd2sql v2.0')
		sys.exit(0)

	if parser.parse_args().HELP or parser.parse_args().FILENAME == []:
		parser.print_help()
		# USAGE
		print('\nNew issue if have questions  : https://github.com/ddcw/ibd2sql/issues\n')
		#print('Or send question to my email : yangguisen1996@gmail.com\n')
		sys.exit(0)

	parser = parser.parse_args()
	# conflict check
	
	if parser.MULTI_VALUE and parser.REPLACE:
		print_error_and_exit('conflict between --replace and --multi-value')

	return parser


from ibd2sql.innodb_page.sdi import SDI
from ibd2sql.innodb_page.page import PAGE_READER
from ibd2sql.innodb_page.fsp import FSP
from ibd2sql.innodb_page.fsp import GET_FSP_STATUS_FROM_FLAGS
from ibd2sql.innodb_page.inode import INODE
from ibd2sql.innodb_page.index import INDEX
from ibd2sql.innodb_page.table import TABLE
import struct
def t_ddl(filename,DDL_HISTORY,DISABLE_KEYS):
	pg = PAGE_READER(page_size=16384,filename=filename)
	#pg = PAGE_READER(page_size=8192,filename=filename)
	aa = struct.unpack('>L',pg.read()[54:58])[0]
	fsp_flags = GET_FSP_STATUS_FROM_FLAGS(aa)
	pg = PAGE_READER(page_size=fsp_flags['physical_size'],filename=filename)
	fsp = FSP(pg.read())
	inode = INODE(pg)
	sdino = inode.seg[0][0]['FSEG_FRAG_ARR'][0] if inode.seg[0][1]['FSEG_FRAG_ARR'][0] == 4294967295 else inode.seg[0][1]['FSEG_FRAG_ARR'][0]
	#print(json.dumps(inode.seg))
	#sys.exit(1)
	bb = SDI(sdino,pg,'COMPRESSED' if fsp_flags['logical_size'] != fsp_flags['physical_size'] else '1')
	#bb = SDI(121,aa,'1')
	#print(bb.get_sdi())
	sdi = json.dumps([bb.get_sdi()[1]] if fsp_flags['compressed'] else [bb.get_sdi()[0]])
	#print(sdi)
	#sys.exit(1)
	table = TABLE(sdi)
	if DDL_HISTORY:
		print(table.get_ddl_history(DDL_HISTORY,DISABLE_KEYS))
	else:
		print(table.get_ddl(DDL_HISTORY,DISABLE_KEYS))
	if DISABLE_KEYS:
		print(table.get_ddl_key())
	idx = INDEX()
	idx.init_index(table=table,idxid=0,pg=pg,page_type='PK_LEAF')
	#print(json.dumps(idx.read_all_rows()))
	idx.init_data(pg.read(4))
	print(idx.get_data())
	#print(';\n'.join(idx.get_sql()),';')
	sys.exit(1)
	pageid = 7
	while pageid < 4294967295:
		data = pg.read(pageid)
		pageid = struct.unpack('>L',data[12:16])[0]
		idx.init_data(data)
		print(';\n'.join(idx.get_sql()),';')
	#print(idx.read_all_rows())

class LOG(object):
	def __init__(self,filename=None):
		self.filename = filename
		if self.filename is not None:
			if self.filename is True:
				self.f = sys.stderr
			else:
				self.f = open(self.filename,'a')
		else:
			self._write = self._write_nothing

	def _write_nothing(self,msg):
		pass

	def _write(self,msg):
		self.f.write(msg)

	def info(self,*args):
		msg = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] {' '.join([ str(x) for x in args ])}\n"
		return self._write(msg)

	def error(self,*args):
		msg = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] {' '.join([ str(x) for x in args ])}\n"
		return self._write(msg)

	def warning(self,*args):
		msg = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [WARNING] {' '.join([ str(x) for x in args ])}\n"
		return self._write(msg)

	def __close__(self):
		if self.filename is not None:
			self.f.close()

if __name__ == '__main__':
	parser = _argparse()
	opt = {}
	# --set="a=1,b=2" --set 'c=3;d=4' --set 'a=5'
	if parser.SET_OPTIONS is not None:
		for x in parser.SET_OPTIONS:
			for y in x.split(';'):
				for z in y.split(','):
					kv = z.split('=')
					if len(kv) == 2:
						opt[kv[0]] = kv[1]
					elif len(kv) == 1 and z != '':
						opt[kv[0]] = True
	disable_foreign_key = True if 'disable-foreign-keys' in opt or 'foreign-keys-after' in opt else False
	foreign_keys_after = True if 'foreign-keys-after' in opt else False
	# init log
	log = LOG(parser.LOG_FILE)
	log.info('SET:',opt)
	log.info('INIT FILENAME')

	# for fragmented page
	FRAGMENT_PAGE = False
	FRAGMENT_FILENAME = ''
	FRAGMENT_FILENAME_PRE = ''
	if os.path.isdir(parser.FILENAME[0]):
		if os.path.join(parser.FILENAME[0],'FIL_PAGE_INDEX') and os.path.join(parser.FILENAME[0],'FIL_PAGE_TYPE_BLOB'):
			log.info('for fragmented page')
			if 'indexid' not in opt:
				print_error_and_exit('--set indexid=xx is must when fragementd page')
			filename = os.path.join(parser.FILENAME[0],'FIL_PAGE_INDEX',opt['indexid'].zfill(16)) + ".page"
			if not os.path.exists(filename):
				print_error_and_exit(f"indexid={opt['indexid']} file {filename} not exists")
			if parser.SDI_FILE is None:
				print_error_and_exit(f"--sdi xx is must when fragementd page")
			if not os.path.exists(parser.SDI_FILE):
				print_error_and_exit(f"sdifile {parser.SDI_FILE} is not exists")
			FRAGMENT_FILENAME = filename
			FRAGMENT_PAGE = True
			opt['leafno'] = 0
			opt['rootno'] = 0
			parser.FORCE = True
			FRAGMENT_FILENAME_PRE = os.path.join(parser.FILENAME[0],'FIL_PAGE_TYPE_BLOB')
	# init filename
	filename_list = [] if not FRAGMENT_PAGE else [FRAGMENT_FILENAME]
	for x in parser.FILENAME:
		for filename in glob.glob(x):
			if os.path.isfile(filename):
				filename_list.append(filename)
			elif os.path.isdir(filename):
				for n in os.listdir(filename):
					nfilename = os.path.join(filename,n)
					if os.path.isfile(nfilename):
						filename_list.append(nfilename)
			else:
				log.warning('file',filename,'not exists. [skip it]')
	if len(filename_list) == 0:
		print(*parser.FILENAME,'not exists')
		sys.exit(1)
	if len(filename_list) > 1 and parser.SDI_FILE is not None:
		print_error_and_exit(f'there are multiple files({len(filename_list)}), but with --sdi-file {parser.SDI_FILE}',2)


	# init data file/sdi(json)/keyringfile(if)
	_file_list = FORMAT_IBD_FILE(filename_list,parser.SDI_FILE,parser.KEYRING_FILE,log)
	# filter table/schema
	file_list = []
	for file_base in _file_list:
		if 'table' in opt and opt['table'] != file_base['sdi']['dd_object']['name']:
			log.info(f"table name: {opt['table']} != {file_base['sdi']['dd_object']['name']}, skip it")
			continue
		if 'schema' in opt and opt['schema'] != file_base['sdi']['dd_object']['tablespace_ref']:
			log.info(f"table name: {opt['schema']} != {file_base['sdi']['dd_object']['tablespace_ref'].name}, skip it")
			continue
		file_list.append(file_base)
	if len(file_list) == 0:
		print_error_and_exit('no tables matched',4)
	if len(file_list) > 1 and parser.TABLE_NAME is not None:
		print_error_and_exit(f'there are multiple tables({len(file_list)}), but with --table',3)

	# web
	if parser.WEB:
		RUN_IBD2SQL_WEB(file_list,opt,log)
	elif parser.PRINT_SDI:
		sdi = []
		for x in file_list:
			sdi.append(x['sdi'])
		print(json.dumps(sdi))
	elif parser.LCTN or parser.LCTN == 0: # show/set lower_case_table_name
		log.info('modify lower_case_table_name')
		if len(filename_list) == 1 and len(file_list) > 60: # shared tablespace
			log.info('get table(dd_properties) info...',)
			table = None
			file_base = None
			rootno = 0
			for i in range(len(file_list)):
				file_base = file_list[i]
				if file_base['sdi']['dd_object']['name'] == 'dd_properties':
					table = TABLE(file_base['sdi'])
					rootno = int(file_base['sdi']['dd_object']['indexes'][0]['root'])
			if table is None:
				print_error_and_exit(' no dd_properties')
			pg = PAGE_READER(page_size=file_base['pagesize'],filename=file_base['filename'],encryption=file_base['encryption'],key=file_base['key'],iv=file_base['iv'])
			inode = INODE(pg)
			#rootno = inode.seg[0][0]['FSEG_FRAG_ARR'][0] if file_base['fsp_flags']['SDI'] == 0 else inode.seg[1][0]['FSEG_FRAG_ARR'][0]
			leafno = FIND_LEAF_PAGE_FROM_ROOT(pg,rootno,table)
			pageid = leafno
			log.info('leaf no',leafno)
			data = pg.read(pageid)
			offset = 99
			offset += struct.unpack('>h',data[97:99])[0]
			log.info(f'first row: pageid:{pageid}  offset:{offset}')
			LCTN_PAGENO = 0
			LCTN_OFFSET = 0
			current_lctn = -1
			if data[offset-2-5-1:offset-5-1] == b'\x14\xc0': # 
				offset += 6 + 13
				SPACE_ID,PAGENO,BLOB_HEADER,REAL_SIZE = struct.unpack('>3LQ',data[offset:offset+20])
				log.info(f'SPACE_ID:{SPACE_ID} PAGENO:{PAGENO} BLOB_HEADER:{BLOB_HEADER} REAL_SIZE:{REAL_SIZE}')
				data = pg.read(PAGENO)
				entry = data[96:96+60]
				while True:
					if len(entry) < 12:
						break
					LCTN_PAGENO,datalen,lobversion = struct.unpack('>3L',entry[-12:])
					datalen = datalen>>16
					if LCTN_PAGENO == 0:
						break
					elif LCTN_PAGENO == PAGENO:
						rdata = data
					else:
						rdata = pg.read(LCTN_PAGENO)
					LCTN_OFFSET = rdata.find(b';LCTN=')
					if LCTN_OFFSET > 0:
						LCTN_OFFSET += 6
						current_lctn = rdata[LCTN_OFFSET:][:1].decode()
						break
					next_entry_pageno,next_entry_offset = struct.unpack('>LH',entry[6:12])
					if next_entry_pageno >0 and next_entry_pageno < 4294967295:
						entry = pg.read(next_entry_pageno)[next_entry_offset:next_entry_offset+60]
					else:
						break

				print('current lower_case_table_name =',current_lctn)
				print('pageno:',LCTN_PAGENO,'offset:',LCTN_OFFSET)
				if type(parser.LCTN) is int and parser.LCTN != int(current_lctn) :
					log.info('will set lower_case_table_name =',parser.LCTN)
					# danger! start after countdown ends
					if MODIFY_PAGE_INPLACE(filename,LCTN_PAGENO,file_base['pagesize'],LCTN_OFFSET,str(parser.LCTN).encode()):
						print('set lower_case_table_name =',parser.LCTN,'success')
					else:
						print('set lower_case_table_name =',parser.LCTN,'faild')
			else:
				print_error_and_exit('cant not support lctn')
		else:
			print(f'there have {len(filename_list)} files, but have {len(file_list)} tables. not mysql.ibd')
	elif parser.SUPER_FAST_COUNT: # super_fast_count
		for file_base in file_list:
			time_1 = time.time()
			table = TABLE(file_base['sdi'])
			count_1 = 0
			count_2 = 0 # with deleted
			pg = PAGE_READER(page_size=file_base['pagesize'],filename=file_base['filename'],encryption=file_base['encryption'],key=file_base['key'],iv=file_base['iv'])
			inode = INODE(pg)
			if 'rootno' in opt:
				rootno = opt['rootno']
			elif file_base['fsp_flags']['SHARED']:
				rootno = int(file_base['sdi']['dd_object']['indexes'][0]['root'])
			else:
				rootno = inode.seg[0][0]['FSEG_FRAG_ARR'][0] if file_base['fsp_flags']['SDI'] == 0 else inode.seg[1][0]['FSEG_FRAG_ARR'][0]
			leafno = FIND_LEAF_PAGE_FROM_ROOT(pg,rootno,table)
			pageid = leafno
			log.info(file_base['filename'],file_base['sdi']['dd_object']['name'],f'rootno:{rootno} leafno:{leafno}')
			while pageid < 4294967295:
				data = pg.read(pageid)
				if data == b'':
					break
				pageid = struct.unpack('>L',data[12:16])[0]
				count_1 += struct.unpack('>H',data[54:56])[0]
				count_2 += (struct.unpack('>H',data[42:44])[0] & 32767) - 2
			time_2 = time.time()
			print(f"{file_base['filename']}\t{file_base['sdi']['dd_object']['name']}\tROWS:{count_1}\tROWS(with deleted):{count_2}\tTIME:{round((time_2-time_1),2)} seconds\tFILE SIZE:{round(os.path.getsize(file_base['filename'])/1024/1024,2)} MB")
	elif parser.CHECKSUM: # only checksum
		print('CHECKSUM TODO')
	else: # ddl/sql
		filename_pre = ''
		if parser.OUTPUT_FILEDIR:
			if parser.OUTPUT_FILEDIR is True:
				filename_pre = f"ibd2sql_auto_dir_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
			else:
				filename_pre = parser.OUTPUT_FILEDIR
			print('output dir:',filename_pre)
		if filename_pre != '':
			os.makedirs(filename_pre,exist_ok=True)
			log.info('output dir:',filename_pre)
		if parser.DELETED:
			parser.SQL = True
		if not parser.SQL and not parser.DDL:
			parser.DDL = True
		for x in file_list:
			table = TABLE(x['sdi'])
			if parser.SCHEMA_NAME is not None:
				table.schema = parser.SCHEMA_NAME
			if parser.TABLE_NAME is not None:
				table.name = parser.TABLE_NAME
			if filename_pre != '':
				ddl_filename = os.path.join(filename_pre,f'{table.schema}.{table.name}{x["partition_name"] if x["partition_name"] is not None else ""}_{os.getpid()}')+'_ddl.sql'
				f = open(ddl_filename,'a')
				print('DDL filename:',ddl_filename)
			else:
				f = sys.stdout
			if parser.DDL:
				ddl = ''
				if parser.DDL == 'history':
					ddl = table.get_ddl_history(True,False,disable_foreign_key)
				elif parser.DDL in ['disable-keys','keys-after']:
					ddl = table.get_ddl(False,True,disable_foreign_key)
				else:
					ddl = table.get_ddl(False,False,disable_foreign_key)
				f.write(ddl+"\n")

			# sql/data
			if parser.SQL:
				IBD2SQL_SINGLE(table,x,opt,filename_pre,log,parser,FRAGMENT_FILENAME_PRE)
				#if parser.PARALLEL is not None and parser.PARALLEL > 1: # multi process
				#	IBD2SQL_MULTI(table,x,opt,filename_pre,log,parser)
				#else: # single
				#	IBD2SQL_SINGLE(table,x,opt,filename_pre,log,parser)

			if parser.DDL == 'keys-after':
				f.write(table.get_ddl_key()+"\n")
			if foreign_keys_after:
				f.write(table.get_ddl_reference()+"\n")
			if filename_pre != '':
				f.close()
