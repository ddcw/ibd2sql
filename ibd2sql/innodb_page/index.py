from ibd2sql.innodb_page.page import PAGE
from ibd2sql.innodb_page.lob import FIRST_BLOB
from ibd2sql.utils.b2data import B2UINT6
from ibd2sql.utils.b2data import B2UINT7
import struct
import zlib
REC_STATUS_ORDINARY = 0 # leaf
REC_STATUS_NODE_PTR = 1 # non-leaf
REC_STATUS_INFIMUM  = 2 # INFIMUM
REC_STATUS_SUPREMUM = 3 # SUPREMUM
REC_N_FIELDS_ONE_BYTE_MAX = 0x7F

class INDEX(PAGE):
	"""
	init_index INPUT:
		table:
		idxid:
		colid_list:
		null_count:
		pg:
		page_type:
		disable_extra_pages:
		decode:
		row_format:
		replace:
		complete:
		multi: # for sql
		fields_terminated: # for load data
		fields_enclosed:
		lines_terminated:

	USAGE:
	init_index: init index obj
	init_data : init data for next page
	get_sql   : return sql list # only for pk leaf
	get_data  : return data # for load data
	get_all_rows : return all rows list[dict]
	"""

	def init_index(self,**kwargs):
		# must
		self.table = kwargs['table']
		self.idxid = kwargs['idxid']
		self.pg = kwargs['pg']
		self.page_type = kwargs['page_type'] # pk_leaf,pk_non_leaf...

		# other
		self.foffset = 99
		self.offset = 99
		self._offset = 99
		self.offset_start = 120
		self.offset_end = 0
		self.rec_header = {}

		# options
		self.disable_extra_pages = kwargs['disable_extra_pages'] if 'disable_extra_pages' in kwargs else False
		self.decode = kwargs['decode'] if 'decode' in kwargs else True
		self.replace = kwargs['replace'] if 'replace' in kwargs else False
		self.complete = kwargs['complete'] if 'complete' in kwargs else False
		self.multi = kwargs['multi'] if 'multi' in kwargs else False
		self.fields_terminated = kwargs['fields_terminated'] if 'fields_terminated' in kwargs else '\t'
		self.fields_enclosed = kwargs['fields_enclosed'] if 'fields_enclosed' in kwargs else '' # no use
		self.lines_terminated = kwargs['lines_terminated'] if 'lines_terminated' in kwargs else '\n'
		
		# gen
		self.row_format = self.table.row_format
		self.colid_list = self.table.index[self.idxid]['colid_list']
		self.colid_list_pk = self.colid_list + self.table.pk if self.table.mysql_version_id <= 50744 else self.colid_list
		self.null_count = self.table.index[self.idxid]['null_count']
		self.sqlpre = "REPLACE " if self.replace and not self.multi else "INSERT "
		self.sqlpre += f"INTO {self.table._enclosed}{self.table.schema}{self.table._enclosed}.{self.table._enclosed}{self.table.name}{self.table._enclosed}"
		if self.complete:
			self.sqlpre += "(" + ','.join([ self.table._enclosed+colname+self.table._enclosed for colname,coldefault in self.table.column_order ]) + ")"
		self.sqlpre += " VALUES "
		if self.multi:
			self.get_sql = self._get_sql_multi
		else:
			self.get_sql = self._get_sql_single

		if self.page_type == "PK_LEAF":
			self._read_row = self._read_row_pk_leaf
		elif self.page_type == "PK_NON_LEAF":
			self._read_row = self._read_row_pk_non_leaf
			self.null_count = self.table.pk_null_count
		elif self.page_type == "KEY_LEAF":
			self._read_row = self._read_row_key_leaf
		elif self.page_type == "KEY_NON_LEAF":
			self._read_row = self._read_row_key_non_leaf

		if self.table.mysql_version_id <= 80028:
			self._read_row_version = self._read_row_count

		# auto (base at REDUNDANT)
		if self.row_format == "REDUNDANT":
			self._read_extra_column = self._read_extra_column_with_768
			self._read_rec_header_new = self._read_rec_header_old
			self._read_nullbitmask_varsize_new = self._read_nullbitmask_varsize_old
			self.foffset = 101
		elif self.row_format == "COMPACT":
			self._read_extra_column = self._read_extra_column_with_768
		elif self.row_format == "COMPRESSED":
			self.get_all_rows = self._get_all_rows_compressed
			self._read_extra_20 = self._read_extra_20_compressed
			self._read_trx_id_rollptr = self._read_trx_id_rollptr_compressed
			#self._read_nullbitmask_varsize_new = self._read_nullbitmask_varsize_compressed
		

	def init_data(self,data):
		self.data = data
		self.offset = self.foffset
		self._offset = self.foffset

	def get_data(self,deleted=False):
		data_list = []
		for data in self.get_all_rows(deleted):
			data = data['data']
			v = ''
			for colname,coldefault in self.table.column_order:
				v += f"{coldefault if colname not in data else data[colname]['data']}"+self.fields_terminated
			data_list.append(v[:-1])
		return data_list

	def get_sql(self):
		pass # do nothing

	def _get_sql_single(self,deleted=False):
		sql_list = []
		for data in self.get_all_rows(deleted):
			data = data['data']
			v = ''
			for colname,coldefault in self.table.column_order:
				v += f"{coldefault if colname not in data else data[colname]['data']},"
			sql_list.append(f"{self.sqlpre}({v[:-1]})")
		return sql_list

	def _get_sql_multi(self,deleted=False):
		sql = f"{self.sqlpre}"
		for data in self.get_all_rows(deleted):
			data = data['data']
			v = ''
			for colname,coldefault in self.table.column_order:
				v += f"{coldefault if colname not in data else data[colname]['data']},"
			sql += f"({v[:-1]}),"
		return [sql[:-1]]

	def get_all_rows(self,deleted=False):
		all_row = []
		row_count = 0
		if deleted:
			deleted_offset = struct.unpack('>H',self.data[44:46])[0]
			self.offset = deleted_offset
			self._offset = deleted_offset
			row_count = (struct.unpack('>H',self.data[42:44])[0] & 32767) - struct.unpack('>H',self.data[54:56])[0] - 2
		else:
			row_count = struct.unpack('>H',self.data[54:56])[0] + 2

		for _ in range(row_count):
			self._read_rec_header_new()
			if self.rec_header['REC_TYPE'] <= 1:
				row,pageid = self._read_row()
				all_row.append({'data':row,'pageid':pageid,'deleted':self.rec_header['REC_INFO_DELETED']})
			# next page
			self.offset = self._offset = self.rec_header['REC_NEXT']
		return all_row

	def _get_all_rows_compressed(self,deleted=False):
		all_row = []
		n_dense = struct.unpack('>H',self.data[42:44])[0] & 32767
		n_recs = struct.unpack('>H',self.data[54:56])[0]
		d = zlib.decompressobj()
		c = d.decompress(self.data[94:])
		toffset = c.find(b'\x01') + 1
		data = self.data[:94]
		data += struct.pack('>BBB',0x01,0x00,0x02)
		data += self.data[-2:]
		data += struct.pack('>8B',0x69, 0x6e, 0x66, 0x69, 0x6d, 0x75, 0x6d, 0x00)
		data += b'\x03'
		data += struct.pack('>12B',0x00,0x0b,0x00,0x00,0x73,0x75,0x70,0x72,0x65,0x6d,0x75,0x6d)
		data += c[toffset:]
		compressed_offset = len(data)
		data += d.unused_data
		old_data = self.data
		self.data = data
		self.offset = 120
		self.offset_end = len(data)
		self.offset_start = self.offset
		page_dir = []
		for i in range(n_recs):
			slot = struct.unpack('>H',self._read_compressed_end(2))[0] & 16383 # ignore owned
			page_dir.append([slot,False])
		for j in range(n_dense-n_recs-2): # user record deleted
			slot = struct.unpack('>H',self._read_compressed_end(2))[0] & 16383
			page_dir.append([slot,True])
		_ = page_dir.sort()
		if self.page_type == "PK_LEAF":
			self.trxid_rollptr = [ self._read_compressed_end(13) for x in range(n_dense-2) ]
		self.c_offset = 0 # compressed offset
		have_compressed = False # True if compressed else False
		have_compressed_offset = 0
		for x in range(n_dense-2):
			self.offset_start = self.offset
			offset,is_deleted = page_dir[x]
			self.offset = offset - 5*(x+1) - 13*x
			if self.offset > compressed_offset:
				#print(x,have_compressed_offset,have_compressed,self.offset_start,page_dir[x],data[1037:1037+14])
				have_compressed_offset += 1 if x <= 62 else 2
				have_compressed = True
				self.offset_start += 1 if x <= 62 else 2
			if have_compressed:
				self.offset += have_compressed_offset
			if deleted != is_deleted:
				continue
			self._offset = self.offset
			self.rec_header = {
				"REC_INFO_INSTANT":False,
				"REC_INFO_VERSION":False,
				"REC_INFO_DELETED":is_deleted,
				"REC_INFO_MIN_REC":True if x == 0 else False,
				"REC_N_OWNED":False,
				"REC_HEAP_NO":0,
				"REC_TYPE": 0 if self.page_type in ["PK_LEAF","KEY_LEAF"] else 1,
				"REC_NEXT":self.offset,
				"is_compressed": not have_compressed
			}
			row,pageid = self._read_row()
			all_row.append({'data':row,'pageid':pageid,'deleted':self.rec_header['REC_INFO_DELETED']})
		self.data = old_data
		return all_row


	def _read_id_comprssed(self):
		b1 = self._read_compressed_start(1)
		if b1 == b'\x80':
			b1 += self._read_compressed_start(1)
		return b1

	def _read_nullbitmask_varsize_old(self,colid_list,null_count,compressed=True):
		null_list = []
		size_list = []
		size_null_format = '>H'
		size_null_size = 2
		nmask = 32768
		if self.rec_header['REC_SHORT']:
			size_null_format = '>B'
			size_null_size = 1
			nmask = 128
		lastoffset = 0
		for colid in colid_list:
			size_null = struct.unpack(size_null_format,self.read_reverse(size_null_size))[0]
			isnull = True if nmask&size_null else False
			vsize = (nmask-1)&size_null
			t = vsize
			vsize -= lastoffset
			lastoffset = t
			if self.table.column[colid]['name'] in ['DB_TRX_ID','DB_ROLL_PTR']:
				continue
			size_list.append(vsize)
			null_list.append(isnull)
		return null_list,size_list

	def _read_nullbitmask_varsize_new(self,colid_list,null_count,compressed=True):
		null_list = []
		size_list = []
		nullvalue = 0
		compressed = self.rec_header['is_compressed']
		#compressed = True if 'is_compressed' in self.rec_header and self.rec_header['is_compressed'] else False
		if compressed:
			nullvalue = int.from_bytes(self.read_reverse((null_count+7)//8),'big') if null_count > 0 else 0
		else:
			nullvalue = int.from_bytes(self._read_compressed_start((null_count+7)//8),'big') if null_count > 0 else 0
		n = 0
		for colid in colid_list:
			col = self.table.column[colid]
			vsize = col['size']
			null = False
			if col['is_nullable']:
				null = True if nullvalue&(1<<n) else False
				n += 1
			if null: # null
				vsize = 0
			else:
				if col['is_var']:
					if col['is_big']:
						tsize = struct.unpack('>B',self.read_reverse(1) if compressed else self._read_compressed_start(1))[0]
						if tsize > REC_N_FIELDS_ONE_BYTE_MAX:
							vsize = struct.unpack('>B',self.read_reverse(1) if compressed else self._read_compressed_start(1) )[0] + (tsize-128)*256
						else:
							vsize = tsize
					else:
						vsize = struct.unpack('>B',self.read_reverse(1))[0] if compressed else self._read_compressed_start(1)[0]
			null_list.append(null)
			size_list.append(vsize)
		return null_list,size_list

	def _read_nullbitmask_varsize_compressed(self,colid_list,null_count,compressed=True):
		pass # do nothing

	def _read_trx_id_rollptr(self):
		offset = self.offset
		trxid = self.read(6)
		rollptr = self.read(7)
		return self._read_trx_id_format(trxid,rollptr,offset)

	def _read_trx_id_format(self,trxid,rollptr,offset):
		return {
			'DB_TRX_ID':{
				'data':B2UINT6(trxid),
				'offset':offset,
				'size':6
			},
			'DB_ROLL_PTR':{
				'data':B2UINT7(rollptr),
				'offset':offset+6,
				'size':7
			}
		}

	def _read_trx_id_rollptr_compressed(self):
		offset = self.offset_end
		data = self.trxid_rollptr.pop(0)
		trxid = data[:6]
		rollptr = data[6:13]
		return self._read_trx_id_format(trxid,rollptr,0)

	def _read_row(self):
		pass # do nothing. return row,(pageid if non leaf else 0)

	def _read_row_pk_leaf(self):
		# varsize,null_bitmask,row_version,record_header,pk,[pk,field]
		row_version = self._read_row_version()
		colid_list = self.table.pk + self.table.pkmr[row_version]['colid']
		null_count = self.table.pkmr[row_version]['null_count']
		null_list,size_list = self._read_nullbitmask_varsize_new(colid_list,null_count)
		row = self._read_field(self.table.pk,[ null_list.pop(0) for _ in range(len(self.table.pk)) ],[ size_list.pop(0) for _ in range(len(self.table.pk))]) # key, nullable,varsize
		row.update(self._read_trx_id_rollptr())
		the_rest_of_field = self.table.pkmr[row_version]['colid'][2:] if self.row_format == 'REDUNDANT' else self.table.pkmr[row_version]['colid']
		row.update(self._read_field(the_rest_of_field,null_list,size_list))
		return row,0

	def _read_row_pk_non_leaf(self):
		# varsize,null_bitmask,record_header,pk,child_pageid
		null_list,size_list = self._read_nullbitmask_varsize_new(self.table.pk,self.null_count)
		row = self._read_field(self.table.pk,null_list,size_list)
		return row,struct.unpack('>L',self.read(4))[0]

	def _read_row_key_leaf(self):
		# varsize,null_bitmask,record_header,key,pk
		null_list,size_list = self._read_nullbitmask_varsize_new(self.colid_list+self.table.pk,self.null_count)
		row = self._read_field(self.colid_list,null_list,size_list,)
		return row,0

	def _read_row_key_non_leaf(self):
		# varsize,null_bitmask,key,record_header,key,pk,child_pageid
		null_list,size_list = self._read_nullbitmask_varsize_new(self.colid_list_pk,self.null_count)
		row = self._read_field(self.colid_list_pk,null_list,size_list)
		return row,struct.unpack('>L',self.read(4))[0]


	def _read_field(self,colid_list,null_list,size_list):
		row = {}
		for colid in colid_list:
			col = self.table.column[colid]
			colname = col['name']
			vsize = size_list.pop(0)
			null = null_list.pop(0)
			offset = self.offset
			data = None
			if null:
				data = 'null'
			elif vsize == 16404:
				if self.disable_extra_pages:
					data = 'null'
					null = True
				else:
					data = self._read_extra_column()
			else:
				data = self.read(vsize)
			if not null:
				if self.decode:
					data = col['decode'](data,*col['args'])
				else:
					data = '0x' + data.hex()
			row[colname] = {
				'data':data,
				'offset:':offset,
				'size':vsize
			}
		return row

	def _read_row_version(self):
		return struct.unpack('>B',self.read_reverse(1))[0] if self.rec_header['REC_INFO_INSTANT'] or self.rec_header['REC_INFO_VERSION'] else 0

	def _read_row_count(self,): # <=8.0.28
		rdata = 0
		if self.rec_header['REC_INFO_INSTANT']:
			t1 = struct.unpack('>B',self.read_reverse(1))[0]
			if t1 >= 128:
				t2 = struct.unpack('>B',self.read_reverse(1))[0]
				t1 = t2 + (t1-128)*256
			rdata = t1
		return rdata

	def _read_rec_header_old(self):
		data = self.read_reverse(6)
		rec,rec_next = struct.unpack('>LH',data)
		REC_TYPE = REC_STATUS_ORDINARY if self.data[64:66] == b'\x00\x00' else REC_STATUS_NODE_PTR
		if self.offset == 101:
			REC_TYPE = REC_STATUS_INFIMUM
		if rec_next == 0:
			REC_TYPE = REC_STATUS_SUPREMUM
		self.rec_header = {
			"REC_INFO_INSTANT": True if rec&2147483648 > 0 else False,
			"REC_INFO_VERSION": True if rec&1073741824 > 0 else False,
			"REC_INFO_DELETED": True if rec&536870912  > 0 else False,
			"REC_INFO_MIN_REC": True if rec&268435456  > 0 else False,
			"REC_N_OWNED" : (rec&251658240)>>24,
			"REC_HEAP_NO" : (rec&16775168)>>11,
			"REC_N_FIELDS": (rec&2046)>>1,
			"REC_SHORT"   : True if rec&1 == 1 else False,
			"REC_TYPE"    : REC_TYPE,
			"REC_NEXT"    : rec_next,
			"is_compressed":True,
		}

	def _read_rec_header_new(self):
		data = self.read_reverse(5)
		rec1,rec2,rec_next = struct.unpack('>HBh',data)
		rec = (rec1<<8)+rec2
		self.rec_header = {
			"REC_INFO_INSTANT": True if rec&8388608 > 0 else False,
			"REC_INFO_VERSION": True if rec&4194304 > 0 else False,
			"REC_INFO_DELETED": True if rec&2097152 > 0 else False,
			"REC_INFO_MIN_REC": True if rec&1048576 > 0 else False,
			"REC_N_OWNED" : (rec&983040)>>16,
			"REC_HEAP_NO" : (rec&65528)>>3,
			"REC_TYPE"    : rec&7,
			"REC_NEXT"    : rec_next + self._offset + 5,
			"is_compressed":True,
		}

	def _read_extra_column_with_768(self):
		return self.read(768) + self._read_extra_column()

	def _read_extra_column(self):
		SPACE_ID,PAGENO,BLOB_HEADER,REAL_SIZE = struct.unpack('>3LQ',self._read_extra_20())
		data = b''
		if self.table.mysql_version_id > 50744:
			data = FIRST_BLOB(self.pg,PAGENO)
		else:
			while True:
				_ndata = self.pg.read(PAGENO)
				REAL_SIZE,PAGENO = struct.unpack('>LL',_ndata[38:46])
				data += _ndata[46:46+REAL_SIZE]
				if PAGENO == 4294967295:
					break
		return data

	def _read_extra_20(self):
		return self.read(20)

	def _read_extra_20_compressed(self):
		return self._read_compressed_end(20)

	def _read_compressed_start(self,n):
		data = self.data[self.offset_start:self.offset_start+n]
		self.offset_start += n
		return data

	def _read_compressed_end(self,n):
		data = self.data[self.offset_end-n:self.offset_end]
		self.offset_end -= n
		return data

