#解析sdi page
#storage/innobase/dict/dict0crea.cc

#STRUCT:
#FIL_HEADER 38
#PAGE_HEADER 56
#INFIMUM 13 (5+8) rec_header的最后两字节指向 sdi数据位置

import struct,json,zlib

PAGE_NEW_INFIMUM = 99

PAGE_SIZE = 16384
class sdi(object):
	def __init__(self,tdata):
		bdata = tdata
		if len(tdata) != PAGE_SIZE:
			with open(tdata,'rb') as f:
				f.seek(PAGE_SIZE*3,0)
				bdata = f.read(PAGE_SIZE)
		self.bdata = bdata
		self.dic_info = None
		self.HAS_NULL = True #设置空值 for ddl
		self.HAS_DEFAULT = True #设置默认值 for ddl
		self.HAS_COMMENT = True #设置注释
		self.HAS_IF_NOT_EXISTS = False #不要create table if not exists

	def get_index(self,):
		return self.get_dic()['dd_object']['indexes']

	def get_columns(self,):
		return self.get_dic()['dd_object']['columns']

	def get_version(self,):
		return self.get_dic()['mysqld_version_id']

	def get_name(self,):
		dic_info = self.get_dic()
		return f"{dic_info['dd_object']['schema_ref']}.{dic_info['dd_object']['name']}"

	def get_ddl(self):
		dic_info = self.get_dic()
		columns = dic_info['dd_object']['columns']
		indexes = dic_info['dd_object']['indexes']
		dd_object_type = dic_info['dd_object_type']
		schema = dic_info['dd_object']['schema_ref']
		engine = dic_info['dd_object']['engine']
		comment = dic_info['dd_object']['comment']
		foreign_keys = None #不支持外键
		name = dic_info['dd_object']['name']

		ddl = f"CREATE {dd_object_type} {'IF NOT EXISTS' if self.HAS_IF_NOT_EXISTS else '' } {schema}.{name}"
		cols = ''
		coll = {}
		for col in columns:
			if col['name'] in ['DB_TRX_ID','DB_ROLL_PTR','DB_ROW_ID']:
				continue
			coll[col['ordinal_position']-1] = col['name']
			cols += f"\n{col['name']} {col['column_type_utf8']} {'NULL' if col['is_nullable'] else 'NOT NULL' if self.HAS_NULL else ''} { col['default_value_utf8'] if self.HAS_DEFAULT else '' } { col['comment'] if self.HAS_COMMENT else ''},"
		indexl = []
		for i in indexes:
			index_name = "PRIMARY KEY" if i['name'] == 'PRIMARY' else f"KEY {i['name']}"
			idxl = []
			for x in i['elements']:
				if x['length'] < 4294967295:
					idxl.append(x['column_opx'])
			if len(idxl) == 0:
				continue
			indexl.append(f'{index_name}({",".join([ coll[x] for x in idxl ])})')
		index = ",".join([ x for x in indexl ])
		col_index = f"{cols}\n{index}" if len(index) > 0 else f"{cols[:-1]}"
		ddl = f"{ddl}({col_index}) ENGINE={engine} {comment if self.HAS_COMMENT else ''};"

		return ddl

	def get_dic(self):
		offset = struct.unpack('>H',self.bdata[PAGE_NEW_INFIMUM-2:PAGE_NEW_INFIMUM])[0] + PAGE_NEW_INFIMUM
		dtype,did = struct.unpack('>LQ',self.bdata[offset:offset+12])
		dtrx = int.from_bytes(self.bdata[offset+12:offset+12+6],'big')
		dundo = int.from_bytes(self.bdata[offset+12+6:offset+12+6+7],'big')
		dunzip_len,dzip_len = struct.unpack('>LL',self.bdata[offset+33-8:offset+33]) 

		unzbdata = zlib.decompress(self.bdata[offset+33:offset+33+dzip_len])
		dic_info = json.loads(unzbdata.decode())
		return dic_info if len(unzbdata) == dunzip_len else {}
		
