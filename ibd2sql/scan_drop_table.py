import datetime
import struct
import base64
import json
import zlib
import time
import sys
import os
import re
from ibd2sql.ibd2sql import IBDBASE
from ibd2sql.ibd2sql import FORMAT_IBD_FILE
from ibd2sql.innodb_page.table import TABLE
from ibd2sql.innodb_page.table import str2dict
from ibd2sql.innodb_page.index import INDEX
from ibd2sql.innodb_page.page import PAGE_READER
#from ibd2sql.meta2sdi import mysql2sdi
#from ibd2sql.meta2sdi import ibdata2sdi

from ibd2sql.frm.frm2sdi import COL_TYPE
from ibd2sql.frm.frm2sdi import MYSQLFRM
from ibd2sql.utils.crc32c import CHECK_PAGE
from ibd2sql.utils.check_table_old import CHECK_PAGE_OLD
from ibd2sql.ibd2sql import IBD2SQL_SINGLE

import ctypes
from multiprocessing import Process
from multiprocessing import Value
from multiprocessing import Lock


# 查找目录下某个名字结尾的文件
def GET_MATCHFILE_FROMDIR(filename,dirname):
	rdata = []
	for _name in os.listdir(dirname):
		name = os.path.join(dirname,_name)
		if name.endswith(filename):
			rdata.append(name)
	return rdata

# 恢复被drop的表的, truncate的不行,因为是update更新的元数据信息,找不到之前的indexid了.
# 但是可以扫描整个磁盘, 然后一个个index文件去尝试....


def IS_PAGE(data):
	return True if data[:4] == data[-8:-4] else False

def IS_INDEX(data):
	return True if data[24:26] == b'E\xbf' else False

def IS_FRM(data):
	return True if data[:10] == b'\xfe\x01\n\x0c\x03\x00\x00\x10\x01\x00' else False

def IS_SDI(data):
	return True if data[24:26] == b'E\xbd' else False

def IS_OFFPAGE(data):
	return True if data[24:26] in [b'\x00\x18',b'\x00\x17',b'\x00\x16',b'\x00\n'] else False


DATA_NOT_NULL = 256
DATA_UNSIGNED = 512
DATA_BINARY_TYPE = 1024
DATA_VIRTUAL = 8192
DATA_FTS_DOC_ID = 3
DATA_SYS_PRTYPE_MASK = 0xF
DATA_GIS_MBR = 2048
DATA_LONG_TRUE_VARCHAR = 4096
DATA_MYSQL_TYPE_MASK = 255

def GET_CHARSET_ID_FROM_PRTYPE(k):
	return (k>>16)&32767


def GET_SIZE_FROM_DEV(filename):
	import stat
	f_stat = os.stat(filename)
	file_size = 0
	status = True
	if stat.S_ISREG(f_stat.st_mode): # file
		file_size = f_stat.st_size
	elif stat.S_ISBLK(f_stat.st_mode):
		real_dev = ''
		try:
			real_dev = os.readlink(filename).split('/')[-1] # lv
		except:
			real_dev = os.path.basename(filename) # dev
		with open(f'/sys/class/block/{real_dev}/size') as f:
			sectors = int(f.read().strip())
		try:
			with open(f'/sys/class/block/{real_dev}/queue/hw_sector_size') as f:
				sector_size = int(f.read().strip())
		except:
			sector_size = 512
		file_size = sectors * sector_size
	else:
		status = False
	return status,file_size



__TABLE_IN_SYS_80 = """
create table SCHEMATA.TABLES(
  COLUMNS
  key INDEXES(INDEX_COLUMNS_USAGES)
  CHECK_CONSTRAINTS
  FOREIGNS_KEYS
)comment=TABLES
TABLE_PARTITIONS
"""

_SYS_COL_OPT = {
	'collation_id': 63,
	'column_type_utf8':'',
	'is_unsigned':False,
	'is_zerofill':False,
	'default_value_utf8_null':True,
	'elements':[],
	'datetime_precision':0,
	'datetime_precision_null':1,
	'options':'',
	'is_nullable':False,
	'generation_expression':'',
	'default_value_null':True,
	'default_value_utf8':'',
	'default_value_utf8_null':True,
	'srs_id_null':True,
	'update_option':'',
	'is_auto_increment':False,
	'comment':'',
}


def GET_ROWFORMAT_FROM_TABLE_FLAGS(flags):
	if not flags&1:
		return 'REDUNDANT'
	elif not (flags&32)>>5:
		return 'COMPACT'
	elif (flags&30)>>1:
		return 'COMPRESSED'
	else:
		return 'DYNAMIC'

def INT2BOOLEAN(k):
	return False if k == 0 else True

MAINTYPELIST = ['DATA_MISSING','DATA_VARCHAR','DATA_CHAR','DATA_FIXBINARY','DATA_BINARY','DATA_BLOB','DATA_INT','DATA_SYS_CHILD','DATA_SYS','DATA_FLOAT','DATA_DOUBLE','DATA_DECIMAL','DATA_VARMYSQL','DATA_MYSQL','DATA_GEOMETRY','DATA_POINT','DATA_VAR_POINT'] + [ 'DATA_UNKNOWN' ]*46 + ['DATA_MTYPE_MAX']

INDEXTYPE2INT = {
	'PRIMARY':1,
	'UNIQUE':2,
	'MULTIPLE':3,
	'FULLTEXT':4,
	'SPATIAL':5
}

def INDEX57TYPE2INT(k):
	if k&1:
		return 1
	elif k&2:
		return 2
	elif k&32:
		return 4
	elif k&64:
		return 5
	else:
		return 3

INDEXALGORITHM2INT = {
	'SE_SPECIFIC':1,
	'BTREE':2,
	'RTREE':3,
	'HASH':4,
	'FULLTEXT':5,
	'SPATIAL':3
}

UPDATERILE2INT = {
	'NO ACTION':1,
	'RESTRICT':2,
	'CASCADE':3,
	'SET NULL':4,
	'SET DEFAULT':5
}

COLUMNKEY2INT = {
	"":1,
	"PRI":2,
	"UNI":3,
	"MUL":4,
}

ROW_FORMAT2INT = {
        'DYNAMIC':2,
        'COMPRESSED':3,
        'REDUNDANT':4,
        'COMPACT':5
}

HIDDEN2INT = {
	'Visible':1,
	'SE':2,
	'SQL':3,
	'User':4
}

