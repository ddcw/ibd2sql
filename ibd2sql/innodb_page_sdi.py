from ibd2sql.innodb_page import *
from ibd2sql.COLLATIONS import COLLID_TO_CHAR
import struct,json,zlib
from ibd2sql.innodb_type import innodb_type_isvar
import base64
from ibd2sql.partition import subpartition
import sys


class TABLE(object):
	def __init__(self):
		#表的基础信息
		self.schema = ''
		self.table_name = ''
		self.column = {} #NAME,TYPE,VISIBLE ..
		self.index = {}   #PK,KEY,FOREIGN KEY, UK(not in SDI)
		self.check = [] #约束 CONSTRAINT
		self.foreign = [] #外键
		self.table_options = {}
		self.partitions = "" #only for one level
		#self.nullable = True #是否有空值 判断null bitmask要
		self._ci = "    " #4个空格开头(for column and index) pretty
		self.cluster_index_id = None #cluster index的id, 空表示没得主键, 使用的rowid(6 bytes)
		self.uindex_id = []
		self.have_null = False #标记这张表是否有null字段
		self.have_null_instant = False #标记这张表是否有null字段
		self.null_bitmask_count = 0 #可为空的字段数量
		self.null_bitmask_count_instant = 0#可为空的字段数量
		self.instant = False #是否有过instant online DDL
		self.instant_list = [] #

		#可禁用一些功能, 比如外键
		self.FOREIGN = True
		self.ENCRYPTION = True
		self.AUTO_EXTEND = True
		self.COLUMN_COLL = True #解析字段的排序规则/字符集 
		self.COLLATION = True #表的排序规则还是要的
		self.HAS_EXIST = True #是否有has exist
		self.CONSTRAINT = True #支持约束
		self.PARTITIONS = True #支持分区
		self.row_format = "DYNAMIC"
		self.mysqld_version_id = 80028

	def _set_name(self,):
		self.name = f"`{self.schema}`.`{self.table_name}`"

	def get_name(self):
		self._set_name()
		return self.name

	def remove_virtual_column(self,):
		"""
		把虚拟列去掉, 目前不支持虚拟列 (获取数据前 请删掉虚拟字段, 不然虚拟列会出现一些错误的数据)
		"""
		column = {}
		for colno in self.column:
			if self.column[colno]['is_virtual']:
				#self.debug(f"remove virtual column {self.column[column]['name']}")
				continue
			column[colno] = self.column[colno]
		self.column = column
		
	def get_ddl(self):
		self._set_name()
		ddl = f"CREATE TABLE{' IF NOT EXISTS' if self.HAS_EXIST else ''} {self.name}(\n"
		ddl += self._column()
		idx = self._index()
		ddl += ",\n" + idx if idx != '' else ''
		if self.FOREIGN:
			fgk = self._foreign_keys()
			ddl += ",\n" + fgk if fgk != '' else ''
		chk = self._check()
		ddl += ",\n" + chk if chk != '' else ''
		ddl += "\n) "
		ddl += self._options()
		if self.PARTITIONS and self.partitions != "":
			ddl += "\n" + self._partitions()
		ddl += ";"
		#self.remove_virtual_column()
		return ddl

	def _column(self):
		ddl = ""
		for colid in self.column:
			if self.column[colid]['name'] == 'FTS_DOC_ID':
				continue
			if self.column[colid]['version_dropped'] > 0:
				continue
			ddl += self._ci
			col = self.column[colid]
			ddl += f"`{col['name']}` {col['type']}" #column name
			if self.COLUMN_COLL and col['type'] != 'int' and (self.table_options['charset'] != col['character_set']) and col['isvar'] and col['type'][:7] == 'varchar':
				ddl += f" CHARACTER SET {col['character_set']} COLLATE {col['collation']}"
			if col['srs_id'] > 0:
				ddl += f" /*!80003 SRID {col['srs_id']} */"
			if not col['is_virtual']:# and col["default_option"] == "":
				ddl += f"{' NOT' if not col['is_nullable'] else ''} NULL" #nullabel
			else:
				#虚拟列 VIRTUAL 
				ddl += f"{' GENERATED ALWAYS AS (' + col['generation_expression'] + ') VIRTUAL' if col['is_virtual'] else '' }"
			if col["default_option"] != "":
				#ddl += f" DEFAULT ({col['default_option']})"
				ddl += f" DEFAULT ({col['default_option']})" if self.mysqld_version_id > 80012 else f" DEFAULT {col['default_option']}"
			else:
				ddl += f"{' DEFAULT '+repr(col['default']) if col['have_default'] else ''}" #default
			ddl += f"{' AUTO_INCREMENT' if col['is_auto_increment'] else ''}" #auto_increment
			ddl += f"{' ON UPDATE '+col['update_option'] if 'update_option' in col and col['update_option']!='' else ''}"
			ddl += f"{' COMMENT '+repr(col['comment']) if col['comment'] != '' else '' }" #comment
			#COLUMN_FORMAT 
			#STORAGE 
			#SECONDARY_ENGINE_ATTRIBUTE 
			ddl += ",\n"
		return ddl[:-2] #去掉',\n'

	def _index(self):
		ddl = ""
		for idxid in self.index:
			ddl += self._ci
			idx = self.index[idxid]
			ddl += idx['idx_type'] + "KEY "
			ddl += f"`{idx['name']}` " if idx['name'] else ' '
			ddl += "(" +     ",".join( [ f"`{self.column[x[0]]['name']}`{'' if x[1] == 0 else '('+str(x[1])+')'} {'DESC' if x[2] == 3 else ''}" for x in idx['element_col'] ] )   + ")"
			#ddl += "(" +     ",".join( [ f"`{self.column[x[0]]['name']}`" for x in idx['element_col'] ] )   + ")" #不考虑前缀索引
			ddl += " COMMENT " + repr(idx['comment']) if idx['comment'] != "" else ''
			if not idx['is_visible']:
				ddl += " /*!80000 INVISIBLE */"
			ddl += ",\n"
		return ddl[:-2]

	def _check(self):
		ddl = ''
		for chk in self.check:
			ddl += self._ci + chk + ",\n"
		return ddl[:-2]

	def _partitions(self):
		#/*!50100 PARTITION xxx */
		return self.partitions

	def _foreign_keys(self):
		ddl = ''
		for fgk in self.foreign:
			ddl += self._ci + fgk + ",\n"
		return ddl[:-2]

	def _options(self):
		ddl = ''
		ddl += f"ENGINE={self.table_options['engine']}"
		if self.COLLATION:
			ddl += f" DEFAULT CHARSET={self.table_options['charset']} COLLATE={self.table_options['collate']}"
		ddl += f" {' COMMENT '+repr(self.table_options['comment']) if self.table_options['comment'] != '' else ''}"
		# FOR COMPRESS
		ddl += f"{' COMPRESSION='+repr(self.table_options['compress']) if 'compress' in self.table_options else ''}"
		return ddl

