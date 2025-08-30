import struct
from ibd2sql.utils import crc32c
from ibd2sql.innodb_page.xdes import GET_XDES_SIZE_COUNT
from ibd2sql.utils.aes import aes_ecb256_decrypt

INFO_SIZE = 111
INFO_MAX_SIZE = 115
SDI_VERSION = 1

def GET_FSP_STATUS_FROM_FLAGS(flags):
	logical_size = 16384 if ((flags & 960) >> 6) == 0 else 512 << ((flags & 960) >> 6)
	physical_size = logical_size if ((flags & 30) >> 1) == 0 else 512<<((flags & 30) >> 1)
	compressed = False if ((flags & 30) >> 1) == 0 else True
	return {
		'POST_ANTELOPE':(flags & 1) >> 0,
		'ZIP_SSIZE':(flags & 30) >> 1,
		'ATOMIC_BLOBS':(flags & 32) >> 5,
		'PAGE_SSIZE':(flags & 960) >> 6,
		'DATA_DIR':(flags & 1024) >> 10,
		'SHARED':(flags & 2048) >> 11,
		'TEMPORARY':(flags & 4096) >> 12,
		'ENCRYPTION':(flags & 8192) >> 13,
		'SDI':(flags & 16384) >> 14,
		'logical_size':logical_size, # logical page size (in memory)
		'physical_size':physical_size, # physical page size (in disk)
		'compressed':compressed
	}

def PARSE_ENCRYPTION_INFO(data,kd):
	"""
	INPUT:
		data: encryption_data(115 bytes)
		kd: keyring file data dict
	RETURN:
		dict(key,iv...)
	"""
	magic = data[:3]
	master_key_id = struct.unpack('>L',data[3:7])[0]
	offset = 7
	if magic == b"lCB":
		offset += 4
	server_uuid = data[offset:offset+36].decode()
	offset += 36
	master_key = kd['INNODBKey'+'-'+server_uuid+'-'+str(master_key_id)]['key']
	key_info = aes_ecb256_decrypt(master_key,data[offset:offset+32*2])
	offset += 32*2
	checksum_1 = crc32c.calculate_crc32c(key_info)
	checksum_2 = struct.unpack('>L',data[offset:offset+4])[0]
	return {'key':key_info[:32],'iv':key_info[32:48],'magic':magic,'server_uuid':server_uuid,'checksum_1':checksum_1,'checksum_2':checksum_2,'status':checksum_1 == checksum_2}

class FSP(object):
	def __init__(self,data,page_size=0,compression_ratio=1):
		self.compression_ratio = compression_ratio
		self.data = data
		self.PAGE_SIZE = len(data) if page_size == 0 else page_size
		self.XDES_SIZE,self.XDES_COUNT = GET_XDES_SIZE_COUNT(self.PAGE_SIZE)
		self.XDES_SIZE = self.XDES_SIZE//compression_ratio
		self.init_space_header()
		self.init_xdes()
		self.init_encryption()
		self.init_sdi()
		self.FIL_PAGE_PREV,self.FIL_PAGE_NEXT = struct.unpack('>2L',data[8:16])
		#self.init_fsp_status()
		

	def init_space_header(self):
		data = self.data[38:38+112]
		self.FSP_SPACE_ID,self.FSP_NOT_USED,self.FSP_SIZE,self.FSP_FREE_LIMIT,self.FSP_SPACE_FLAGS,self.FSP_FRAG_N_USED = struct.unpack('>6L',data[:6*4])
		self.FSP_FREE = struct.unpack('>LLHLH',data[24:40])
		self.FSP_FREE_FRAG = struct.unpack('>LLHLH',data[40:56])
		self.FSP_FULL_FRAG = struct.unpack('>LLHLH',data[56:72])
		self.FSP_SEG_ID = struct.unpack('>Q',data[72:80])
		self.FSP_SEG_INODES_FULL = struct.unpack('>LLHLH',data[80:96])
		self.FSP_SEG_INODES_FREE = struct.unpack('>LLHLH',data[96:112])


	def init_xdes(self):
		self.xdes = []
		for i in range(self.XDES_COUNT):
			self.xdes.append(self.data[150+i*self.XDES_SIZE:150+i*self.XDES_SIZE+self.XDES_SIZE])

	def init_encryption(self):
		offset = 150+self.XDES_COUNT*self.XDES_SIZE
		self.encryption_info = self.data[offset:offset+INFO_MAX_SIZE]
		self.encryption = False if self.encryption_info != b'\x00'*115 else True

	def init_sdi(self):
		offset = 150+self.XDES_COUNT*self.XDES_SIZE+115
		self.SDI_VERSION,self.SDI_PAGE_NO = struct.unpack('>LL',self.data[offset:offset+8])