MYSQLTYPE2INNODBTYPE = {
	'MYSQL_TYPE_DECIMAL':0,
	'MYSQL_TYPE_TINY':2,
	'MYSQL_TYPE_SHORT':3,
	'MYSQL_TYPE_LONG':4,
	'MYSQL_TYPE_FLOAT':5,
	'MYSQL_TYPE_DOUBLE':6,
	'MYSQL_TYPE_NULL':7,
	'MYSQL_TYPE_TIMESTAMP':8,
	'MYSQL_TYPE_LONGLONG':9,
	'MYSQL_TYPE_INT24':10,
	'MYSQL_TYPE_DATE':15,
	'MYSQL_TYPE_TIME':20,
	'MYSQL_TYPE_DATETIME':19,
	'MYSQL_TYPE_YEAR':14,
	'MYSQL_TYPE_NEWDATE':15,
	'MYSQL_TYPE_VARCHAR':16,
	'MYSQL_TYPE_BIT':17,
	'MYSQL_TYPE_TIMESTAMP2':18,
	'MYSQL_TYPE_DATETIME2':19,
	'MYSQL_TYPE_TIME2':20,
	'MYSQL_TYPE_TYPED_ARRAY':0,
	'MYSQL_TYPE_INVALID':0,
	'MYSQL_TYPE_BOOL':2,
	'MYSQL_TYPE_JSON':31,
	'MYSQL_TYPE_NEWDECIMAL':21,
	'MYSQL_TYPE_ENUM':22,
	'MYSQL_TYPE_SET':23,
	'MYSQL_TYPE_TINY_BLOB':24,
	'MYSQL_TYPE_MEDIUM_BLOB':25,
	'MYSQL_TYPE_LONG_BLOB':26,
	'MYSQL_TYPE_BLOB':27,
	'MYSQL_TYPE_VAR_STRING':16,
	'MYSQL_TYPE_STRING':16,
	'MYSQL_TYPE_GEOMETRY':30,
}


SYS_TABLES = ['tables','indexes','index_column_usage','columns','foreign_keys','check_constraints','table_partitions','schemata','tablespaces','foreign_key_column_usage']
SYS_TABLES_UPDATE = {
	'tables':'se_private_id',
	'indexes':'se_private_data',
	'columns':'se_private_data',
	'indexes':'se_private_data',
	'table_partitions':'se_private_id',
}

def remove_quotes(s):
	if isinstance(s,str) and len(s) > 2:
		return s[1:-1] if (s[0] == "'" and s[-1] == "'") or (s[0] == '"' and s[-1] == '"') else s
	else:
		return s

