from collections import namedtuple
import zlib
import struct
from ibd2sql.utils import lz4
from ibd2sql.utils import aes
from ibd2sql.utils.b2data import *

PAGE_NEW_INFIMUM = 99
PAGE_NEW_SUPREMUM = 112
INFO_SIZE = 111
INFO_MAX_SIZE = 115
SDI_VERSION = 1

class PAGE_READER(object):
	"""
	INPUT:
		require:
			page_size: page size
			filename: filename
		option:
			encryption: True or False
				iv  (require if encryption is True)
				key (require if encryption is True)
			compression: True or False

	RETURN:
		PAGE: binary data
		
	"""
	def __init__(self,*args,**kwargs):
		self.PAGE_SIZE = kwargs['page_size']
		self.filename = kwargs['filename']
		self.f = open(self.filename,'rb')
		self.pageid = 0
		if 'encryption' in kwargs and kwargs['encryption']:
			self.iv = kwargs['iv']
			self.key = kwargs['key']
			self.read = self._read_page_encryption
		else:
			self.read = self._read_page_compression
	#	elif 'compression' in kwargs and kwargs['compression']:
	#		self.read = self._read_page_compression
	#	else:
	#		self.read = self._read_page
		
	def __close__(self):
		self.f.close()

	def read(self,n):
		pass
	
	def _read_page_compression(self,*args):
		data = self._read_page(*args)
		if data[24:26] == b'\x00\x0e':
			FIL_PAGE_VERSION,FIL_PAGE_ALGORITHM_V1,FIL_PAGE_ORIGINAL_TYPE_V1,FIL_PAGE_ORIGINAL_SIZE_V1,FIL_PAGE_COMPRESS_SIZE_V1 = struct.unpack('>BBHHH',data[26:34])
			if FIL_PAGE_ALGORITHM_V1 == 1:
				data = data[:24] + struct.pack('>H',FIL_PAGE_ORIGINAL_TYPE_V1) + b'\x00'*8 + data[34:38] + zlib.decompress(data[38:38+FIL_PAGE_COMPRESS_SIZE_V1])
			elif FIL_PAGE_ALGORITHM_V1 == 2:
				data = data[:24] + struct.pack('>H',FIL_PAGE_ORIGINAL_TYPE_V1) + b'\x00'*8 + data[34:38] + lz4.decompress(data[38:38+FIL_PAGE_COMPRESS_SIZE_V1],FIL_PAGE_ORIGINAL_SIZE_V1)
		return data

	def _read_page(self,n=None):
		if n is not None:
			self.f.seek(n*self.PAGE_SIZE,0)
			self.pageid = n
		else:
			self.pageid += 1
		return self.f.read(self.PAGE_SIZE)

	def _read_page_encryption(self,*args):
		data = self._read_page(*args)
		if data[24:26] == b'\x00\x0f':
			FIL_PAGE_VERSION,FIL_PAGE_ALGORITHM_V1,FIL_PAGE_ORIGINAL_TYPE_V1,FIL_PAGE_ORIGINAL_SIZE_V1,FIL_PAGE_COMPRESS_SIZE_V1 = struct.unpack('>BBHHH',data[26:34])
			data = data[:24] + struct.pack('>H',FIL_PAGE_ORIGINAL_TYPE_V1) + b'\x00'*8 + data[34:38] + aes.aes_cbc256_decrypt(self.key,data[38:-10],self.iv) + aes.aes_cbc256_decrypt(self.key,data[-32:],self.iv)[-10:]
		return data


class PAGE(object):
	def __init__(self,):
		pass

	def init(self,data):
		self.data = data
		self.offset = 0
		self._offset = 0

	def init_fil(self):
		# FIL HEADER 0:38
		self.FIL_PAGE_SPACE_OR_CHECKSUM,self.FIL_PAGE_OFFSET,self.FIL_PAGE_PREV,self.FIL_PAGE_NEXT,self.FIL_PAGE_LSN,self.FIL_PAGE_TYPE,self.FIL_PAGE_FILE_FLUSH_LSN,self.FIL_PAGE_SPACE_ID = struct.unpack('>4LQHQL',self.data[:38])
		# FIL DATA 38:-8
		# FIL TRAILER -8:
		self.CHECKSUM,self.FIL_PAGE_LSN2 = struct.unpack('>LL',self.data[-8:])

	def init_page_header(self):
		self.PAGE_N_DIR_SLOTS,self.PAGE_HEAP_TOP,self.PAGE_N_HEAP,self.PAGE_FREE,self.PAGE_GARBAGE,self.PAGE_LAST_INSERT,self.PAGE_DIRECTION,self.PAGE_N_DIRECTION,self.PAGE_N_RECS,self.PAGE_MAX_TRX_ID,self.PAGE_LEVEL,self.PAGE_INDEX_ID = struct.unpack('>9HQHQ',self.data[38:38+36])
		self.PAGE_BTR_SEG_LEAF = struct.unpack('>LLH',self.data[74:84])
		self.PAGE_BTR_SEG_TOP = struct.unpack('>LLH',self.data[84:94])
		self.offset = PAGE_NEW_INFIMUM
		self._offset = PAGE_NEW_INFIMUM

	def read(self,n):
		data = self.data[self.offset:self.offset+n]
		self.offset += n
		return data

	def read_reverse(self,n):
		data = self.data[self._offset-n:self._offset]
		self._offset -= n
		return data
