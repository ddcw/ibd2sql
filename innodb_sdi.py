#@ddcw
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

	def get_ddl(self,HAS_IF_NOT_EXISTS=True):
		dic_info = self.get_dic()
		columns = dic_info['dd_object']['columns']
		indexes = dic_info['dd_object']['indexes']
		dd_object_type = dic_info['dd_object_type']
		schema = dic_info['dd_object']['schema_ref']
		engine = dic_info['dd_object']['engine']
		comment = dic_info['dd_object']['comment']
		foreign_keys = dic_info['dd_object']['foreign_keys']
		check_constraints = dic_info['dd_object']['check_constraints']
		partitions = dic_info['dd_object']['partitions']
		name = dic_info['dd_object']['name']
		ddl = f"CREATE {dd_object_type} {'IF NOT EXISTS' if HAS_IF_NOT_EXISTS else '' } `{schema}`.`{name}`("
		#列
		cols = '' #记录列信息
		coll = {} #记录列的位置 (索引是记录位置的, 所以这里要把位置和名字的对应关系页记录下)
		for col in columns:
			if col['name'] in ['DB_TRX_ID','DB_ROLL_PTR','DB_ROW_ID']:
				continue #跳过不相干的COL
			coll[col['ordinal_position']-1] = col['name']
			cols += f"\n`{col['name']}` {col['column_type_utf8']} "
			#判断空
			cols += "DEFAULT NULL " if col['is_nullable'] else "NOT NULL "

			#判断是否有符号(column_type_utf8包含了有无符号)
			#cols += "UNSIGNED " if col['is_unsigned'] else ""

			#判断是否填充0 (The ZEROFILL attribute is deprecated and will be removed in a future release. Use the LPAD function to zero-pad numbers, or store the formatted numbers in a CHAR column)
			#cols += "ZEROFILL " if col['is_zerofill'] else ""

			#engine_attribute
			#cols += f"ENGINE_ATTRIBUTE {col['engine_attribute']} " if col['engine_attribute'] !='' else ""
			#自增
			cols += "AUTO_INCREMENT " if col['is_auto_increment'] else ""
			#默认值
			cols += f"DEFAULT {str(col['default_value_utf8'])} " if col['default_value_utf8'] != '' else ""
			#注释
			if col['comment'] != '':
				cols += f"COMMENT '{col['comment']}' "
			cols += ","
		ddl += cols

		#索引
		index = ''
		for i in indexes:
			index_name = "\nPRIMARY KEY" if i['name'] == 'PRIMARY' else f"\nKEY `{i['name']}`"
			idxl = ''
			for x in i['elements']:
				if x['length'] < 4294967295:
					#idxl.append(x['column_opx'])
					idxl += f"`{coll[x['column_opx']]}`,"
			if len(idxl) == 0:
				continue
			index += f"{index_name} ({idxl[:-1]}),"
		if len(index) > 0:
			ddl += index

		#外键 (delete_rule,delete_rule 还未做,elements只支持一个)
		forg = ''
		for i in foreign_keys:
			forg += "\nCONSTRAINT `" + i["name"] + "` FOREIGN KEY " + f"(`{coll[i['elements'][0]['column_opx']]}`)" + f" REFERENCES `{i['referenced_table_schema_name']}`.`{i['referenced_table_name']}` (`{i['elements'][0]['referenced_column_name']}`),"
		if len(forg) > 0:
			ddl += forg

		#约束
		check_con = ''
		for i in check_constraints:
			check_con += "\nCONSTRAINT `" + i['name'] + "` CHECK(" + i['check_clause_utf8'] + "),"
		if len(check_con) > 0:
			ddl += check_con
		

		#表选项
		ddl = ddl[:-1] + "\n)"
		ddl += f"ENGINE={engine} "
		if comment != '':
			ddl += f"COMMENT='{comment}' " 
		
		#分区信息 TODO (还有子分区...)

		#返回DDL
		return ddl+";"

	def get_dic(self):
		offset = struct.unpack('>H',self.bdata[PAGE_NEW_INFIMUM-2:PAGE_NEW_INFIMUM])[0] + PAGE_NEW_INFIMUM
		dtype,did = struct.unpack('>LQ',self.bdata[offset:offset+12])
		dtrx = int.from_bytes(self.bdata[offset+12:offset+12+6],'big')
		dundo = int.from_bytes(self.bdata[offset+12+6:offset+12+6+7],'big')
		dunzip_len,dzip_len = struct.unpack('>LL',self.bdata[offset+33-8:offset+33]) 

		unzbdata = zlib.decompress(self.bdata[offset+33:offset+33+dzip_len])
		dic_info = json.loads(unzbdata.decode())
		return dic_info if len(unzbdata) == dunzip_len else {}
		