# 从mysql.ibd中读取被标记为delete的表
def READ_META_FROM_MYSQLIBD(log,filename,parser,opt):
	ibdbase = IBDBASE(filename,log,{})
	file_base = {
		'filename':filename,
		'sdi':{},
		'encryption':ibdbase.ENCRYPTION,
		'key':ibdbase.key,
		'iv':ibdbase.iv,
		'pagesize':ibdbase.physical_size,
		'partition_name':None,
		'fsp_flags':ibdbase.fsp_flags,
	}
	pg = PAGE_READER(page_size=file_base['pagesize'],filename=file_base['filename'],encryption=file_base['encryption'],key=file_base['key'],iv=file_base['iv'])
	allsdi = FORMAT_IBD_FILE([filename],None,None,log)
	SYS_TABLE_OBJ = {}
	for x in allsdi:
		table_schema = x['sdi']['dd_object']['schema_ref']
		table_name = x['sdi']['dd_object']['name']
		if table_schema == 'mysql' and table_name in SYS_TABLES:
			indexid = str2dict(x['sdi']['dd_object']['indexes'][0]['se_private_data'])['id']
			bindexid = b'\x00\x00'+struct.pack('>Q',int(indexid))
			table = TABLE(x['sdi'])
			idx = INDEX()
			idx.init_index(table=table,idxid=0,pg=pg,page_type='PK_LEAF',POST_ANTELOPE=file_base['fsp_flags']['POST_ANTELOPE'])
			SYS_TABLE_OBJ[bindexid] = {'name':table_name,'obj':idx}
	pages = os.path.getsize(file_base['filename'])//file_base['pagesize']
	pg.pageid = -1
	dd = {}

	DD = {
		'tables':{},
		'columns':{},
		'indexes':{},
		'index_column_usage':{},
		'foreign_keys':{},
		'foreign_key_column_usage':{},
		'check_constraints':{},
		'table_partitions':{},
		'schemata':{},
		'tablespaces':{}
	}
	DDD = {
		'tables':'id',
		'columns':'table_id',
		'indexes':'table_id',
		'index_column_usage':'index_id',
		'foreign_keys':'table_id',
		'foreign_key_column_usage':'foreign_key_id',
		'check_constraints':'table_id',
		'table_partitions':'table_id',
		'schemata':'id',
		'tablespaces':'id',
	}
	for _ in range(pages):
		data = pg.read(_)
		log.info('READ PAGE:',_)
		if data[64:74] in SYS_TABLE_OBJ:
			idx = SYS_TABLE_OBJ[data[64:74]]['obj']
			name = SYS_TABLE_OBJ[data[64:74]]['name']
			idx.init_data(data)
			all_data = []
			if name == 'schemata':
				all_data = idx.get_all_rows(False)
			if 'deleted' in opt:
				if opt['deleted'] in ['except','with']:
					all_data += idx.get_all_rows(False)
				elif opt['deleted'] in ['only','with']:
					all_data += idx.get_all_rows(True)
			else:
				all_data += idx.get_all_rows(True) # only deleted data
			for x in all_data:
				if name in SYS_TABLES_UPDATE:
					if x['data'][SYS_TABLES_UPDATE[name]]['data'] == 'null':
						continue
				k = x['data'][DDD[name]]['data']
				tt = {}
				for column_name in x['data']:
					column_value = remove_quotes(x['data'][column_name]['data'])
					if column_value == 'null' or column_value == "''":
						column_value = ''
					tt[column_name] = column_value
				if k not in DD[name]:
					DD[name][k] = []
				DD[name][k].append(tt)
	# format dd
	dd = {}
	for table_id in DD['tables']:
		#print(len(DD['tables'][x]),DD['tables'][x][0]['name'])
		if len(DD['tables'][table_id]) != 1:
			log.warning('SKIP',DD['tables'][table_id])
			continue
		table_name = DD['tables'][table_id][0]['name']
		log.info(f'format table({table_name}) table_id:{table_id}')
		if table_id not in DD['columns']:
			log.warning(f'SKIP TABLE {table_name}, no column')
			continue
		table = DD['tables'][table_id][0]
		try:
			schema_name = DD['schemata'][table['schema_id']][0]['name']
		except:
			continue
		#columns = DD['columns'][table_id]
		columns = []
		for col in DD['columns'][table_id]:
			col['type'] = MYSQLTYPE2INNODBTYPE[col['type']]
			col['is_nullable'] = INT2BOOLEAN(col['is_nullable'])
			col['is_zerofill'] = INT2BOOLEAN(col['is_zerofill'])
			col['is_unsigned'] = INT2BOOLEAN(col['is_unsigned'])
			col['is_auto_increment'] = INT2BOOLEAN(col['is_auto_increment'])
			col['is_virtual'] = INT2BOOLEAN(col['is_virtual'])
			col['hidden'] = HIDDEN2INT[col['hidden']]
			col['datetime_precision_null'] = 0 if col['type'] in [18,19,20] else 1
			if col['datetime_precision'] == '':
				col['datetime_precision'] = 0
			col['numeric_scale_null'] = True if col['type'] == 21 else False
			if col['numeric_scale'] == 'null':
				col['numeric_scale'] = 0
			if col['default_value_utf8'] == 'null':
				col['default_value_utf8'] = ''
				col['default_value_null'] = True
			else:
				col['default_value_null'] = False
			col['srs_id_null'] = True if col['srs_id'] == '' else False
			if col['default_value_utf8'] == 'null':
				col['default_value_utf8'] = ''
				col['default_value_utf8_null'] = True
			else:
				col['default_value_utf8_null'] = False
			col['default_option'] = '' if col['default_option'] == '' else bytes.fromhex(col['default_option'][2:]).decode()
			if col['update_option'] == '':
				col['update_option'] = ''
			if col['comment'] == "''":
				col['comment'] = ''
			if col['generation_expression_utf8'] == '':
				col['generation_expression_utf8'] = ''
			if col['generation_expression'] == '':
				col['generation_expression'] = ''
			else:
				col['generation_expression'] = bytes.fromhex(col['generation_expression'][2:]).decode()
			if col['options'] == 'null':
				col['options'] == ''
			col['column_key'] = COLUMNKEY2INT[col['column_key']]
			if col['type'] in [22,23]: # enum,set
				cvl = []
				cv = re.findall(r"['\"](.*?)['\"]",col['column_type_utf8'])
				for v in range(len(cv)):
					cvl.append({'name':base64.b64encode(cv[v].encode()).decode(),'index':v+1})
				
				col['elements'] = cvl
			else:
				col['elements'] = []
			col['is_explicit_collation'] = INT2BOOLEAN(col['is_explicit_collation'])
			columns.append(col)
		column_dict = { k['id']:k['ordinal_position'] for k in columns }

		# 对columns排个序
		_tcolumns = [ [_col['ordinal_position'],_col] for _col in columns ]
		try:
			_s = _tcolumns.sort()
		except:
			continue
		columns = [ _col[1] for _col in _tcolumns ]
			
		col_max_ordinal_position = max([ k['ordinal_position'] for k in columns ])
		if col_max_ordinal_position != len(columns):
			log.warning(f'SKIP TABLE {table_name}, incomplete column')
			continue
		indexes = []
		have_primary_key = False
		indexid = -1
		if table_id not in DD['indexes']:
			continue
		for idx in DD['indexes'][table_id]:
			if idx['name'] == 'PRIMARY':
				have_primary_key = True
				indexid = str2dict(idx['se_private_data'])['id']
			idxid = idx['id']
			if idxid not in DD['index_column_usage']:
				log.warning(f"SKIP TABLE {table_name} INDEX idx['name'], not in index_column_usage")
				continue
			elements = []
			for e in DD['index_column_usage'][idxid]:
				if e['column_id'] not in column_dict:
					log.warning(f"SKIP TABLE {table_name} INDEX idx['name'], column not found")
					continue
				#print(e['column_id'],column_dict[e['column_id']],e['ordinal_position'])
				elements.append({
					'ordinal_position':e['ordinal_position'],
					'length':4294967295 if e['length'] == '' else int(e['length']),
					'order':2 if e['order'] == 'ASC' else 3,
					'hidden':True if e['hidden'] == 0 else False,
					'column_opx':column_dict[e['column_id']]-1
					
				})
			t = idx
			# 对elements排个序
			_elements = [ [_e['ordinal_position'],_e] for _e in elements ]
			_s = _elements.sort()
			elements = [ _e[1] for _e in _elements ]

			t['elements'] = elements
			try:
				t['tablespace_ref'] = DD['tablespaces'][idx['tablespace_id']][0]['name']
			except:
				continue
			t['type'] = INDEXTYPE2INT[t['type']]
			t['algorithm'] = INDEXALGORITHM2INT[t['algorithm']]
			indexes.append(t)
		if not have_primary_key:
			log.warning(f'SKIP TABLE {table_name}, no primary key')
			continue
		check_constraints = []
		if table_id in DD['check_constraints']:
			for chk in DD['check_constraints'][table_id]:
				check_constraints.append({
					'name':chk['name'],
					'state':2,
					'check_clause':base64.b64encode(bytes.fromhex(chk['check_clause'][2:])).decode(),
					'check_clause_utf8':chk['check_clause_utf8'],
				})
		foreign_keys = []
		if table_id in DD['foreign_keys']:
			for fgk in DD['foreign_keys'][table_id]:
				fgk_elements = []
				rfgkid = fgk['id']
				if rfgkid in DD['foreign_key_column_usage']:
					_tt = -1
					for e in DD['foreign_key_column_usage'][rfgkid]:
						_tt += 1
						fgk_elements.append({'column_opx':_tt,'ordinal_position':e['ordinal_position'],'referenced_column_name':e['referenced_column_name']})
				foreign_keys.append({
					'name':fgk['name'],
					'match_option':fgk['match_option'],
					'update_rule':UPDATERILE2INT[fgk['update_rule']],
					'delete_rule':UPDATERILE2INT[fgk['delete_rule']],
					'unique_constraint_name':fgk['unique_constraint_name'],
					'referenced_table_catalog_name':fgk['referenced_table_catalog'],
					'referenced_table_schema_name':fgk['referenced_table_schema'],
					'referenced_table_name':fgk['referenced_table_name'],
					'elements':fgk_elements,
				})
		partitions = [] 
		mysql_version_id = table['mysql_version_id']
		dd[table_id] = {
			'table_id':table_id,
			'index_id':indexid,
			'table_name':table_name,
			'schema_name':schema_name,
			'sdi':{
				'dd_object':{
					'name':table_name,
					'options':table['options'],
					'check_constraints':check_constraints,
					'collation_id':table['collation_id'],
					'columns':columns,
					'comment':table['comment'],
					'created':table['created'],
					'default_partitioning':'',
					'default_subpartitioning':'',
					'engine':'InnoDB',
					'engine_attribute':'',
					'foreign_keys':foreign_keys,
					'hidden':1,
					'indexes':indexes,
					'last_altered':table['last_altered'],
					'last_checked_for_upgrade_version_id':0,
					'mysql_version_id':mysql_version_id,
					'partition_expression':'',
					'partition_expression_utf8':'',
					'is_explicit_partition_expression':True,
					'partition_type':0,
					'partitions':partitions,
					'row_format':ROW_FORMAT2INT[table['row_format'].upper()],
					'schema_ref':schema_name,
					'se_private_data':'',
					'se_private_id':0,
					'secondary_engine_attribute':'',
					'subpartition_expression':'',
					'subpartition_expression_utf8':'',
					'subpartition_type':0,
				},
				'dd_object_type':'Table',
				'dd_version':80000,
				'mysqld_version_id':mysql_version_id,
				'sdi_version':80000,
			},
		}
	return dd

