#!/usr/bin/env python3
# writen by ddcw @https://github.com/ddcw
# 解析frm生成sdi_page的

import struct
import sys
import os
import datetime
import time
import json
import zlib
import base64
from ibd2sql.collations2 import COLLATIONS_DICT
from ibd2sql.mysql_json import jsonob
from ibd2sql.innodb_page import page
from ibd2sql.innodb_type import innodb_type_isvar

class MINI_PAGE(page):
	def __init__(self,bdata):
		super(MINI_PAGE,self).__init__(bdata)
		self.decimal_data = b''
	def read(self,n):
		return self.decimal_data

# 数据类型转换, mysql_type --> innodb_type
COL_TYPE = {
	#5.7 id: ('name', size, 8.0 id)
	1: ('tinyint', 1, 2), 
	2: ('smallint', 2, 3), 
	3: ('int', 4, 4), 
	4: ('float', 4, 5), 
	5: ('double', 8, 6), 
	7: ('timestamp', 4, 18), 
	8: ('bigint', 8, 9), 
	9: ('mediumint', 3, 10), 
	10: ('date', 4, 15), 
	11: ('time', 3, 20), 
	12: ('datetime', 8, 19), 
	13: ('year', 1, 14), 
	14: ('date', 3, 15), 
	15: ('varchar', -1, 16), 
	16: ('bit', -2, 17), 
	17: ('timestamp', 4, 18), 
	18: ('datetime', 8, 19), 
	19: ('time', 3, 20), 
	245: ('json', -1, 31), 
	246: ('decimal', -1, 21), 
	247: ('enum', -1, 22), 
	248: ('set', -1, 23), 
	249: ('tinyblob', 9, 24), 
	250: ('mediumblob', 11, 25), 
	251: ('longblob', 12, 26), 
	252: ('blob', 10, 27), 
	253: ('varchar', -1, 16), 
	254: ('char', -1, 16), 
	255: ('geometry', 12, 30)
}



def INNODB_TIMESPLIT(data,n,rule1):
	rdata1 = []
	for start,count in rule1:
		t = ( data & ((2**(n-start)-1)-(2**(n-start-count)-1)) )>>(n-start-count)
		rdata1.append(t)
	return rdata1


def BDATA2INTBD(bdata,):
	n = len(bdata)
	sn = ">"+str(n)+"B"
	tdata = struct.unpack(sn,bdata)
	rdata = 0
	for x in range(n):
		rdata += tdata[x]<<((n-x-1)*8)
	return rdata

class DATA_BUFFER(object):
	def __init__(self,data):
		self.size = len(data)
		self.data = data
		self.offset = 0
		self._offset = self.offset

	def read(self,n):
		if self.offset+n > self.size:
			return b''
		data = self.data[self.offset:self.offset+n]
		self.offset += n
		return data

	def read_int(self,n): # 全是无符号小端字节序
		data = self.read(n)
		if data is None:
			return None
		tdata = [ x for x in data ]
		rdata = 0
		for x in range(n):
			rdata += tdata[x]<<(x*8)
		return rdata

	def seek(self,offset,action=0):
		self.offset = offset


