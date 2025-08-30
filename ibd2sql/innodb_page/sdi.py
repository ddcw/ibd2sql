import struct
import json
import zlib
from ibd2sql.innodb_page.page import PAGE

class SDI(object):
	"""
	INPUT:
		sdino: sdi page id
		pg: page reader
		row_format: row format
	RETURN:
		data(json): sdi data
	"""
	def __init__(self,sdino,pg,row_format):
		self.sdino = sdino
		self.pg = pg
		self.offset = 99
		self.rec_header_size = 5
		self.row_format = row_format
		if row_format == "REDUNDANT":
			self.offset = 101
			self.rec_header_size = 6

	def get_sdi(self):
		pageno = self.sdino
		data = PAGE()
		n_recs = 0
		#dd = {}
		dd = []
		while pageno < 4294967295: 
			data.init(self.pg.read(pageno))
			data.init_fil()
			data.init_page_header()
			n_recs = data.PAGE_N_RECS
			pageno = data.FIL_PAGE_NEXT
			if self.row_format == 'COMPRESSED':
				data._offset = self.pg.PAGE_SIZE - 2*n_recs
				d = zlib.decompressobj()
				_dd = d.decompress(data.data[94:])
				data.offset = self.pg.PAGE_SIZE - len(d.unused_data)
			self.offset = data.offset
			self.offset += struct.unpack('>h',data.data[data.offset-2:data.offset])[0]
			while n_recs > 0:# general tablespace
				n_recs -= 1
				if self.row_format != 'COMPRESSED':
					data.offset = self.offset
					self.offset += struct.unpack('>h',data.data[data.offset-2:data.offset])[0]
				if data.offset > 16384 or (data.offset == 112 and self.row_format != 'COMPRESSED'):
					break
				if self.row_format == 'COMPRESSED':
					_t1,_t2 = struct.unpack('>BB',data.read(2))
					if _t2 >= 128:
						_t1 += (_t2-128)*256
					else:
						data.offset -= 1
					_ = data.read(1)
					sdi_type,sdi_id = struct.unpack('>LQ',data.read(12))
					trx1,trx2,undo1,undo2,undo3 = struct.unpack('>LHLHB',data.read_reverse(13))
				else:
					sdi_type,sdi_id = struct.unpack('>LQ',data.read(12))
					trx1,trx2,undo1,undo2,undo3 = struct.unpack('>LHLHB',data.read(13))
				dunzip_len,dzip_len = struct.unpack('>LL',data.read(8))
				trx = (trx1<<16) + trx2
				undo = (undo1<<24) + (undo2<<8) + undo3
				unzbdata = b''
				if b'\x14\xc0' == data.data[data.offset-self.rec_header_size-2:data.offset-self.rec_header_size] or data.data[data.offset:data.offset+2] == b'\x14\xc0': # overflow page
					unzbdata = b''
					SPACE_ID,PAGENO,BLOB_HEADER,REAL_SIZE = struct.unpack('>3LQ',data.read(20))
					if REAL_SIZE != dzip_len:
						sys.exit(1)
					while True:
						tdata = self.pg.read(PAGENO)
						REAL_SIZE,PAGENO = struct.unpack('>LL',tdata[38:46])
						unzbdata += tdata[46:-8]
						if PAGENO == 4294967295:
							break
					unzbdata = zlib.decompress(unzbdata)
				else:
					#unzbdata = zlib.decompress(data[offset+33:offset+33+dzip_len])
					unzbdata = zlib.decompress(data.read(dzip_len))
				dic_info = json.loads(unzbdata.decode())
				#dd[dic_info['dd_object']['schema_ref']+'.'+dic_info['dd_object']['name']] = dic_info
				#dd[dic_info['dd_object']['name']] = dic_info
				dd.append(dic_info)
		return dd