# 从ibdata1(5.7)中读取被标记为delete的表
def READ_META_FROM_IBDATA1(log,filename,parser,opt):
	from ibd2sql.dictionary.tables import GET_SYS_TABLES_SDI
	SYS_TABLES_SDI = GET_SYS_TABLES_SDI()
	sdi_sys_table = [ SYS_TABLES_SDI[x] for x in SYS_TABLES_SDI ]
	ibdbase = IBDBASE(filename,log,{})
	file_base = {
		'filename':filename,
		'sdi':{},
		'encryption':ibdbase.ENCRYPTION,
		'key':ibdbase.key,
		'iv':ibdbase.iv,
		'pagesize':ibdbase.physical_size,
		'partition_name':None,
		'fsp_flags':ibdbase.fsp_flags,
	}
	pg = PAGE_READER(page_size=file_base['pagesize'],filename=file_base['filename'],encryption=file_base['encryption'],key=file_base['key'],iv=file_base['iv'])
	sys_index_id = {'sys_tables':[1,'id'],'sys_columns':[2,'table_id'],'sys_indexes':[3,'table_id'],'sys_fields':[4,'index_id'],'sys_foreign':[11,'name'],'sys_foreign_cols':[14,'name'],'sys_tablespaces':[15,'space'],'sys_datafiles':[16,'space'],'sys_virtual':[17,'table_id']}
	DD = {
		'sys_tables':{},
		'sys_columns':{},
		'sys_indexes':{},
		'sys_fields':{},
		'sys_foreign':{},
		'sys_foreign_cols':{},
		'sys_tablespaces':{},
		'sys_datafiles':{},
		'sys_virtual':{}
	}
	SYS_TABLE_OBJ = {}
	for sdi in sdi_sys_table:
		table_name = sdi[0]['dd_object']['name']
		bindexid = struct.pack('>HQ',0,sys_index_id[table_name][0])
		table = TABLE(sdi[0])
		idx = INDEX()
		idx.init_index(table=table,idxid=0,pg=pg,page_type='PK_LEAF',POST_ANTELOPE=file_base['fsp_flags']['POST_ANTELOPE'])
		SYS_TABLE_OBJ[bindexid] = {'name':table_name,'obj':idx}
	pages = os.path.getsize(file_base['filename'])//file_base['pagesize']
	pg.pageid = -1
	for _ in range(0,pages):
		data = pg.read(_)
		log.info('READ PAGE:',_)
		# double write,insert buffer
		if data[34:38] == b'\x00\x00\x00\x00' and data[64:74] in SYS_TABLE_OBJ:
			idx = SYS_TABLE_OBJ[data[64:74]]['obj']
			name = SYS_TABLE_OBJ[data[64:74]]['name']
			idx.init_data(data)
			all_data = []
			#all_data += idx.get_all_rows(True) # only deleted data
			if 'deleted' in opt:
				if opt['deleted'] in ['with','except']:
					all_data += idx.get_all_rows(False)
				elif opt['deleted'] in ['only','except']:
					all_data += idx.get_all_rows(True)
			else:
				all_data += idx.get_all_rows(True) # only deleted data
			for x in all_data:
				k = x['data'][sys_index_id[name][1]]['data']
				tt = {}
				for column_name in x['data']:
					column_value = remove_quotes(x['data'][column_name]['data'])
					if column_value == 'null' or column_value == "''":
						column_value = ''
					tt[column_name] = column_value
				if k not in DD[name]:
					DD[name][k] = []
				DD[name][k].append(tt)
				#if name == 'sys_tables':
				#	log.info(f"current_pageid:{_} table_name:{tt['name']} index_id:{tt['space']}")