# @sql/table.cc create_frm open_binary_frm make_field_from_frm
# @mysqlfrm
class MYSQLFRM(object):
	def __init__(self,filename):
		self.filename = filename
		self.schema = filename.split('/')[-2] if len(filename.split('/')) >=2 else 'NO_DBNAME'
		self.table_name = filename.split('/')[-1].split('.frm')[0]
		with open(filename,'rb') as f:
			data = f.read()
		self.data = DATA_BUFFER(data)

		self.pack_record = 0
		self.HAVE_PRIMARY = False
		self.FRM_TYPE = None
		self.FRM_HEADER = None
		self.KEYS = None
		self.DEFAULT_VALUE = None
		self.ENGINE_DATA = None
		self.COMMENT = None
		self.COLUMNS = None

		self._read_frm_type()
		self._read_frm_header()
		self._read_keys()
		self._read_default_value()
		self._read_engine_data()
		self._read_comment()
		self._read_columns()

	def read_int(self,n):
		return self.data.read_int(n)

	def read(self,n):
		return self.data.read(n)

	def _read_frm_type(self):
		self.data.seek(0,0)
		self.FRM_TYPE = self.read_int(2)
		if self.FRM_TYPE != 0x01fe : # table:0x01fe  view:0x5954
			raise ValueError(f"仅支持table类型, 当前为:{self.FRM_TYPE}")

	def _read_frm_header(self):
		self.data.seek(2,0)
		self.FRM_HEADER = {
			'frm_version':self.read_int(1),
			'legacy_db_type':self.read_int(1),
			'_0':self.read_int(2),
			'io_size':self.read_int(2),
			'_1':self.read_int(2),
			'length':self.read_int(4),
			'tmp_key_length':self.read_int(2),
			'rec_length':self.read_int(2),
			'create_info_max_rows':self.read_int(4),
			'create_info_min_rows':self.read_int(4),
			'_2':self.read_int(2),
			'key_info_length':self.read_int(2),
			'create_info_table_option':self.read_int(2),
			'_3':self.read_int(2),
			'avg_row_length':self.read_int(4),
			'default_table_charset':self.read_int(1),
			'_4':self.read_int(1),
			'row_type':self.read_int(1),
			'charset_left':self.read_int(1),
			'stats_sample_pages':self.read_int(2),
			'stats_auto_recalc':self.read_int(1),
			'_5':self.read_int(2),
			'key_length':self.read_int(4),
			'mysql_version_id':self.read_int(4),
			'extra_size':self.read_int(4),
			'extra_rec_buf_length':self.read_int(2),
			'default_part_db_type':self.read_int(1),
			'key_block_size':self.read_int(2),
		}
		#print(json.dumps(self.FRM_HEADER))
		if self.FRM_HEADER['frm_version'] < 9:
			raise ValueError(f'frm_version require >= 9, current:{self.FRM_HEADER["frm_version"]}')
		if self.FRM_HEADER['legacy_db_type'] != 12:
			raise ValueError(f'only support innodb. current is:{elf.FRM_HEADER["legacy_db_type"]}')
		#record_offset = self.FRM_HEADER['io_size']+self.FRM_HEADER['tmp_key_length']+self.FRM_HEADER['rec_length']
		#record_offset = ((record_offset//self.FRM_HEADER['io_size']) + 1)*self.FRM_HEADER['io_size']
		#self.record_offset = record_offset
		self.record_offset = struct.unpack('<H',self.data.data[67:69])[0]

	def _read_keys(self):
		self.data.seek(self.FRM_HEADER['io_size'],0)
		keys = self.read_int(1)
		if keys & 0x80:
			keys = (keys&0x7f) | (self.read_int(1)<<8)
			key_parts = self.read_int(2)
			_ = self.read_int(6)
		else:
			key_parts = self.read_int(1)
			_ = self.read_int(4)
		INDEX = []
		for i in range(keys):
			key_info = {
				'name':'',
				'flags':self.read_int(2),
				'key_length':self.read_int(2),
				'user_defined_key_parts':self.read_int(1),
				'algorithm':self.read_int(1),
				'block_size':self.read_int(2),
				'key_parts':[],
				'comment':''
			}
			for j in range(key_info['user_defined_key_parts']):
				key_info['key_parts'].append({
					'fieldnr': self.read_int(2) & 16383, # FIELD_NR_MASK
					'offset': self.read_int(2),
					'key_type': self.read_int(2),
					'key_part_flag':self.read_int(1),
					'length':self.read_int(2)
				})
			INDEX.append(key_info)

		# 读取索引名字
		terminator = self.read(1)
		for i in range(keys):
			idxname = b''
			while True:
				name = self.read(1)
				if name == terminator:
					break
				else:
					idxname += name
			INDEX[i]['name'] = idxname.decode()
			if INDEX[i]['name'] == 'PRIMARY':
				self.HAVE_PRIMARY = True
		_ = self.read(1)

		# 读取索引的注释
		for i in range(keys):
			INDEX[i]['comment'] = self.read(self.read_int(2)).decode()

		self.KEYS = {
			'keys':keys,
			'key_parts':key_parts,
			'key':INDEX
		}
		#print(json.dumps(self.KEYS))
		

	def _read_default_value(self):
		self.data.seek(self.FRM_HEADER['io_size']+self.FRM_HEADER['tmp_key_length'],0)
		self.DEFAULT_VALUE = DATA_BUFFER(self.data.read(self.FRM_HEADER['rec_length']))
		

	def _read_engine_data(self):
		self.data.seek(self.FRM_HEADER['io_size']+self.FRM_HEADER['tmp_key_length']+self.FRM_HEADER['rec_length'],0)
		_  = self.read_int(2)
		engine_len = self.read_int(2)
		engine_name = self.read(engine_len).decode()
		partition_len = self.read_int(4)
		partition = self.read(partition_len).decode()
		self.ENGINE_DATA = {
			'engine_name':engine_name,
			'partition':partition
		}
		#print(json.dumps(self.ENGINE_DATA))

	def _read_comment(self):
		self.data.seek(self.record_offset+46,0)
		comment_size = self.read_int(1)
		if comment_size < 255:
			self.COMMENT = self.read(comment_size).decode()
		else:
			self.data.seek(self.FRM_HEADER['io_size']+self.FRM_HEADER['tmp_key_length']+self.FRM_HEADER['rec_length']+16,0)
			comment_size = self.read_int(2)
			self.COMMENT = self.read(comment_size).decode()
		#print('COMMENT:',self.COMMENT)

	def _read_columns(self):
		# 你以为结束了么, 其实才开始呢
		self.data.seek(self.record_offset+258,0)
		self.COLUMNS = {
			'fields':self.read_int(2),
			'pos':self.read_int(2),
			'_0':self.read_int(6),
			'n_length':self.read_int(2),
			'interval_count':self.read_int(2),
			'interval_parts':self.read_int(2),
			'int_length':self.read_int(2),
			'_1':self.read_int(6),
			'null_fields':self.read_int(2),
			'comment_length':self.read_int(2),
			'gcol_screen_length':self.read_int(2),
			'_2':self.read_int(5),
			'fields_per_screen':self.read_int(1),
			'field':[]
		}
		#print(self.COLUMNS['null_fields'],'')
		NAMESIZE = 0
		_ = self.read(42)
		screens_read = 1
		col_in_screen = 1
		fields_per_screen_n = 0
		for i in range(self.COLUMNS['fields']):
			if col_in_screen == self.COLUMNS['fields_per_screen']:
				screens_read += 1
				col_in_screen = 2 # issue 54 (1-->2)
				self.data.read(8)
				_terminator = self.data.read(1)
				while _terminator == b' ':
					_terminator = self.data.read(1)
				fields_per_screen_n += 1
				#_ = self.read(2)
			else:
				col_in_screen += 1
			ordinal_position = self.read_int(2) - 3 + fields_per_screen_n*(self.COLUMNS['fields_per_screen']-1)
			namesize = self.read_int(1)
			#name = self.read(namesize)
			name = self.read(namesize)[:-1].decode()
			NAMESIZE += namesize
			self.COLUMNS['field'].append({
				'ordinal_position':ordinal_position, # 逻辑位置
				'name':name,
				'comment':'',
				'metadata':None,
			})
		for i in range(self.COLUMNS['fields']):
			self.COLUMNS['field'][i]['metadata'] = {
				'_0':[self.read_int(1),self.read_int(1),self.read_int(1),],
				'field_length':self.read_int(2),
				'recpos':self.read_int(3),
				'pack_flag':self.read_int(2),
				'unireg_type':self.read_int(1),
				'charset_low':self.read_int(1),
				'interval_nr':self.read_int(1),
				'field_type':self.read_int(1),
				'collation_id':self.read_int(1),
				'comment_length':self.read_int(2),
			}
			if self.COLUMNS['field'][i]['metadata']['field_type'] > 248 or self.COLUMNS['field'][i]['metadata']['field_type'] == 15:
				self.pack_record = 1
			#print(self.COLUMNS['field'][i]['metadata'])
		_filedname = self.read(NAMESIZE+2)
		for i in range(self.COLUMNS['fields']):
			self.COLUMNS['field'][i]['comment'] = self.read(self.COLUMNS['field'][i]['metadata']['comment_length']).decode()
		
		for i in range(self.COLUMNS['fields']):
			if self.COLUMNS['field'][i]['metadata']['field_type'] in [247,248]:
				tdata = b''
				terminator = self.read(1)
				element = []
				while True:
					edata = self.read(1)
					if edata == b'\x00':
						break
					elif edata == terminator:
						element.append(tdata.decode())
						tdata = b''
						continue
					else:
						tdata += edata
				self.COLUMNS['field'][i]['elements'] = element
						
		# 将默认值拆分给每个字段 (字段是否有默认值)
		# HA_OPTION_PACK_RECORD = 1
		self.null_bit_pos = 1 if self.FRM_HEADER['create_info_table_option'] & 1 == 0 else 0
		self.default_value_null_bitmask = self.DEFAULT_VALUE.read_int((self.COLUMNS['null_fields']+7+self.null_bit_pos)//8)
		for i in range(self.COLUMNS['fields']):
			if i < self.COLUMNS['fields'] - 1:
				self.COLUMNS['field'][i]['default_bin'] = self.DEFAULT_VALUE.read(self.COLUMNS['field'][i+1]['metadata']['recpos']-self.COLUMNS['field'][i]['metadata']['recpos'])
			else:
				self.COLUMNS['field'][i]['default_bin'] = self.DEFAULT_VALUE.data[self.DEFAULT_VALUE.offset:]
			#print(self.COLUMNS['field'][i]['default_bin'])


	def _get_sdi_json(self):
		""" 返回json格式的sdi信息 """
		partition_type = 0
		partition_type2 = 0
		subpartition_type = 0
		if   self.ENGINE_DATA['partition'].startswith(' PARTITION BY HASH '):
			partition_type = 3
			partition_type2 = 1
		elif self.ENGINE_DATA['partition'].startswith(' PARTITION BY KEY '):
			partition_type = 3
			partition_type2 = 3
		elif self.ENGINE_DATA['partition'].startswith(' PARTITION BY LIST '):
			partition_type = 1
			partition_type2 = 8
		elif self.ENGINE_DATA['partition'].startswith(' PARTITION BY RANGE '):
			partition_type = 1
			partition_type2 = 7
		if self.ENGINE_DATA['partition'].find('\nSUBPARTITION BY ') > 0:
			subpartition_type = 3
		# 字段信息
		COLUMN = []
		#self.default_value_null_bitmask = self.DEFAULT_VALUE.read(1)
		#null_bitmask_adds = -1 if self.pack_record == 1 else 0
		null_bitmask_adds = 0 if self.FRM_HEADER['create_info_table_option'] & 1 == 0 else -1
		for i in range(len(self.COLUMNS['field'])):
			col = self.COLUMNS['field'][i]
			field_type = COL_TYPE[col['metadata']['field_type']][2]
			#print(col['name'],field_type,col['metadata']['field_type'],col['metadata'])
			char_length = col['metadata']['field_length']
			pack_flag = col['metadata']['pack_flag']
			type_default_size = COL_TYPE[col['metadata']['field_type']][1]
			default_size = type_default_size if type_default_size > 0 else char_length
			collation_id = col['metadata']['collation_id']
			options = 'interval_count=0'
			numeric_precision = 0
			numeric_scale = 0
			numeric_scale_null = True
			datetime_precision = 0
			datetime_precision_null = 1
			if col['metadata']['field_type'] == 246: # decimal
				numeric_precision = char_length - 2
				numeric_scale = (pack_flag>>8) & 31
				numeric_scale_null = False
			if field_type in [18,19] and char_length > 19:
				datetime_precision = char_length - 20
				datetime_precision_null = 0
			elif field_type == 20 and char_length > 10:
				datetime_precision = char_length - 11
				datetime_precision_null = 0
			if field_type == 22: # enum 重新计算type_default_size
				type_default_size = 2 if len(col['elements']) >= 2**8 else 1
				options = f'interval_count={len(col["elements"])}'
			elif field_type == 23: # set
				type_default_size = (len(col['elements'])+7)//8
				options = f'interval_count={len(col["elements"])}'

			# 默认值的判断
			has_no_default = False
			#null_bitmask_adds = 0 if self.pack_record == 1 else 1
			if col['metadata']['pack_flag']&(2**14)>0 or col['metadata']['unireg_type'] == 15:
				default_value_null = True
			elif col['metadata']['pack_flag']&(2**15)>0:
				null_bitmask_adds += 1
				default_value_null = False if self.default_value_null_bitmask&(1<<(null_bitmask_adds)) == 0 else True
			else:
				default_value_null = False
			default_value = b''
			default_value_utf8 = ''
			if type_default_size > 0 or field_type in [21,22,23]: # 定长类型的默认值
				default_value = col['default_bin']
				datasize = len(default_value)
				if field_type in [2,3,4,9,10]: # int
					default_value_utf8 = repr(int.from_bytes(default_value, byteorder='little', signed=False if pack_flag&1 == 1 else True))
				elif field_type == 5: # float
					default_value_utf8 = struct.unpack('f',default_value)[0]
				elif field_type == 6: # double
					default_value_utf8 = struct.unpack('d',default_value)[0]
				elif field_type == 18: # timestamp
					default_value_utf8 = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(BDATA2INTBD(default_value)))
				elif field_type == 14: # year
					default_value_utf8 = BDATA2INTBD(default_value)+1900
				elif field_type == 15:
					signed,year,month,day = INNODB_TIMESPLIT(
						BDATA2INTBD(default_value[:3]),
						24,
						[[0,1], [1,14], [15,4], [19,5]])
					jingdu = BDATA2INTBD(default_value[3:]) if datasize > 3 else ''
					rdata = f"{'-' if signed == 0 else ''}{year}-{str(month).zfill(2)}-{str(day).zfill(2)}{'.'+str(jingdu) if datasize > 3 else ''}"
					default_value_utf8 = rdata
				elif field_type == 19: # datetime
					signed,year_month,day,hour,minute,second = INNODB_TIMESPLIT(
						BDATA2INTBD(default_value[:5]),
						40,
						[[0,1], [1,17], [18,5], [23,5], [28,6], [34,6]])
					jingdu = BDATA2INTBD(default_value[5:]) if datasize > 5 else ''
					year = int(year_month/13)
					month = int(year_month%13)
					rdata = f"{'-' if signed == 0 else ''}{year}-{str(month).zfill(2)}-{str(day).zfill(2)} {str(hour).zfill(2)}:{str(minute).zfill(2)}:{str(second).zfill(2)}{'.'+str(jingdu) if datasize > 5 else ''}"
					default_value_utf8 = rdata
				elif field_type == 20: # time
					signed,hour,minute,second = INNODB_TIMESPLIT(
						BDATA2INTBD(default_value[:3]),
						24,
						[[0,1], [1,11], [12,6], [18,6]])
					jingdu = BDATA2INTBD(default_value[3:]) if datasize > 3 else ''
					rdata = f"{'-' if signed == 0 else ''}{str(hour).zfill(2)}:{str(minute).zfill(2)}:{str(second).zfill(2)}{'.'+str(jingdu) if datasize > 3 else ''}"
					default_value_utf8 = rdata
				elif field_type == 21: # decimal
					aa = MINI_PAGE(b'\x00'*16384)
					aa.decimal_data = default_value
					ct,isvar,size,isbig,elements_dict,varsize,extra = innodb_type_isvar({'name':'','column_type_utf8':f'decimal({numeric_precision},{numeric_scale})','elements':[],'type':field_type})
					default_value_utf8 = aa.read_innodb_decimal(len(default_value),(extra))
				elif field_type == 22: # enum
					default_value_utf8 = col['elements'][BDATA2INTBD(default_value)]
				elif field_type == 23: # set
					_tdata = BDATA2INTBD(default_value)
					_sn = 0
					_sdata = ''
					for x in col['elements']:
						if 1<<_sn & _tdata:
							_sdata += col['elements'][x] + ","
						_sn += 1
					default_value_utf8 = _sdata[:-1]
				elif col['metadata']['field_type'] in [15,254] and field_type == 16 and col['metadata']['pack_flag']&1 > 0:
					default_value_utf8 = hex(BDATA2INTBD(default_value))
				elif field_type == 31: # json
					_tdata = jsonob(bdata[1:],struct.unpack('<B',default_value[:1])[0]).init()
					default_value_utf8 = json.dumps(_tdata)
				else:
					default_value_utf8 = repr(int.from_bytes(default_value, byteorder='little', signed=False if pack_flag&1 == 1 else True))
					
			else: # 不定长类型的默认值
				_sizesize = 1 if char_length <= 255 else 2
				_default_value = col['default_bin']
				_default_value_size = int.from_bytes(_default_value[:_sizesize],byteorder='little',signed=False)
				default_value = _default_value[_sizesize:]
				default_value_utf8 = default_value[:_default_value_size].decode()
				
			#print(default_value_utf8,i,self.default_value_null_bitmask,default_value_null,self.pack_record)
			default_value = base64.b64encode(default_value).decode()
			column_type_utf8 = COL_TYPE[col['metadata']['field_type']][0]
			if col['metadata']['field_type'] == 15 and field_type == 16 and col['metadata']['pack_flag']&1 > 0: # 是否是varbinary
				column_type_utf8 = 'varbinary'
			if col['metadata']['field_type'] == 254 and field_type == 16 and col['metadata']['pack_flag']&1 > 0: # 是否是binary
				column_type_utf8 = 'binary'
			if field_type == 21 and not numeric_scale_null: #decimal
				column_type_utf8 += f"({numeric_precision},{numeric_scale})" 
			elif field_type in [22,23]:
				column_type_utf8 += f"({','.join([ repr(item) for item in col['elements'] ])})"
			elif field_type in [18,19,20] and datetime_precision_null != 1:
				column_type_utf8 += f"({datetime_precision})"
			elif field_type in [16]: # varchar之类的
				column_type_utf8 += f"({char_length//int(COLLATIONS_DICT[str(collation_id)]['MAXLEN'])})"
			elif field_type in [17]: # bit
				column_type_utf8 += f"({char_length})"
			elif field_type in [1,3,4,9]: # int
				column_type_utf8 += f"{' unsigned' if pack_flag&1==0 else '' }"

			# TIMESTAMP_OLD_FIELD  = 18
			# TIMESTAMP_DN_FIELD   = 21 # TIMESTAMP DEFAULT CURRENT_TIMESTAMP
			# TIMESTAMP_UN_FIELD   = 22 # TIMESTAMP DEFAULT <default value> ON UPDATE CURRENT_TIMESTAMP
			# TIMESTAMP_DNUN_FIELD = 23 # DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
			# None                      # no DEFAULT, no ON UPDATE
			default_option = ''
			if col['metadata']['unireg_type'] in [21,23]:
				default_option = 'CURRENT_TIMESTAMP'
				default_value_null = False
			update_option = ''
			if col['metadata']['unireg_type'] in [22,23]:
				update_option = 'CURRENT_TIMESTAMP'
				default_value_null = False

			# char是定长的, 不需要记录长度. 顺便把空格干掉
			if col['metadata']['field_type'] == 254:
				default_value_utf8 = col['default_bin'].decode().rstrip()

			COLUMN.append({
				'name':col['name'],
				'type':field_type,
				'type_name':COL_TYPE[col['metadata']['field_type']][0],
				'is_nullable':True if pack_flag&32768 else False,
				'is_zerofill':True if pack_flag&4 else False,
				'is_unsigned':False if pack_flag&1 else True,
				'is_auto_increment':True if col['metadata']['unireg_type'] == 15 else False,
				'is_virtual':False,
				'hidden':1,
				'ordinal_position':col['ordinal_position'],
				'char_length':char_length,
				'bytes':type_default_size if type_default_size > 0 else char_length,
				'numeric_precision':numeric_precision,
				'numeric_scale':numeric_scale,
				'numeric_scale_null':numeric_scale_null,
				'datetime_precision':datetime_precision,
				'datetime_precision_null':datetime_precision_null,
				'has_no_default':has_no_default,
				'default_value_null':default_value_null,
				'srs_id_null':True,
				'srs_id':0,
				'default_value':default_value,
				'default_value_utf8_null':default_value_null,
				'default_value_utf8':default_value_utf8,
				'default_option':default_option,
				'update_option':update_option,
				'comment':col['comment'],
				'generation_expression':'',
				'generation_expression_utf8':'',
				'options':options,
				'se_private_data':'table_id=123456789',
				'engine_attribute':'',
				'secondary_engine_attribute':'',
				'column_key':1, # 索引还是直接看INDEX部分
				'column_type_utf8':column_type_utf8,
				'elements':[] if 'elements' not in col else [ {'name':base64.b64encode(ename.encode()).decode(),'index':eindex} for eindex,ename in enumerate(col['elements'],start=1) ],
				'collation_id':collation_id,
				'is_explicit_collation':False, # 管它手动不手动的
			})
		current_ordinal_position = len(COLUMN)
		# 补充隐藏字段 rowid,rollptr & trxid
		if not self.HAVE_PRIMARY:
			current_ordinal_position += 1
			COLUMN.append({
				'name':'DB_ROW_ID',
				'type':10,
				'hidden':2,
				'char_length':6,
				'ordinal_position':current_ordinal_position,
			})
		current_ordinal_position += 1
		COLUMN.append({
			'name':'DB_TRX_ID',
			'type':10,
			'hidden':2,
			'char_length':6,
			'ordinal_position':current_ordinal_position,
		})
		current_ordinal_position += 1
		COLUMN.append({
			'name':'DB_ROLL_PTR',
			'type':9,
			'hidden':2,
			'char_length':7,
			'ordinal_position':current_ordinal_position,
		})

		INDEX = []
		PKC = 1 # 主键的数量, 主键一定是第一个索引, 所以只要看第一个索引即可.
		# 如果没得主键的话, 就伪造一个
		if not self.HAVE_PRIMARY:
			INDEX.append({
				'name':'PRIMARY',
				'hidden':True,
				'is_generated':False,
				'ordinal_position':1,
				'comment':'',
				'se_private_data':'root=3',
				'type':2,
				'algorithm':2,
				'is_visible':True,
				'elements':[ 
					{ 
						'ordinal_position':i,
						'length':4294967295,
						'order':2,
						'hidden':True,
						'column_opx': i+1 if i < current_ordinal_position - 1 else i - (current_ordinal_position-1)
					} for  i in range(1,current_ordinal_position+1)  ]
			})

		for i in range(len(self.KEYS['key'])):
			idx = self.KEYS['key'][i]
			#PK:0 UK:64 K:65 FULL:1025 SPA:129
			key_type = 3 if idx['name'] != 'PRIMARY' else 1
			if not idx['flags']&1 and key_type != 1:
				key_type = 2
			elif idx['flags'] & 1024:
				key_type = 4
			elif idx['flags'] & 128:
				key_type = 5
			INDEX.append({
				'name':idx['name'],
				'hidden':False,
				'ordinal_position':i+1 if self.HAVE_PRIMARY else i+2,
				'comment':idx['comment'],
				'se_private_data':'root=3;',
				'type':key_type,
				'is_visible':True,
				'engine':'InnoDB',
				'elements':[ {
					'ordinal_position':eindex,
					'length':ekey['length'] if key_type != 5 else 4294967295,
					'order':2,
					'hidden':False,
					'column_opx':ekey['fieldnr']-1
					} for eindex,ekey in enumerate(idx['key_parts'],start=1) ]
				#'o':idx
			})

		if self.HAVE_PRIMARY:
			PKC = len(INDEX[0]['elements'])
			# 补充主键索引剩余字段 # PK LEAF 有trx&ptr, 索引里面也会体现出来
			INDEX[0]['elements'].append({
				'ordinal_position':PKC+1,
				'length':4294967295,
				'order':2,
				'hidden':True,
				'column_opx':len(COLUMN)-2
			})
			INDEX[0]['elements'].append({
				'ordinal_position':PKC+2,
				'length':4294967295,
				'order':2,
				'hidden':True,
				'column_opx':len(COLUMN)-1
			})
			# 然后就是剩余字段了
			_have_column = []
			for x in INDEX[0]['elements']:
				_have_column.append(x['column_opx'])
			_current_idx = len(INDEX[0]['elements'])
			for x in range(len(COLUMN)):
				if x not in _have_column:
					_current_idx += 1
					INDEX[0]['elements'].append({
						'ordinal_position':_current_idx,
						'length':4294967295,
						'order':2,
						'hidden':True,
						'column_opx':x
					})
			

		# 补充其它索引的主键字段


		dd_object = {
			'name':self.table_name,
			'options':f'key_block_size={self.FRM_HEADER["key_block_size"]};pack_record={self.pack_record};stats_auto_recalc=0;stats_sample_pages=0;',
			'check_constraints':[],
			'collation_id':(self.FRM_HEADER['charset_left']<<8)+self.FRM_HEADER['default_table_charset'],
			'columns':COLUMN,
			'comment':self.COMMENT,
			'created':datetime.datetime.now().strftime('%Y%m%d%H%M%S'), # 可以查看文件的时间, 但没必要.
			'default_partitioning':partition_type,
			'default_subpartitioning':subpartition_type,
			'engine':'InnoDB', #self.FRM_HEADER['legacy_db_type'],
			'engine_attribute':'',
			'foreign_keys':[],
			'hidden':1,
			'indexes':INDEX,
			'last_altered':datetime.datetime.now().strftime('%Y%m%d%H%M%S'),
			'last_checked_for_upgrade_version_id':0, # 上一次执行check table tbl_name for upgrade命令时的版本
			'mysql_version_id':self.FRM_HEADER['mysql_version_id'],
			'partition_expression':self.ENGINE_DATA['partition'],
			'partition_expression_utf8':self.ENGINE_DATA['partition'],
			'is_explicit_partition_expression':True, # 现成的表达式, 没必要再拼接了
			'partition_type':partition_type2,
			'partitions':[], # 所以这个就没必要了.
			'row_format':2 if self.FRM_HEADER['row_type'] == 0 else self.FRM_HEADER['row_type'], #0:DEFAULT 2:DYNAMIC 3:COMPRESSED 4:REDUNDANT 5:COMPACT
			'schema_ref':self.schema,
			'se_private_data':'',
			'se_private_id':0,
			'secondary_engine_attribute':'',
			'subpartition_expression':self.ENGINE_DATA['partition'],
			'subpartition_expression_utf8':self.ENGINE_DATA['partition'],
			'subpartition_type':1 if subpartition_type > 0 else 0
		}
		dd = {
			'dd_object':dd_object,
			'dd_object_type':'Table',
			'dd_version':80000,
			'mysqld_version_id':self.FRM_HEADER['mysql_version_id'],
			'sdi_version':80000,
		}
		return json.dumps(dd)

	def get_sdi_page(self):
		""" 返回page 格式的sdi信息 """
		sdidata = self._get_sdi_json().encode()
		dunzip_len = len(sdidata)
		sdidata = zlib.compress(sdidata)
		dzip_len = len(sdidata)
		rsdidata = b'\x00'*24 + b'E\xbd' + b'\x00'*71 + b'\x01H' + b'\x00'*353 + struct.pack('>LL',dunzip_len,dzip_len) + sdidata + b'\x00'*(16384-460-dzip_len)
		return rsdidata
	

#f = open(sys.argv[1],'rb')
#data = f.read()
#aa = MYSQLFRM(sys.argv[1])
#print(aa._get_sdi_json())
