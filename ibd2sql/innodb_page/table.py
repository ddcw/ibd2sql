import json
import base64
from ibd2sql.utils.collations import COLLATIONS_DICT
from ibd2sql.utils.b2data import *
from ibd2sql.innodb_page.column_type import COLUMN_TYPE
from ibd2sql.innodb_page.subpartition import SUB_PARTITION

ROW_FORMAT = {
	2:'DYNAMIC',
	3:'COMPRESSED',
	4:'REDUNDANT',
	5:'COMPACT'
}

INDEX_TYPE = {
	1:'PRIMARY ',
	2:'UNIQUE ',
	3:'',
	4:'FULLTEXT ',
	5:'SPATIAL '
}

INDEX_ALG = {
	2:'BTREE+',
	3:'SPATIAL',
	5:'FULLTEXT'
}

PARTITION_TYPE = {
	0:"",
	1:"HASH",
	3:"KEY",
	7:"RANGE",
	8:"LIST"
}

def str2dict(data):
	dd = {}
	for x in data.split(';'):
		if x == '':
			continue
		k,v = x.split('=')
		dd[k] = v
	return dd

def element_b64_format(data):
	dd = {}
	for x in data:
		dd[x['index']] = base64.b64decode(x['name']).decode()
	return dd
	

#def map_decimal(n):
#	# [[bytes, length], [],... ]
#	return [ [4,9] for _ in range(n//9) ] + ([[ ((n%9)+1)//2 if n%9 < 7 else 4,n%9 ]] if n%9 > 0 else [])


def auto_col_convert(data,column,charset):
	"""
	`colname` --> convert(`colname`using charset) if column['charset']!=charset
	"""
	for colid in column:
		col = column[colid]
		colname = col['name']
		if col['character_set_name'] != charset and col['is_var']:
			data = data.replace(f"`{colname}`",f"convert(`{colname}` using {charset})")
	return data

# for ddl history
def column_type_utf8(col):
	col_type = col['type']
	col_type_name = COLUMN_TYPE[col_type]['name2']
	data = COLUMN_TYPE[col_type]['name2']
	if col['collation_id'] == 63:
		data.replace('char','binary')
	if col_type >= 24 and col_type <= 27 and col['collation_id'] == 63: # blob
		data.replace('text','blob')
	elif col_type_name in ['char','varchar']: # char/varchar
		data += f"({col['char_length']//int(col['character_set_maxlen'])})"
	elif col_type_name in ['int','tinyint','smallint','mediumint','bigint']: # number
		data += f"({col['char_length']})"
		if col['is_unsigned']:
			data += " unsigned"
		if col['is_zerofill']:
			data += " zerofill"
	elif col_type_name == 'decimal': # decimal
		data += f"({col['numeric_precision']},{col['numeric_scale']})"
	elif col_type_name in ['time','timestamp','datetime'] and 'datetime_precision' in col and col['datetime_precision'] > 0:
		data += f"({col['datetime_precision']})"
	elif col_type_name == 'bit' and col['numeric_precision'] > 0:
		data += f"({col['numeric_precision']})"
	elif col_type_name in ['enum','set']:
		data += f"({ ','.join([ repr(base64.b64decode(x['name']).decode()) for x in col['elements'] ]) })"
	return data