#			idx.init_data(data)
#			all_data = idx.get_sql(True) # only deleted data
#			if name == parser.TABLE_NAME:
#				for k in all_data:
#					print('PAGENO:',_,k)
#	exit(1)
	# format dd
	dd = {}
	for table_id in DD['sys_tables']:
		table = DD['sys_tables'][table_id][-1]
		if len(table['name'].split('/')) != 2:
			log.warning(f"SKIP TABLE {table['name'].split('/')}, not schema/name")
			continue
		schema_name,table_name = table['name'].split('/')
		if table_id not in DD['sys_columns']:
			log.warning(f'SKIP TABLE {table_name}, no column')
			continue
		if table_name[:4] == 'FTS_':
			continue
		mysql_version_id = 50744
		#indexid = table['space']
		indexid = 0
		table_options = ""
		table_comment = ''
		table_created = ''
		table_last_altered = ''
		table_row_format = ROW_FORMAT2INT['REDUNDANT'] if table['n_cols']&(2**31) == 0 else ROW_FORMAT2INT[GET_ROWFORMAT_FROM_TABLE_FLAGS(table['type'])]
		table_collation_id = 33 # 没记录表的字符集啊, 我也没辙
		columns = []
		column_dict = {}
		for col in DD['sys_columns'][table_id]:
			if col['pos']>>16:
				continue # 虽然我们知道虚拟列有哪些字段(sys_virtual), 但无法确定其关系,故丢了算逑.
			if col['name'] in column_dict:
				continue
			else:
				column_dict[col['name']] = [col['pos']+1,col['len']]
			colltion_id = col['prtype']>>16
			col['type'] = COL_TYPE[col['prtype']&255][2]
			col['is_nullable'] = True if col['prtype']&256 == 0 else False
			col['is_zerofill'] = False
			col['is_unsigned'] = False if col['prtype']&512 == 0 else True
			col['is_auto_increment'] = False
			col['is_virtual'] = False #True if col['prtype']&8192 == 0 else False
			col['hidden'] = 1 
			col['ordinal_position'] = col['pos'] + 1
			col['collation_id'] = col['prtype']>>16
			col['collation_id'] = table_collation_id if col['collation_id'] == 0 else col['collation_id']
			col['char_length'] = col['len']
			col['numeric_precision'] = 0
			col['numeric_scale'] = 0
			col['numeric_scale_null'] = True
			col['datetime_precision'] = 0
			col['datetime_precision_null'] = 0
			col['has_no_default'] = True
			col['default_value_null'] = True
			col['srs_id_null'] = True
			col['srs_id'] = 0
			col['default_value'] = ''
			col['default_value_utf8_null'] = True
			col['default_value_utf8'] = ''
			col['default_option'] = ''
			col['update_option'] = ''
			col['comment'] = ''
			col['generation_expression'] = ''
			col['generation_expression_utf8'] = ''
			col['options'] = ''
			col['se_private_data'] = ''
			col['engine_attribute'] = ''
			col['secondary_engine_attribute'] = ''
			col['column_key'] = ''
			col['column_type_utf8'] = ''
			col['elements'] = ''
			col['is_explicit_collation'] = False
			columns.append(col)
		# sort columns by ordinal_position
		_t_columns = [ [c['ordinal_position'],c] for c in columns  ]
		_t = _t_columns.sort()
		columns = [ c[1] for c in _t_columns ]
		have_primary_key = False
		PRIMARY_KEY_IS_ROWID = False
		indexes = []
		indexes_used = []
		indexes_ordinal_position = 0
		if table_id not in DD['sys_indexes']:
			log.warning(f"SKIP TABLE {table_name}, not in indexes")
			continue
		for idx in DD['sys_indexes'][table_id]:
			if idx['id'] in indexes_used:
				continue
			else:
				indexes_used.append(idx['id'])
			idxid = idx['id']
			elements = []
			elements_used = []
			if (idxid not in DD['sys_fields']) and (idx['name'] != 'GEN_CLUST_INDEX'):
				log.warning(f"SKIP TABLE {table_name} INDEX {idx['name']}, not in sys_fields")
				continue
			if idx['name'] == 'GEN_CLUST_INDEX':
				indexid = idxid
				PRIMARY_KEY_IS_ROWID = True
				idx['name'] = 'PRIMARY'
				have_primary_key = True
				_elc_odp = 0
				for _elc in range(len(columns),len(columns)+3):
					_elc_odp += 1
					elements.append({
						'ordinal_position':_elc_odp,
						'length':4294967295,
						'order':2,
						'hidden':True,
						'column_opx':_elc
					})
				for _elc in range(len(columns)):
					_elc_odp += 1
					elements.append({
						'ordinal_position':_elc_odp,
						'length':4294967295,
						'order':2,
						'hidden':True,
						'column_opx':_elc
					})
					
			elif idx['name'] == 'PRIMARY':
				indexid = idxid
				have_primary_key = True
				for e in DD['sys_fields'][idxid]:
					if e['col_name'] in elements_used:
						continue
					else:
						elements_used.append(e['col_name'])
					if e['col_name'] in column_dict:
						log.warning(f"SKIP TABLE {table_name} INDEX {idx['name']}, column not found")
						elements.append({
							'ordinal_position':(e['pos']>>16)+1,
							'length':e['pos']&65535 if e['pos']&65535 >0 else column_dict[e['col_name']][1],
							'order':2,
							'hidden':False,
							'column_opx':column_dict[e['col_name']][0]-1
						})
			idx['elements'] = elements
			idx['tablespace_ref'] = ''
			idx['type'] = INDEX57TYPE2INT(idx['type'])
			idx['algorithm'] = 2
			idx['se_private_data'] = ''
			indexes_ordinal_position += 1
			idx['ordinal_position'] = indexes_ordinal_position
			idx['comment'] = ''
			idx['is_visible'] = True
			indexes.append(idx)
		if PRIMARY_KEY_IS_ROWID:
			_tc = {
				'name':'DB_ROW_ID',
				'type':10,
				'hidden':2,
				'char_length':6,
				'ordinal_position':len(columns)+1,
			}
			_tc.update(_SYS_COL_OPT)
			columns.append(_tc)
		
		_tc = {
			'name':'DB_TRX_ID',
			'type':10,
			'hidden':2,
			'char_length':6,
			'ordinal_position':len(columns)+1,
		}
		_tc.update(_SYS_COL_OPT)
		columns.append(_tc)
		_tc = {
			'name':'DB_ROLL_PTR',
			'type':9,
			'hidden':2,
			'char_length':7,
			'ordinal_position':len(columns)+1,
		}
		_tc.update(_SYS_COL_OPT)
		columns.append(_tc)
		check_constraints = []
		foreign_keys = []
		partitions = []
		#print(DD['sys_tables'][table_id][0]['name'])
		dd[table_id] = {
			'table_id':table_id,
			'index_id':indexid,
			'table_name':table_name,
			'schema_name':schema_name,
			'sdi':{
				'dd_object':{
					'name':table_name,
					'options':table_options,
					'check_constraints':check_constraints,
					'collation_id':table_collation_id,
					'columns':columns,
					'comment':table_comment,
					'created':table_created,
					'default_partitioning':'',
					'default_subpartitioning':'',
					'engine':'InnoDB',
					'engine_attribute':'',
					'foreign_keys':foreign_keys,
					'hidden':1,
					'indexes':indexes,
					'last_altered':table_last_altered,
					'last_checked_for_upgrade_version_id':0,
					'mysql_version_id':mysql_version_id,
					'partition_expression':'',
					'partition_expression_utf8':'',
					'is_explicit_partition_expression':True,
					'partition_type':0,
					'partitions':partitions,
					'row_format':table_row_format,
					'schema_ref':schema_name,
					'se_private_data':'',
					'se_private_id':0,
					'secondary_engine_attribute':'',
					'subpartition_expression':'',
					'subpartition_expression_utf8':'',
					'subpartition_type':0,
				},
				'dd_object_type':'Table',
				'dd_version':80000,
				'mysqld_version_id':mysql_version_id,
				'sdi_version':80000,
			},
		}
#	for k in dd:
#		if dd[k]['table_name'] == 't20251231_null':
#			print(json.dumps(dd[k]))
#			exit(1)
#	exit(1)
	return dd