class sdi(page):
	"""
         |---> FIL_HEADER       38 bytes
         |---> PAGE_HEADER      56 bytes
SDI_PAGE-|---> INFIMUM          13 bytes
         |---> SUPEREMUM        13 bytes
         |---> SDI_DATA         xx
         |---> PAGE_DIRECTORY   xx
         |---> FIL_TRAILER      8 bytes
	"""
	def __init__(self,*args,**kwargs):
		super().__init__(*args,**kwargs)
		if self.FIL_PAGE_TYPE != 17853:
			return None
		self.page_name = 'SDI'
		self.filename = kwargs['filename']

		self.HAS_IF_NOT_EXISTS = True
		self.table = TABLE() #初始化一个表对象
		self._init_table()
		self.table._set_name()

	def _init_table(self):
		"""
		初始化表对象
		"""
		dd = self.get_dict()
		self.table.schema = dd['dd_object']['schema_ref']
		self.table.table_name = dd['dd_object']['name']

		column = {}
		nullable = False #是否有空值
		null_bitmask_count = 0
		null_bitmask_count_instant = 0
		#1:不是索引,  2:主键索引  3:唯一索引  4:普通索引
		idx_type = {1:'NONE', 2:'PK', 3:'UK', 4:'SK'}
		for col in dd['dd_object']['columns']:
			if col['name'] in ['DB_TRX_ID','DB_ROLL_PTR','DB_ROW_ID']:
				continue
			#if col['name'][:17] == '!hidden!_dropped_': #"options": "gipk=1;interval_count=0;"
			#	continue # issue 19  被删除的字段就不要了
			#if col['name'] == 'DB_ROW_ID':
			#	self.table.pk = False
			coll_id = col['collation_id']
			ct,isvar,size,isbig,elements_dict,varsize,extra = innodb_type_isvar(col)
			se_private_data  = {}
			for x in col['se_private_data'].split(";"):
				if x == '':
					continue
				xk,xv = x.split('=')
				se_private_data[xk] = xv

			#INSTANT
			se_private_data_default_value = ''
			col_instant = False
			nullable_instant = False
			instant_null = True
			if 'default_null' in se_private_data:
				se_private_data_default_value = None
				col_instant = True
				self.table.instant = True
				self.table.instant_list.append(col['ordinal_position'])
				instant_null = True
			elif 'default' in se_private_data:
				#se_private_data_default_value = se_private_data['default']
				se_private_data_default_value = col['default_value_utf8']
				col_instant = True
				self.table.instant = True
				self.table.instant_list.append(col['ordinal_position'])
				instant_null = False

			physical_pos = int(se_private_data['physical_pos']) if 'physical_pos' in se_private_data else col['ordinal_position']
			version_dropped = int(se_private_data['version_dropped']) if 'version_dropped' in se_private_data else 0
			version_added = int(se_private_data['version_added']) if 'version_added' in se_private_data else 0

			#NULLABLE
			if col['is_nullable']  and not col_instant: #instant的不需要使用null bitmask. 因为本来就自带默认值
				nullable = True
				null_bitmask_count += 1
			if col['is_nullable'] and col_instant:
				null_bitmask_count_instant += 1
				nullable_instant = True

			column[col['ordinal_position']] = {
				'name':col['name'],
				'is_autoincrement':col['is_auto_increment'],
				'type':col['column_type_utf8'],
				'isvar':isvar,
				'size':size,
				'isbig':isbig,
				'elements_dict':elements_dict,
				'varsize':varsize,
				'have_default':False if col['default_value_utf8_null'] else True,
				'default':col['default_value_utf8'],
				'comment':col['comment'],
				'collation':COLLID_TO_CHAR[coll_id][1],
				'character_set':COLLID_TO_CHAR[coll_id][0],
				'index_type':idx_type[col['column_key']],
				'is_nullable':col['is_nullable'],
				'is_zerofill':col['is_zerofill'],
				'is_unsigned':col['is_unsigned'],
				'is_auto_increment':col['is_auto_increment'],
				'is_virtual':col['is_virtual'],
				'hidden':col['hidden'],
				'char_length':col['char_length'], #作为字符串的最大长度
				'extra':extra,
				'instant':col_instant,
				'instant_value':se_private_data_default_value,
				'instant_null':instant_null,
				'generation_expression':col['generation_expression'],
				'default_option':col['default_option'],
				'collation_id':col['collation_id'],
				'srs_id':col['srs_id'],
				'version_dropped':version_dropped,
				'version_added':version_added,
				'physical_pos':physical_pos,
				'update_option':col['update_option'] if 'update_option' in col else '',
				'ct':ct #属于类型
			}
		column_ph = []
		for _xx in column:
			column_ph.append([column[_xx]['physical_pos'],_xx])
		column_ph.sort()
		self.table.column = column
		self.table.column_ph = column_ph
		self.table.have_null = nullable
		#self.table.have_null_instant = nullable_instant
		self.table.null_bitmask_count = null_bitmask_count
		self.table.null_bitmask_count_instant = null_bitmask_count_instant


		index = {}
		for idx in dd['dd_object']['indexes']:
			# issue 35
			is_visible = False if 'is_visible' in idx and (not idx['is_visible']) else True
			element_col = []
			comment = idx['comment'] 
			hidden = idx['hidden']
			for x in idx['elements']:
				if x['length'] == 4294967295: #fix issue 10 (mysql 8.0.12 has not hidden attr in index_metadata)
					continue
				#判断前缀索引
				prefix_key = 0
				if self.table.column[x['column_opx']+1]['isvar']:
					_varlen = 4 if self.table.column[x['column_opx']+1]['collation_id'] == 255 else 3 if self.table.column[x['column_opx']+1]['ct'] in ['varchar','char','varbinary'] and self.table.column[x['column_opx']+1]['type'][:4] != "varb" else 1
					if self.table.column[x['column_opx']+1]['char_length'] > x['length']:
						prefix_key = int(x['length']/_varlen)
				xorder = x['order'] if 'order' in x else 0
				if self.table.column[x['column_opx']+1]['ct'] == 'geom':
					prefix_key = 0
				element_col.append((x['column_opx']+1,prefix_key,xorder)) # order 是否为降序索引 
				#/*column[ordinal_position] 从1开始计数,   idx['column_opx'] 从0开始计*/
			if len(element_col) == 0:
				continue #没得k
			if idx['type'] == 1:
				idx_type = 'PRIMARY '
				self.table.cluster_index_id = idx['ordinal_position'] #设置主键
			elif idx['type'] == 2:
				idx_type = 'UNIQUE '
				self.table.uindex_id.append(idx['ordinal_position'])
			elif idx['type'] == 4:
				idx_type = 'FULLTEXT '
			elif idx['type'] == 5:
				idx_type = 'SPATIAL '
			else:
				idx_type = ''
			name = idx['name'] if idx['name'] != "PRIMARY" else None
			_options = {}
			for x in idx['se_private_data'].split(';')[:-1]:
				xk,xv = x.split('=')
				_options[xk] = xv
			index[idx['ordinal_position']] = {
				'name':name,#只有主键没得名字
				'comment':comment,
				'idx_type':idx_type,
				'element_col':element_col,
				'options':_options,
				'is_visible':is_visible
			}
		self.table.index = index

		#不会使用唯一索引作为cluster index
		#if not self.table.cluster_index_id:
		#	self.table.cluster_index_id = self.table.uindex_id[0] if len(self.table.uindex_id) > 0 else None

		#FOREIGN KEY
		foreign = []
		for fgk in dd['dd_object']['foreign_keys']:
			fkid = f"{','.join([ '`'+x['referenced_column_name']+'`' for x in fgk['elements']])}"
			localcol = f"{','.join([ '`'+str(self.table.column[x['column_opx']+1]['name'])+'`' for x in fgk['elements']])}" # issue 57
			# 1:None 2:RESTRICT 3:CASCADE
			foreign.append(f"CONSTRAINT `{fgk['name']}` FOREIGN KEY ({localcol}) REFERENCES `{fgk['referenced_table_schema_name']}`.`{fgk['referenced_table_name']}` ({fkid}){' ON DELETE RESTRICT' if fgk['delete_rule'] == 2 else ''}{' ON DELETE CASCADE' if fgk['delete_rule'] == 3 else ''}{' ON UPDATE CASCADE' if fgk['update_rule'] == 3 else ''}{' ON UPDATE RESTRICT' if fgk['update_rule'] == 2 else ''}") # issue 57
		self.table.foreign = foreign

		#CONSTRAINT CHECK
		check = []
		if "check_constraints" in dd['dd_object']: #for mysql 8.0.12
			for chk in dd['dd_object']['check_constraints']:
				chkv = base64.b64decode(chk['check_clause']).decode()
				check.append(f"CONSTRAINT `{chk['name']}` CHECK {chkv}")
		self.table.check = check
		

		#PARTITIONS
		pt = ""
		if   dd['dd_object']['partition_type'] == 0:#非分区
			pass
		elif dd['dd_object']['partition_type'] == 8: #list分区
			pt = f"/*!50100 PARTITION BY LIST({dd['dd_object']['partition_expression_utf8']})\n("
			for p in dd['dd_object']['partitions']:
				pt += f" PARTITION {p['name']} VALUES IN ({p['description_utf8']}) ENGINE = {p['engine']},\n"
			pt = pt[:-2] +  ") */"
		elif dd['dd_object']['partition_type'] == 7: #range分区
			pt = f"/*!50100 PARTITION BY RANGE({dd['dd_object']['partition_expression_utf8']})\n("
			for p in dd['dd_object']['partitions']:
				pt += f" PARTITION {p['name']} VALUES LESS THAN ({p['description_utf8']}) ENGINE = {p['engine']},\n"
			pt = pt[:-2] +  ") */"
		elif dd['dd_object']['partition_type'] == 3: #key分区
			pt = f"/*!50100 PARTITION BY KEY ({dd['dd_object']['partition_expression_utf8']})\nPARTITIONS {len(dd['dd_object']['partitions'])} */"
		elif dd['dd_object']['partition_type'] == 1: #hash分区
			pt = f"/*!50100 PARTITION BY HASH ({dd['dd_object']['partition_expression_utf8']})\nPARTITIONS {len(dd['dd_object']['partitions'])} */"
		else: #不支持其它分区了(就4种: https://dev.mysql.com/doc/refman/8.0/en/partitioning-types.html)
			pass
		#self.table.partitions = pt
		#self.table.partitions = pt if dd['dd_object']['subpartition_type'] == 0 else subpartition(dd['dd_object']) # for subpartition
		if dd['dd_object']['subpartition_type'] == 0 and dd["mysqld_version_id"] > 50744:
			self.table.partitions = pt
		elif dd["mysqld_version_id"] > 50744:
			self.table.partitions = subpartition(dd['dd_object'])
		elif dd["mysqld_version_id"] <= 50744:
			self.table.partitions = dd['dd_object']['subpartition_expression']


		table_options = {}
		table_options['engine'] = dd['dd_object']['engine']
		for x in dd['dd_object']['options'].split(';')[:-1]:
			xk,xv = x.split('=')
			table_options[xk] = xv
		table_options['comment'] = dd['dd_object']['comment']
		coll_id = dd['dd_object']['collation_id']
		table_options['charset'] = COLLID_TO_CHAR[coll_id][0]
		table_options['collate'] = COLLID_TO_CHAR[coll_id][1]
		#table_options['se_private_data'] = dd['dd_object']['se_private_data'] #instant_col 做过ONLIE DDL的字段
		self.table.table_options = table_options
		self.table.mysqld_version_id = dd["mysqld_version_id"]
		if dd['dd_object']['row_format'] == 3:
			self.table.row_format = "COMPRESSED"
		elif dd['dd_object']['row_format'] == 4:
			self.table.row_format = "REDUNDANT"
		elif dd['dd_object']['row_format'] == 5:
			self.table.row_format = "COMPACT"
		elif dd['dd_object']['row_format'] == 2:
			self.table.row_format = "DYNAMIC"
		else:
			self.table.row_format = "Unknown"





	def get_ddl(self):
		"""
		返回表的DDL 参考:https://dev.mysql.com/doc/refman/8.0/en/create-table.html
		"""
		self._init_table()
		return self.table.get_ddl()

	def get_dict(self):
		"""
		返回SDI信息(dict). (读一行数据)
		"""
		offset = struct.unpack('>h',self.bdata[PAGE_NEW_INFIMUM-2:PAGE_NEW_INFIMUM])[0] + PAGE_NEW_INFIMUM
		dtype,did = struct.unpack('>LQ',self.bdata[offset:offset+12])
		dtrx = int.from_bytes(self.bdata[offset+12:offset+12+6],'big')
		dundo = int.from_bytes(self.bdata[offset+12+6:offset+12+6+7],'big')
		dunzip_len,dzip_len = struct.unpack('>LL',self.bdata[offset+33-8:offset+33])
		#if dzip_len + offset > len(self.bdata) or dzip_len > len(self.bdata)//2: # 列太多
		if self.bdata[offset-5-2:offset-5] == (b'\x14' + struct.pack('>B',128+16384//256)):
			unzbdata = b''
			SPACE_ID,PAGENO,BLOB_HEADER,REAL_SIZE = struct.unpack('>3LQ',self.bdata[offset+33:offset+33+20])
			if REAL_SIZE != dzip_len:
				print('REAL_SIZE != dzip_len')
				sys.exit(1)
			with open(self.filename,'rb') as f:
				while True:
					f.seek(PAGENO*16384,0)
					data = f.read(16384)
					REAL_SIZE,PAGENO = struct.unpack('>LL',data[38:46])
					unzbdata += data[46:-8]
					if PAGENO == 4294967295:
						break
			unzbdata = zlib.decompress(unzbdata)
		else:
			unzbdata = zlib.decompress(self.bdata[offset+33:offset+33+dzip_len])
		dic_info = json.loads(unzbdata.decode())
		return dic_info if len(unzbdata) == dunzip_len else {}


	def get_columns(self):
		"""
		返回字段信息dict, 字段名字, 大小, 是否可变长, 是否可为空, 默认值等
		"""
		return self.table.column