class TABLE(object):
	"""
	INPUT:
		sdi: sdi data(json), only one table
		schema: set new schema name
		name: set new table name
	RETURN:
		TBALE OBJ

	ATTR:
		sdi: sdi metadata(json)
		row_format:
		column: all column(rowid,trxid,rollptr,delete_rows,gen_pk...)
		pk: primary key
		pkmr: primary key multi row version()
		name: table name
		schema: schema name
		comment:
		collate: charset
		engine: innodb
		encryption:True,False
		compression:None,zlib,lz4
		#STATS_PERSISTENT:
		_column: column obj
		_index: index obj
		_partition: partition obj
		_reference: foregin key
		_check: check constraint
		
	FUNC:
		get_ddl: get ddl

	pkmr:{
		row_version:{
			colid:[1,2...],
			null_count:n
		}, ....
	}
	"""
	def __init__(self,sdi,schema=None,name=None):
		self._enclosed = '`' # column&index optionally enclosed
		self._start = '  ' # column&index pre char
		self._pre = "CREATE TABLE IF NOT EXISTS "
		self.disable_foreign_key = False 
		#self.sdi = json.loads(sdi)[0]
		self.sdi = sdi
		self.ddl_history_list = []
		self.schema = schema if schema is not None else self.sdi['dd_object']['schema_ref']
		self.name = name if name is not None else self.sdi['dd_object']['name']
		self.init()

	def init(self,):
		dd_object = self.sdi['dd_object']
		options = str2dict(dd_object['options'])
		self.max_row_version = 0 # for mr
		self.mysql_version_id = dd_object['mysql_version_id']
		self.row_format = ROW_FORMAT[dd_object['row_format']]
		self.col_rollptr = 0 # rollptr colid
		self.col_trxid = 0 # trxid colid
		self.pkmr = {}
		self.name = dd_object['name']
		self.schema = dd_object['schema_ref']
		self.comment = dd_object['comment']
		self.collate = dd_object['collation_id']
		self.character_set_name = self._get_character_set_name(dd_object['collation_id'])
		self.collation_name = self._get_collation_name(dd_object['collation_id'])
		self.engine = dd_object['engine']
		self.encryption = False if 'encrypt_type' in options and options['encrypt_type'] == 'N' else True
		self.pack_record = int(options['pack_record']) if 'pack_record' in options else 0
		self.compression = True if 'compress' in options else False
		self.compression_type = options['compress'] if 'compress' in options else ''
		self.init_column()
		self.init_index()
		self.init_pkmr()
		self.init_pk_null_count() # without new add column

	# utf8 --> utf8mb3 when mysql version >= 8.0.29
	# utf8mb3 --> utf8 when mysql version < 8.0.29
	def _get_character_set_name(self,collation_id):
		CHARACTER_SET_NAME = COLLATIONS_DICT[str(collation_id)]['CHARACTER_SET_NAME']
		#return 'utf8' if self.mysql_version_id <= 80028 and CHARACTER_SET_NAME == 'utf8mb3' else CHARACTER_SET_NAME
		return CHARACTER_SET_NAME

	def _get_collation_name(self,collation_id):
		COLLATION_NAME = COLLATIONS_DICT[str(collation_id)]['COLLATION_NAME']
		CHARACTER_SET_NAME = COLLATIONS_DICT[str(collation_id)]['CHARACTER_SET_NAME']
		#return COLLATION_NAME.replace('utf8mb3_','utf8_') if self.mysql_version_id <= 80028 and CHARACTER_SET_NAME == 'utf8mb3' else COLLATION_NAME
		return COLLATION_NAME

	def _get_character_set_maxlen(self,collation_id):
		return COLLATIONS_DICT[str(collation_id)]['MAXLEN']

	def init_column(self):
		column = [ self._init_column(col) for col in self.sdi['dd_object']['columns'] ]
		self.column = dict([ (col['ordinal_position']-1,col) for col in column ])
		self.column_order = []
		for colid in self.column:
			col = self.column[colid]
			if col['hidden'] == 1:
				self.column_order.append((col['name'],col['default']))
		#self.column = dict([ (col['physical_pos'],col) for col in column ])
		#column = [ [col['physical_pos'],col] for col in column ]

		# ph column (for pk)
		column = [ col for col in column  ]
		column2 = [ [column[x]['physical_pos'],x] for x in range(len(column)) ]
		column2.sort()
		self.ph_column = dict([ (x[0],column[x[1]]) for x in column2 ])

	def _init_column(self,data):
		# sql/dd/types/column.h
		data['is_var'] = COLUMN_TYPE[data['type']]['is_var']
		data['is_big'] = True if data['char_length'] > 255 else False
		data['type_name'] = COLUMN_TYPE[data['type']]['name']
		data['character_set_name'] = self._get_character_set_name(data['collation_id'])
		data['character_set_maxlen'] = self._get_character_set_maxlen(data['collation_id'])
		data['collation_name'] = self._get_collation_name(data['collation_id'])
		if data['column_type_utf8'] == '':
			data['column_type_utf8'] = column_type_utf8(data)

		data['default'] = 'null' if data['default_value_utf8_null'] else repr(data['default_value_utf8'])

		se_private_data = {} if 'se_private_data' not in data else str2dict(data['se_private_data'])

		if 'default' in se_private_data or 'version_dropped' in se_private_data or 'version_added' in se_private_data or 'default_null' in se_private_data:
			if self.mysql_version_id <= 80028:
				self.max_row_version += 1
				data['version_added'] = self.max_row_version
				data['version_dropped'] = 66
			else:
				data['version_added'] = 0 if 'version_added' not in se_private_data else int(se_private_data['version_added'])
				data['version_dropped'] = 66 if 'version_dropped' not in se_private_data else int(se_private_data['version_dropped'])
				self.max_row_version = max(data['version_added'],data['version_dropped'],self.max_row_version) if data['version_dropped'] != 66 else max(self.max_row_version,data['version_added'])
		else:
			data['version_added'] = 0
			data['version_dropped'] = 66

		#data['physical_pos'] = int(se_private_data['physical_pos']) if 'physical_pos' in se_private_data else -1
		data['physical_pos'] = int(se_private_data['physical_pos']) if 'physical_pos' in se_private_data else data['ordinal_position'] - 1
		#print(data['name'],data['version_added'],data['version_dropped'])
		#data['version_added'] = 0 if 'version_added' not in se_private_data else int(se_private_data['version_added'])
		#data['version_dropped'] = 66 if 'version_dropped' not in se_private_data else int(se_private_data['version_dropped'])
		#self.max_row_version = max(self.max_row_version,data['version_added'],data['version_dropped'] if data['version_dropped'] < 66 else 0)
		data['table_id'] = 0 if 'table_id' not in se_private_data else se_private_data['table_id']
		data['size'] = 0
		data['decode'] = None
		data['args'] = [] # pad (timestamp,time...)

		data['element'] = [ base64.b64decode(x['name']).decode() for x in data['elements'] ]

		datetime_precision_size = (data['datetime_precision']+1)//2

		if data['name'] == 'DB_ROW_ID':
			data['is_var'] = False
			data['size'] = 6
			data['decode'] = B2UINT6
		elif data['name'] == 'DB_TRX_ID':
			data['is_var'] = False
			data['size'] = 6
			data['decode'] = B2UINT6
			self.col_trxid = data['ordinal_position'] - 1
		elif data['name'] == 'DB_ROLL_PTR':
			data['is_var'] = False
			data['size'] = 7
			data['decode'] = B2UINT7
			self.col_rollptr = data['ordinal_position'] - 1
		elif data['name'] == 'my_row_id' and self.mysql_version_id >= 80030 \
			and data['is_unsigned'] \
			and data['hidden'] == 4:
			# sql_generate_invisible_primary_key
			data['is_var'] = False
			data['size'] = 8
			data['decode'] = B2UINT8
		elif data['type_name'] in ['DECIMAL','NEWDECIMAL']:
			p1 = map_decimal(data['numeric_precision']-data['numeric_scale'])
			p2 = map_decimal(data['numeric_scale'])
			data['size'] = sum([x[0] for x in p1]) + sum([x[0] for x in p2])
			data['args'] = [p1,p2]
			data['decode'] = B2DECIMAL
		elif data['type_name'] in ['TINY']: # tinyint
			data['size'] = 1
			data['decode'] = B2UINT1 if data['is_unsigned'] else B2INT1
		elif data['type_name'] in ['SHORT']: # smallint_col
			data['size'] = 2
			data['decode'] = B2UINT2 if data['is_unsigned'] else B2INT2
		elif data['type_name'] in ['LONG']: # int32
			data['size'] = 4
			data['decode'] = B2UINT4 if data['is_unsigned'] else B2INT4
		elif data['type_name'] in ['FLOAT']: # float
			data['size'] = 4
			data['decode'] = B2FLOAT
		elif data['type_name'] in ['DOUBLE']: # double
			data['size'] = 8
			data['decode'] = B2DOUBLE
		elif data['type_name'] in ['TIMESTAMP','TIMESTAMP2']: # timestamp
			data['size'] = 4 + datetime_precision_size
			data['decode'] = B2TIMESTAMP
			data['args'] = [data['datetime_precision']]
		elif data['type_name'] in ['LONGLONG']: # bigint
			data['size'] = 8
			data['decode'] = B2UINT8 if data['is_unsigned'] else B2INT8
		elif data['type_name'] in ['INT24']: # mediumint col
			data['size'] = 3
			data['decode'] = B2UINT3 if data['is_unsigned'] else B2INT3
		elif data['type_name'] in ['DATE','NEWDATE']: # date
			data['size'] = 3
			data['decode'] = B2DATE
		elif data['type_name'] in ['TIME','TIME2']: # time
			data['size'] = 3 + datetime_precision_size
			data['decode'] = B2TIME
			data['args'] = [data['datetime_precision']]
		elif data['type_name'] in ['DATETIME','DATETIME2']: # datetime
			data['size'] = 5 + datetime_precision_size
			data['decode'] = B2DATETIME
			data['args'] = [data['datetime_precision']]
		elif data['type_name'] in ['YEAR']: # year
			data['size'] = 1
			data['decode'] = B2YEAR
		elif data['type_name'] in ['VARCHAR','VAR_STRING','STRING','TINY_BLOB','MEDIUM_BLOB','LONG_BLOB','BLOB']: # varchar/char/blob/text/binary
			charname = data['character_set_name']
			if charname == 'binary': # blob/binary/varbinary
				data['decode'] = B2STR_binary
			elif charname == 'armscii8':
				data['decode'] = B2STR_armscii8
			elif charname == 'ascii':
				data['decode'] = B2STR_ascii
			elif charname == 'big5':
				data['decode'] = B2STR_big5
			elif charname == 'cp1250':
				data['decode'] = B2STR_cp1250
			elif charname == 'cp1251':
				data['decode'] = B2STR_cp1251
			elif charname == 'cp1256':
				data['decode'] = B2STR_cp1256
			elif charname == 'cp1257':
				data['decode'] = B2STR_cp1257
			elif charname == 'cp850':
				data['decode'] = B2STR_cp850
			elif charname == 'cp852':
				data['decode'] = B2STR_cp852
			elif charname == 'cp866':
				data['decode'] = B2STR_cp866
			elif charname == 'cp932':
				data['decode'] = B2STR_cp932
			elif charname == 'dec8':
				data['decode'] = B2STR_dec8
			elif charname == 'eucjpms':
				data['decode'] = B2STR_eucjpms
			elif charname == 'euckr':
				data['decode'] = B2STR_euckr
			elif charname == 'gb18030':
				data['decode'] = B2STR_gb18030
			elif charname == 'gb2312':
				data['decode'] = B2STR_gb2312
			elif charname == 'gbk':
				data['decode'] = B2STR_gbk
			elif charname == 'geostd8':
				data['decode'] = B2STR_geostd8
			elif charname == 'greek':
				data['decode'] = B2STR_greek
			elif charname == 'hebrew':
				data['decode'] = B2STR_hebrew
			elif charname == 'hp8':
				data['decode'] = B2STR_hp8
			elif charname == 'keybcs2':
				data['decode'] = B2STR_keybcs2
			elif charname == 'koi8r':
				data['decode'] = B2STR_koi8r
			elif charname == 'koi8u':
				data['decode'] = B2STR_koi8u
			elif charname == 'latin1':
				data['decode'] = B2STR_latin1
			elif charname == 'latin2':
				data['decode'] = B2STR_latin2
			elif charname == 'latin5':
				data['decode'] = B2STR_latin5
			elif charname == 'latin7':
				data['decode'] = B2STR_latin7
			elif charname == 'macce':
				data['decode'] = B2STR_macce
			elif charname == 'macroman':
				data['decode'] = B2STR_macroman
			elif charname == 'sjis':
				data['decode'] = B2STR_sjis
			elif charname == 'swe7':
				data['decode'] = B2STR_swe7
			elif charname == 'tis620':
				data['decode'] = B2STR_tis620
			elif charname == 'ucs2':
				data['decode'] = B2STR_ucs2
			elif charname == 'ujis':
				data['decode'] = B2STR_ujis
			elif charname == 'utf16':
				data['decode'] = B2STR_utf16
			elif charname == 'utf16le':
				data['decode'] = B2STR_utf16le
			elif charname == 'utf32':
				data['decode'] = B2STR_utf32
			else: # utf8/utf8mb4
				data['decode'] = B2STR_utf8
		elif data['type_name'] in ['BIT']: # bit
			data['size'] = (data['numeric_precision']+7)//8
			data['decode'] = B2BIT
		elif data['type_name'] in ['ENUM']: # enum
			data['size'] = 2 if len(data['elements']) >= 256 else 1
			data['decode'] = B2ENUM
			data['args'] = (element_b64_format(data['elements']),)
		elif data['type_name'] in ['SET']: # set
			data['size'] = (len(data['elements'])+7)//8
			data['size'] = 8 if data['size'] == 5 else data['size']
			data['decode'] = B2SET
			data['args'] = (element_b64_format(data['elements']),)
		elif data['type_name'] in ['GEOMETRY']: # geometry
			data['decode'] = B2GEOMETRY
			data['args'] = (data['srs_id'],) if 'srs_id' in data else (0,)
		elif data['type_name'] in ['JSON']: # json
			data['decode'] = B2JSON
		elif data['type_name'] in ['VECTOR']: # vector
			data['decode'] = B2VECTOR
		else:
			return {}

		# issue 8  type is char and charset is latin1, will not use varsize
		if data['type'] == 29 and data['character_set_maxlen'] == '1':
			data['size'] = data['char_length']
			data['is_var'] = False
		return data

	def _get_ddl_column(self,ddl_history=False,with_collate=False):
		tddl = ''
		for colid in self.column:
			col = self.column[colid]
			if col['name'] == 'FTS_DOC_ID':
				continue 
			ddl = self._start
			colname_rm = f"_dropped_v{col['version_dropped']}"
			colname_rm2 = f"!hidden!_dropped_v{col['version_dropped']}_p{col['physical_pos']}_"
			colname = col['name']
			if col['version_dropped'] != 66 :
				if colname.endswith(colname_rm):
					colname_len = len(colname) - len(colname_rm)
					colname = colname[:colname_len]
				elif colname.startswith(colname_rm2):
					colname_len = len(colname_rm2)
					colname = colname[colname_len:]
			# column name
			ddl += f"{self._enclosed}{colname}{self._enclosed} "
			# column type
			ddl += f"{col['column_type_utf8'] } "
			# collate
			if with_collate or col['collation_id'] != self.sdi['dd_object']['collation_id']:
				if col['character_set_name'] not in ['latin1','binary']:
					ddl += f"CHARACTER SET {col['character_set_name']} COLLATE {col['collation_name']} "
			# generated & virtual
			if col['generation_expression'] != '':
				generation_expression = auto_col_convert(col['generation_expression'],self.column,col['character_set_name']) if self.mysql_version_id <= 80028 else col['generation_expression']
				ddl += f"GENERATED ALWAYS AS ({generation_expression}) {'VIRTUAL' if col['is_virtual'] else 'STORED'} "
			elif col['type_name'] in ['TINY_BLOB','MEDIUM_BLOB','BLOB','LONG_BLOB']: #  BLOB, TEXT, GEOMETRY or JSON cant't have default
				ddl += "" if col['is_nullable'] else "NOT NULL "
				
			else:
				# null & default
				if col['default_value_null'] and col['default_value_utf8'] == '' and col['is_nullable']:
					ddl += "DEFAULT NULL "
				elif col['default_value_utf8'] == '':
					ddl += "NULL " if col['is_nullable'] else "NOT NULL "
				elif col['default_option'] != '': # default expr
					is_expr = True if col['default_option'].find(')')>=0 else False
					if not is_expr:
						ddl += "NULL " if col['is_nullable'] else "NOT NULL "
					ddl += f"DEFAULT ({col['default_option']}) " if self.mysql_version_id >80012 and is_expr else f"DEFAULT {col['default_option']} "
				else:
					if not col['is_nullable']:
						ddl += "NOT NULL "
					ddl += f"DEFAULT {col['default_value_utf8']} " if col['collation_id'] == 63 or col['type'] == 17 else f"DEFAULT {repr(col['default_value_utf8'])} "
			# srsid
			if not col['srs_id_null']:
				ddl += f"/*!80003 SRID {col['srs_id']} */ "
			# on update
			if col['update_option'] != '':
				ddl += f"ON UPDATE {col['update_option']} "
			# auto_increment
			if col['is_auto_increment']:
				ddl += "AUTO_INCREMENT "
			# visible
			if col['hidden'] == 4:
				ddl += "/*!80023 INVISIBLE */ "
			# comment
			if col['comment'] != '':
				ddl += f"COMMENT {repr(col['comment'])} "
			if colname in ['DB_ROW_ID','DB_TRX_ID','DB_ROLL_PTR']:
				continue
			# SKIP: COLUMN_FORMAT, ENGINE_ATTRIBUTE, SECONDARY_ENGINE_ATTRIBUTE,STORAGE
			if ddl_history:
				table_schema_name = f"{self._enclosed}{self.schema}{self._enclosed}.{self._enclosed}{self.name}{self._enclosed}"
				if col['version_added'] > 0:
					self.ddl_history_list.append([col['version_added'],f"ALTER TABLE {table_schema_name} ADD COLUMN {ddl[2:-1]};"])
				if col['version_dropped'] > 0 and col['version_dropped'] < 66:
					self.ddl_history_list.append([col['version_dropped'],f"ALTER TABLE {table_schema_name} DROP COLUMN {self._enclosed}{colname}{self._enclosed};"])
				if col['version_added'] == 0:
					tddl += ddl[:-1]+",\n"
			elif col['version_dropped'] == 66:
				tddl += ddl[:-1]+",\n"
		return tddl[:-2]

	def init_index(self):
		index = [ self._init_index(idx) for idx in self.sdi['dd_object']['indexes'] ]
		self.index = dict([ (idx['ordinal_position']-1,idx) for idx in index ])

	def _init_index(self,data):
		se_private_data = str2dict(data['se_private_data'])
		options = data['options'] if 'options' in data else {}
		data['gipk'] = True if 'gipk' in options else False
		data['type_name'] = INDEX_TYPE[data['type']]
		data['root'] = se_private_data['root'] if 'root' in se_private_data else 0
		data['space_id'] = se_private_data['space_id'] if 'space_id' in se_private_data else 0
		data['table_id'] = se_private_data['table_id'] if 'table_id' in se_private_data else 0
		data['index_id'] = se_private_data['id'] if 'id' in se_private_data else 0
		data['algorithm_name'] = INDEX_ALG[data['algorithm']]
		data['null_count'] = 0
		data['colid_list'] = []
		tt = {}
		for x in range(len(data['elements'])):
			colid = data['elements'][x]['column_opx']
			col = self.column[colid]
			col_len = col['char_length']
			col_char_max = col['character_set_maxlen']
			idx_len = data['elements'][x]['length']
			#data['elements'][x]['is_pre'] = True if idx_len < col_len and col_len != 4294967295 else False
			if colid in tt: # pre
				data['elements'][x]['is_pre'] = True
				data['elements'][tt[colid]]['is_pre'] = True
			else:
				tt[colid] = x
				if idx_len < col_len and col['is_var']:
					data['elements'][x]['is_pre'] = True
				else:
					data['elements'][x]['is_pre'] = False
			data['elements'][x]['pre_size'] = idx_len//int(col_char_max)
			data['elements'][x]['ordinal_position'] -= 1
			data['null_count'] += 1 if col['is_nullable'] else 0
			data['colid_list'].append(colid)
		return data

	def _get_ddl_index(self,alter=False):
		tddl = ''
		alter_ddl = []
		for idxid in self.index:
			idx = self.index[idxid]
			ddl = self._start
			idx_type_name = INDEX_TYPE[idx['type']]
			if idx_type_name == 'PRIMARY ': # pk'name is PRIMARY
				ddl += f"{idx_type_name}KEY "
			else:
				ddl += f"{idx_type_name}KEY {self._enclosed}{idx['name']}{self._enclosed} "
			e = "("
			for x in idx['elements']:
				if x['length'] == 4294967295:
					continue
				colname = self.column[x['column_opx']]['name']
				isvar = self.column[x['column_opx']]['is_var']
				e += f"{self._enclosed}{colname}{self._enclosed}{'('+str(x['pre_size'])+')' if x['is_pre'] and isvar and self.column[x['column_opx']]['type'] != 30 and idx_type_name !='FULLTEXT ' else ''}"
				if x['order'] == 3: # 2:AESC 3:DESC
					e += " DESC"
				e += ','
			if e == '(': # pk=rowid
				continue
			ddl += e[:-1] + ") "
			if idx['comment'] != "":
				ddl += f"{idx['comment']} "
			if not idx['is_visible']:
				ddl += f"/*!80000 INVISIBLE */ "
			ddl = ddl[:-1]
			if idx_type_name != 'PRIMARY ':
				alter_ddl.append(f"ALTER TABLE {self._enclosed}{self.schema}{self._enclosed}.{self._enclosed}{self.name}{self._enclosed} ADD{ddl};")
			tddl += ddl+",\n"
		return alter_ddl if alter else tddl[:-2] if len(tddl) > 2 else ''

	def _get_ddl_partition(self):
		ddl = ""
		dd = self.sdi
		subpartition_type = PARTITION_TYPE[dd['dd_object']['subpartition_type']]
		partition_type = PARTITION_TYPE[dd['dd_object']['partition_type']]
		if self.mysql_version_id <= 50744: # frm
			ddl = self.sdi['dd_object']['subpartition_expression']
		elif subpartition_type != "": # subpartition
			ddl = SUB_PARTITION(dd['dd_object'])
		elif partition_type != "": # partition
			if partition_type in ['HASH','KEY']:
				ddl = f"/*!50100 PARTITION BY {partition_type} ({dd['dd_object']['partition_expression_utf8']})\nPARTITIONS {len(dd['dd_object']['partitions'])} */"
			else:
				opt = "LESS THAN" if partition_type == "RANGE" else "IN"
				ddl = f"/*!50100 PARTITION BY {partition_type}({dd['dd_object']['partition_expression_utf8']})\n("
				for p in dd['dd_object']['partitions']:
					ddl += f" PARTITION {p['name']} VALUES {opt} ({p['description_utf8']}) ENGINE = {p['engine']},\n"
				ddl = ddl[:-2] + ") */"
		else: # None partition
			pass
		return ddl

	def _get_ddl_reference(self,alter=False):
		foreigns = []
		alter_ddl = ""
		for foreign_keys in self.sdi['dd_object']['foreign_keys']:
			foreign_key_name = foreign_keys['name']
			ref_schema_name = foreign_keys['referenced_table_schema_name']
			ref_table_name = foreign_keys['referenced_table_name']
			ref_schem_table = '' if self.sdi['dd_object']['schema_ref'] == ref_schema_name else f"{self._enclosed}{ref_schema_name}{self._enclosed}."
			ref_schem_table += f"{self._enclosed}{ref_table_name}{self._enclosed} "
			ref_column_name = f"{','.join([ self._enclosed+x['referenced_column_name']+self._enclosed for x in foreign_keys['elements']])}"
			foreign_column_name = f"{','.join([ self._enclosed+str(self.column[x['column_opx']]['name'])+self._enclosed for x in foreign_keys['elements']])}"
			reference_option = '' # 1:None 2:RESTRICT 3:CASCADE
			if foreign_keys['delete_rule'] == 2:
				reference_option = ' ON DELETE RESTRICT'
			elif foreign_keys['delete_rule'] == 3:
				reference_option = ' ON DELETE CASCADE'
			elif foreign_keys['update_rule'] == 2:
				reference_option = ' ON UPDATE RESTRICT'
			elif foreign_keys['update_rule'] == 3:
				reference_option = ' ON UPDATE CASCADE'
			else:
				reference_option = ''
			foreign = f"{self._start}CONSTRAINT {self._enclosed}{foreign_key_name}{self._enclosed} FOREIGN KEY ({foreign_column_name}) REFERENCES {ref_schem_table}({ref_column_name}){reference_option}"
			foreigns.append(foreign) 
			alter_ddl += f"ALTER TABLE {self._enclosed}{self.schema}{self._enclosed}.{self._enclosed}{self.name}{self._enclosed} ADD {foreign};\n"
		return ",\n".join([ x for x in foreigns ]) if not alter else alter_ddl

	def _get_ddl_check(self,alter=False):
		dd = self.sdi
		if "check_constraints" in dd['dd_object']: #for mysql 8.0.12
			check = []
			alter_ddl = ''
			for chk in dd['dd_object']['check_constraints']:
				#chkv = base64.b64decode(chk['check_clause']).decode()
				chkv = chk['check_clause_utf8']
				check.append(f"{self._start}CONSTRAINT {self._enclosed}{chk['name']}{self._enclosed} CHECK ({chkv})")
				alter_ddl += f"ALTER TABLE {self._enclosed}{self.schema}{self._enclosed}.{self._enclosed}{self.name}{self._enclosed} ADD {check[-1]}"
			return ",\n".join([ x for x in check ]) if not alter else alter_ddl
		else:
			return ''

	def _get_ddl_options(self):
		dd = self.sdi
		comment = dd['dd_object']['comment']
		options = str2dict(dd['dd_object']['options'])
		se_private_data = str2dict(dd['dd_object']['se_private_data'])
		row_format = f" ROW_FORMAT={ROW_FORMAT[dd['dd_object']['row_format']]}" if dd['dd_object']['row_format'] >= 3 else ''
		compression = f" COMPRESSION={repr(options['compress'])}" if 'compress' in options else '' 
		auto_inc = f" AUTO_INCREMENT={int(se_private_data['autoinc'])+1}" if 'autoinc' in se_private_data else ''
			
		stats = ''
		if 'stats_persistent' in options:
			stats += f" STATS_PERSISTENT={options['stats_persistent']}"
		if 'stats_auto_recalc' in options and options['stats_auto_recalc'] == 1: # stats_auto_recalc enable
			stats += f" STATS_AUTO_RECALC=1"
		if 'stats_auto_recalc' in options and options['stats_auto_recalc'] == 2: # stats_auto_recalc disabled
			stats += f" STATS_AUTO_RECALC=0"
		if 'stats_sample_pages' in options and int(options['stats_sample_pages']) > 0:
			stats += f" STATS_SAMPLE_PAGES={options['stats_sample_pages']}"
		ddl = f"ENGINE={dd['dd_object']['engine']}{auto_inc} DEFAULT CHARSET={self.character_set_name} COLLATE={self.collation_name}{' COMMENT '+repr(comment) if comment !='' else ''}{stats}{compression}{row_format}" # encrypt_type:PASS
		return ddl

	def get_ddl(self,ddl_history=False,disable_key=False,disable_foreign_key=False):
		"""
		disable_key: without key info
		history_ddl: history ddl
		"""
		ddl = self._pre + f"{self._enclosed}{self.schema}{self._enclosed}.{self._enclosed}{self.name}{self._enclosed} " + "(\n" + self._get_ddl_column(ddl_history)
		index = self._get_ddl_index(disable_key)
		if index != '' and not disable_key:
			ddl += ",\n" + index
		reference = self._get_ddl_reference(disable_foreign_key)
		if reference != '' and not disable_foreign_key:
			ddl += ",\n" + reference
		check = self._get_ddl_check()
		if check != '':
			ddl += ",\n" + check
		ddl += "\n) " + self._get_ddl_options()
		partition = self._get_ddl_partition()
		if partition != '':
			ddl += "\n" + partition
		ddl += ";"
		return ddl
		
	def get_ddl_reference(self,disable_foreign_key=True):
		return self._get_ddl_reference(disable_foreign_key)

	def get_ddl_key(self):
		"""
		return `ALTER TABLE ADD INDEX` statement if have index
		"""
		return "\n".join(self._get_ddl_index(True)) + "\n"

	def get_ddl_history(self,ddl_history=False,disable_key=False,disable_foreign_key=False):
		ddl = self.get_ddl(ddl_history,disable_key,disable_foreign_key) + "\n"
		his_ddl = self.ddl_history_list
		his_ddl.sort()
		ddl += "\n".join([ x[1] for x in his_ddl ])
		return ddl

	def init_pkmr(self):
		"""
		when mysql_version_id <= 8.0.28:
			使用Instant新增字段时, 一定是放在最后的

		when mysql_version_id > 8.0.28:
			ADD/DROP INSTANT时, 有physical_pos 来确定当前/之前的位置
			实际上普通字段也有这个
		mr: [
			0: [key,剩余部分, 可为空的数量,ispk] 注意前缀索引
			1: [key,剩余部分, 可为空的数量,ispk]
			2: [key,剩余部分, 可为空的数量,ispk]
		]
		"""
		pk = []
		prepk = []
		index = self.index[0]
		for x in index['elements']:
			if x['length'] < 4294967295 and not x['hidden']:
				pk.append(x['column_opx'])
			if x['is_pre']:
				prepk.append(x['column_opx'])
		self.pk = [index['elements'][0]['column_opx']] if pk == [] else pk 

		pkmr = {}
		#print(self.max_row_version,self.column[self.pk[0]]['name'],self.column[self.pk[1]]['name'])
		for row_version in range(self.max_row_version+1):
			pkmr[row_version] = {}
			null_count = 0
			colid_list = []
			for colid in self.column:
				col = self.column[colid]
				if (colid in self.pk and colid not in prepk) or col['name'] in ['DB_TRX_ID','DB_ROLL_PTR']:
					continue
				elif col['version_added'] <= row_version and row_version < col['version_dropped']:
					null_count += 1 if col['is_nullable'] else 0
					colid_list.append([col['physical_pos'],colid,col['name']])
			colid_list.sort() # for physical_pos
			#colid_list2 = [ [self.col_trxid,"DB_TRX_ID"],[self.col_rollptr,"DB_ROLL_PTR"] ] + [ [x[1],x[2]] for x in colid_list ]
			#colid_list2 = [ self.col_trxid,self.col_rollptr ] + [ x[1] for x in colid_list ]
			colid_list2 = [ x[1] for x in colid_list ]
			if self.row_format == 'REDUNDANT':
				colid_list2 = [self.col_trxid,self.col_rollptr] + colid_list2
			pkmr[row_version] = {"colid":colid_list2,"null_count":null_count}
		if self.max_row_version > 0 and self.mysql_version_id <= 80028: # 8.0.28 instant
			pkmr = {}
			isfirstrow = True
			for row_version in range(self.max_row_version+1):
				baserow = []
				null_count = 0
				for colid in self.column:
					col = self.column[colid]
					if (colid in self.pk and colid not in prepk) or col['name'] in ['DB_TRX_ID','DB_ROLL_PTR'] or col['version_added'] > row_version:
						continue
					baserow.append(colid)
					null_count += 1 if col['is_nullable'] else 0
			#	print(row_version,baserow)
				if isfirstrow:
					pkmr[0] = {"colid":baserow,"null_count":null_count}
					isfirstrow = False
				pkmr[len(baserow)+2+len(self.pk)] = {"colid":baserow,"null_count":null_count}
		self.pkmr = pkmr		
		#import json
		#print(json.dumps(pkmr))
		#exit(1)

	def init_pk_null_count(self):
		self.pk_null_count = 0
		for colid in self.column:
			col = self.column[colid]
			if col['version_added'] == 0 and col['version_dropped'] == 66 and col['is_nullable']:
				self.pk_null_count += 1