def SCAN_TABLE(log,parser,opt):
	log.info('#################### SCAN DROPPED TABLE ####################')
	# format parameters
	CHUNK_SIZE    = 16777216  if 'chunk-size'    not in opt else int(opt['chunk-size'])
	BUFFER_SIZE   = 1048576   if 'buffer-size'   not in opt else int(opt['buffer-size'])
	PAGE_SIZE     = 16384     if 'page-size'     not in opt else int(opt['page-size'])
	BLOCK_SIZE    = 4096      if 'block-size'    not in opt else int(opt['block-size'])
	OFFSET_START  = 0         if 'offset-start'  not in opt else int(opt['offset-start'])
	OFFSET_STOP   = 2**63     if 'offset-stop'   not in opt else int(opt['offset-stop'])
	TABLESPACE_ID = -1        if 'tablespace-id' not in opt else int(opt['tablespace-id'])
	WITH_SDI = True if 'with-sdi' in opt else False
	WITH_FRM = True if 'with-frm' in opt else False
	CHECK_TABLE  = CHECK_PAGE_OLD if 'check-table-old' in opt else CHECK_PAGE
	# output mode is sql?
	SQLMODE = True if parser.SQL or parser.DELETED else False

	HAVE_METAFILE = True if len(parser.FILENAME) > 0 else False
	HAVE_DEVICE = True if not (parser.SCAN_DROP_TABLE is True) else False
	SCAN_ALL_INDEX = False
	DEVICE_NAME = ''
	SCAN_DIR = parser.SCAN_DROP_TABLE
	if HAVE_DEVICE:
		DEVICE_NAME = parser.SCAN_DROP_TABLE
		if not os.path.exists(DEVICE_NAME):
			print('DEVICE_NAME',DEVICE_NAME,'is not exists')
			return 108
	if not (HAVE_METAFILE or HAVE_DEVICE):
		print('mysql.ibd/ibdata1 and device/dri require at least one')
		return 109
	HAVE_DATA = True
	HAVE_DELETED = False
	if parser.DELETED == 'only' or parser.DELETED == True:
		HAVE_DELETED = True
		HAVE_DATA = False
	if parser.DELETED == 'with':
		HAVE_DELETED = True


	dd = {}
	if HAVE_METAFILE:
		filename = parser.FILENAME[0]
		if not os.path.exists(filename):
			print(filename,'is not exists')
			return 110
		bsfilename = os.path.basename(filename)

		# get metadata
		log.info('will read metadata from ',filename)
		if bsfilename == 'mysql.ibd':
			dd = READ_META_FROM_MYSQLIBD(log,filename,parser,opt)
		elif bsfilename == 'ibdata1':
			dd = READ_META_FROM_IBDATA1(log,filename,parser,opt)
		else:
			print('metafile require ibdata1(5.7) or mysql.ibd(8.x)')
			return 111
	
	# sdi file
	if parser.SDI_FILE is not None:
		if 'indexid' not in opt:
			print('--sdi and --set indexid=xx must be used together')
			return 112
		sdi_file = parser.SDI_FILE
		global_sdi_info = None
		if sdi_file.endswith('.frm'):
			global_sdi_info = json.loads(MYSQLFRM(sdi_file)._get_sdi_json())
		elif sdi_file.endswith('.sdi'):
			with open(sdi_file,'r') as f:
				global_sdi_info = json.load(f)
			if len(global_sdi_info) == 3:
				global_sdi_info = global_sdi_info[1]
		elif sdi_file.endswith('.ibd'):
			ibdbase = IBDBASE(sdi_file,log,{})
			global_sdi_info = ibdbase.sdi[0]
		table_id = str2dict(global_sdi_info['dd_object']['indexes'][0]['se_private_data'])['table_id']
		index_id = opt['indexid']
		schema_name = global_sdi_info['dd_object']['schema_ref']
		table_name = global_sdi_info['dd_object']['name']
		dd[table_id] = {
			'table_id':table_id,
			'index_id':index_id,
			'schema_name':schema_name,
			'table_name':table_name,
			'sdi':global_sdi_info
		}

	# scan-dir's sdi
	if HAVE_DEVICE and os.path.isdir(SCAN_DIR):
		for _fname in os.listdir(os.path.join(SCAN_DIR,'sdi')):
			tfname = os.path.join(SCAN_DIR,'sdi',_fname)
			log.info('READ file',tfname)
			try:
				with open(tfname,'rb') as f:
					while True:
						tdata = f.read(PAGE_SIZE)
						if len(tdata) < PAGE_SIZE:
							break
						if tdata[24:26] != b'E\xbd':
							continue
						offset = struct.unpack('>h',tdata[97:99])[0] + 99
						_table_type,table_id = struct.unpack('>LQ',tdata[offset:offset+12])
						dunzip_len,dzip_len = struct.unpack('>LL',tdata[offset+33-8:offset+33])
						if tdata[offset-3:][:1] == b'\x14':
							continue
						unzbdata = zlib.decompress(tdata[offset+33:offset+33+dzip_len])
						dic_info = json.loads(unzbdata.decode())
						index_id = str2dict(dic_info['dd_object']['indexes'][0]['se_private_data'])['id']
						table_name = dic_info['dd_object']['name']
						schema_name= dic_info['dd_object']['schema_ref']
						dd[table_id] = {
							'table_id':table_id,
							'index_id':index_id,
							'schema_name':schema_name,
							'table_name':table_name,
							'sdi':dic_info
						}
					
			except Exception as e:
				pass

	# fileter
	if 'schema' in opt or 'table' in opt: # drop database, drop/truncate table
		tdd = {}
		for table_id in dd:
			if (True if 'table' not in opt else opt['table'] == dd[table_id]['table_name']) and (True if 'schema' not in opt else opt['schema'] == dd[table_id]['schema_name']):
				tdd[table_id] = dd[table_id]
			else:
				log.info('skip table',dd[table_id]['schema_name'],dd[table_id]['table_name'],'filter')
		dd = tdd

	
	if len(dd) == 0 and not HAVE_DEVICE:
		print('No matched table')
		return 113

	# DDL
	if len(dd) > 0:
		disable_foreign_key = True if 'disable-foreign-keys' in opt or 'foreign-keys-after' in opt else False
		for tbl in dd:
			if parser.PRINT_SDI:
				print(json.dumps(dd[tbl]['sdi']))
				continue
			print(f"\n-- {dd[tbl]['schema_name']}.{dd[tbl]['table_name']} table_id:{dd[tbl]['table_id']} index_id:{dd[tbl]['index_id']}")
			try:
				table = TABLE(dd[tbl]['sdi'])
			except Exception as e:
				log.warning(f"SKIP TABLE {dd[tbl]['table_name']}, {e} FORMAT TABLE faild")
				if SQLMODE:

					print(f'-- some table TABLE faild({e}), --sql/--delete will not become true')
					SQLMODE = False
				continue
			ddl = ''
			if parser.DDL:
				if parser.DDL == 'history':
					ddl = table.get_ddl_history(True,False,disable_foreign_key)
				elif parser.DDL in ['disable-keys','keys-after']:
					ddl = table.get_ddl(False,True,disable_foreign_key)
				else:
					ddl = table.get_ddl(False,False,disable_foreign_key)
				print(ddl)
		print('')
		if parser.PRINT_SDI:
			return 106

	# scan divice
	if HAVE_DEVICE:
		filename_pre = ''
		if parser.OUTPUT_FILEDIR and parser.OUTPUT_FILEDIR is not True:
			filename_pre = parser.OUTPUT_FILEDIR
		else:
			filename_pre = f"./ibd2sql_auto_dir_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
		nopt = {
			'CHUNK_SIZE':CHUNK_SIZE,
			'BUFFER_SIZE':BUFFER_SIZE,
			'PAGE_SIZE':PAGE_SIZE,
			'BLOCK_SIZE':BLOCK_SIZE,
			'OFFSET_START':OFFSET_START,
			'OFFSET_STOP':OFFSET_STOP,
			'TABLESPACE_ID':TABLESPACE_ID,
			'WITH_SDI':WITH_SDI,
			'WITH_FRM':WITH_FRM,
			'OUTPUT_DIR':filename_pre,
			'CHECK_TABLE_OLD':True if 'check-table-old' in opt else False
		}
		for k in nopt:
			log.info(k,':',nopt[k])

		# dir
		if os.path.isdir(parser.SCAN_DROP_TABLE):
			if not SQLMODE and not parser.DDL:
				print('扫描目录要求选项 --sql/--ddl 不然扫描个啥呢?')
				return 114
			if not (os.path.isdir(os.path.join(SCAN_DIR,'index')) and os.path.isdir(os.path.join(SCAN_DIR,'sql')) and os.path.isdir(os.path.join(SCAN_DIR,'blob')) and os.path.isdir(os.path.join(SCAN_DIR,'frm'))):
				print('目录格式不对,要求包含index,sql,frm,blob')
				return 115
			if not SQLMODE:
				return 0
			# 开始一个文件一个文件的解析(调IBD2SQL_SINGLE), 构建溢出页2
			for table_id in dd:
				index_id = dd[table_id]['index_id']
				schema_name = dd[table_id]['schema_name']
				table_name = dd[table_id]['table_name']
				tblname = f"{schema_name}.{table_name}"
				mfile = GET_MATCHFILE_FROMDIR(str(index_id).zfill(16)+'.page',os.path.join(SCAN_DIR,'index'))
				if len(mfile) == 0:
					print(f"-- skip table {tblname}, can not find index page")
					continue
				if len(mfile) > 1:
					print(f"-- table {tblname} have multi index page file, used first one {mfile[0]}")
				mfile = mfile[0]
				print(f"-- parser {dd[table_id]['schema_name']}.{dd[table_id]['table_name']} use file:{mfile}")
				# 生成 file_base
				file_base = {
					'filename':mfile,
					'sdi':dd[table_id]['sdi'],
					'encryption':False,
					'key':None,
					'iv':None,
					'pagesize':PAGE_SIZE,
					'partition_name':None,
					'fsp_flags':{'POST_ANTELOPE':False,'SHARED':False,'SDI':False}
				}
				nopt['PAGE_READER_FRAGMENT_PRE'] = os.path.join(SCAN_DIR,'blob')
				nopt['leafno'] = 0
				nopt['rootno'] = 0
				nopt['indexid'] = index_id
				#IBD2SQL_SINGLE(TABLE(dd[table_id]['sdi']),file_base,{**opt,**nopt},os.path.join(SCAN_DIR,'sql'),log,parser,nopt['PAGE_READER_FRAGMENT_PRE'])
				filenamepre = ''
				if parser.OUTPUT_FILEDIR:
					if parser.OUTPUT_FILEDIR is True:
						filenamepre = os.path.join(SCAN_DIR,'sql')
					else:
						filenamepre = parser.OUTPUT_FILEDIR
				if filenamepre != '':
					os.makedirs(filenamepre,exist_ok=True)
					log.info('output dir:',filenamepre)

				try:
					IBD2SQL_SINGLE(TABLE(dd[table_id]['sdi']),file_base,{**opt,**nopt},filenamepre,log,parser,nopt['PAGE_READER_FRAGMENT_PRE'])
					print(f"-- parser {dd[table_id]['schema_name']}.{dd[table_id]['table_name']} use file:{mfile} FINISH.")
				except Exception as e:
					print(e,f"-- parser {dd[table_id]['schema_name']}.{dd[table_id]['table_name']} use file:{mfile} FAILED.")
		# device 输出sql, 从dd里面获取indexid
		else:
			# device 输出page, 优先从opt获取indexid,否则再从dd获取indexid
			ndd = {}
			if parser.SET_OPTIONS is not None:
				for topt in parser.SET_OPTIONS:
					toptk,toptv = topt.split('=')
					if 'indexid' == toptk:
						for stridxid in toptv.split(','):
							if stridxid.upper() == "ALL": # 仅扫描所有索引页
								SCAN_ALL_INDEX = True
								SQLMODE = False
								continue
							idxid = int(stridxid)
							ndd[idxid] = {
								'table_id':idxid,
								'index_id':idxid,
								'table_name':idxid,
								'schema_name':idxid,
								'sdi':[]
							}
			if len(ndd) == 0:
				ndd = dd
			if SQLMODE: # --sql模式不支持仅指定indexid
				ndd = dd
			if len(ndd) == 0:
				print('no matched tables 115')
				return 115
			else:
				for tableid in ndd:
					log.info('will scan indexid:',ndd[tableid]['index_id'])
			OFFSET = Value(ctypes.c_uint64, 0)
			OFFSET.value = nopt['OFFSET_START']
			os.makedirs(nopt['OUTPUT_DIR'],exist_ok=True)
			os.makedirs(os.path.join(nopt['OUTPUT_DIR'],'blob'),exist_ok=True)
			os.makedirs(os.path.join(nopt['OUTPUT_DIR'],'frm'),exist_ok=True)
			os.makedirs(os.path.join(nopt['OUTPUT_DIR'],'index'),exist_ok=True)
			os.makedirs(os.path.join(nopt['OUTPUT_DIR'],'sdi'),exist_ok=True)
			os.makedirs(os.path.join(nopt['OUTPUT_DIR'],'sql'),exist_ok=True) # 放SQL语句的
			print('-- OUTPUT DIR:',nopt['OUTPUT_DIR'])
			lock = Lock()
			worker = {}
			for x in range(parser.PARALLEL):
				worker[x] = Process(target=SCAN_DEV_WORKER,args=(x,parser,ndd,nopt,log,OFFSET,lock,DEVICE_NAME,SQLMODE,SCAN_ALL_INDEX))
			for x in range(parser.PARALLEL):
				worker[x].start()
			for x in range(parser.PARALLEL):
				worker[x].join()
			print('SCAN FINISHED.',nopt['OUTPUT_DIR'])

def SCAN_DEV_WORKER(p,parser,dd,opt,log,OFFSET,lock,DEVICE_NAME,SQLMODE,SCAN_ALL_INDEX):
	log.info(f'[{p}] Process:',p,'start, PID:',os.getpid())
	CHECK_TABLE  = CHECK_PAGE_OLD if opt['CHECK_TABLE_OLD'] else CHECK_PAGE
	gdd = {} 
	gfdl = {} # 只有index page/sql才会保存fd.  sdi和blob等没必要
	if SQLMODE:
		for tableid in dd:
			table = TABLE(dd[tableid]['sdi'])
			idx = INDEX()
			idx.init_index(table=table,idxid=0,pg=None,page_type='PK_LEAF',disable_extra_pages=True,replace=parser.REPLACE,complete=parser.COMPLETE_INSERT)
			gdd[struct.pack('>HQ',0,int(dd[tableid]['index_id']))] = [idx,str(dd[tableid]['index_id']).zfill(16)]
	else:
		for tableid in dd:
			gdd[struct.pack('>HQ',0,int(dd[tableid]['index_id']))] = [None,str(dd[tableid]['index_id']).zfill(16)]
	print(f"[{p}] START")
	goffset = 0
	f = open(DEVICE_NAME,'rb')
	status,devsize = GET_SIZE_FROM_DEV(DEVICE_NAME)
	if not status:
		print(f'GET {DEVICE_NAME} size failed')
		return 116
	MAXFILESIZE = min(opt['OFFSET_STOP'],devsize)
	LASTPRINTTIME = int(time.time())
	while goffset < opt['OFFSET_STOP']:
		with lock:
			toffset = OFFSET.value
			if toffset > MAXFILESIZE:
				log.info(f"[{p}] NO CHUNK TO REQUEST, {toffset} {MAXFILESIZE}")
				break
			goffset = toffset
			toffset += opt['CHUNK_SIZE']
			OFFSET.value = toffset
		log.info(f"[{p}] REQUEST start:{goffset} size:{opt['CHUNK_SIZE']} ")
		readsize = 0
		finish_flag = False
		if goffset > opt['PAGE_SIZE']:
			f.seek(goffset-opt['PAGE_SIZE']+opt['BLOCK_SIZE'],0)
		data = f.read(opt['PAGE_SIZE']-opt['BLOCK_SIZE'])
		while readsize < opt['CHUNK_SIZE']:
			data += f.read(opt['BUFFER_SIZE'])
			readsize += opt['BUFFER_SIZE']
			if len(data) < opt['BUFFER_SIZE']:
				finish_flag = True
			offset = 0
			WRITE_DATA = []
			while offset < opt['BUFFER_SIZE']:
				tdata = data[offset:][:opt['PAGE_SIZE']]
				if len(tdata) != opt['PAGE_SIZE']:
					break
				tablespace_id,page_id = struct.unpack('>LL',tdata[34:38]+tdata[8:12])
				tablespace_id = f"{p}_"+str(tablespace_id).zfill(10)+"_"
				page_id2 = str(page_id).zfill(16)
				page_id = tablespace_id + str(page_id).zfill(10)
				if IS_PAGE(tdata):
					if IS_INDEX(tdata) and (SCAN_ALL_INDEX or tdata[64:74] in gdd):
						offset += opt['PAGE_SIZE']
						if not CHECK_TABLE(tdata):
							continue
						log.info(f"[{p}] {goffset}:{readsize}:{offset} is MATCHE INDEX PAGE")
						if SQLMODE: # 转为SQL语句
							idx = gdd[tdata[64:74]][0]
							idx.init_data(tdata)
							try:
								tsql = idx.get_sql(False)
								WRITE_DATA.append(['sql',f'{p}_{idx.table.schema}.{idx.table.name}',tsql])
							except:
								pass
						else: # 输出page
							#WRITE_DATA.append(['index',tablespace_id+gdd[tdata[64:74]][1],tdata])
							WRITE_DATA.append(['index',tablespace_id+str(struct.unpack('>Q',tdata[66:74])[0]).zfill(16),tdata])
					elif opt['WITH_SDI'] and IS_SDI(tdata) and not SQLMODE:
						if not CHECK_TABLE(tdata):
							continue
						WRITE_DATA.append(['sdi',page_id,tdata])
						offset += opt['PAGE_SIZE']
					elif IS_OFFPAGE(tdata) and not SQLMODE and page_id2 != '0000000000000000':
						if not CHECK_TABLE(tdata):
							continue
						offset += opt['PAGE_SIZE']
						WRITE_DATA.append(['blob',page_id2,tdata])
					else:
						offset += opt['BLOCK_SIZE']
				elif opt['WITH_FRM'] and IS_FRM(tdata):
					offset += opt['PAGE_SIZE']
				else:
					offset += opt['BLOCK_SIZE']
			# 写这次buffer获取到的数据
			if len(WRITE_DATA) > 0:
				print(f"[{p}] WRITE BUFFER DATA",len(WRITE_DATA))
			for t,name,tdata in WRITE_DATA:
				ofilename = os.path.join(opt['OUTPUT_DIR'],t,name)
				ofilename += ".page" if t != 'sql' else '.sql'
				if t == 'index' or t == 'sql':
					if ofilename not in gfdl:
						print(f"[{p}] NEW FILE",ofilename)
						gfdl[ofilename] = open(ofilename,'ab' if t != 'sql' else 'a')
					if SQLMODE:
						for ntdata in tdata:
							gfdl[ofilename].write(ntdata+';\n')
					else:
						gfdl[ofilename].write(tdata)
				else:
					with open(ofilename,'ab') as _tf:
						_tf.write(tdata)
				

			# 下一次循环
			data = data[offset:]

		if finish_flag:
			break
		# 展示下进度吧
		if (time.time()-LASTPRINTTIME)>10:
			print(f"[{p}] {round((goffset+opt['CHUNK_SIZE']-opt['OFFSET_START'])/(MAXFILESIZE-opt['OFFSET_START'])*100,2)} %")
			LASTPRINTTIME = int(time.time())
	for ofilename in gfdl:
		#print(f"[{p}] closed file ",ofilename)
		gfdl[ofilename].close()
	f.close()
	print(f"[{p}] FINISH")

# 直接使用ib2sql/ibd2sql.signal
def SCAN_DIR_WORKER(p,parser,dd,opt):
	pass
