from ibd2sql.innodb_page import *

class xdes(page):
	"""
             |---> FIL_HEADER                    38  bytes
             |---> SPACE_HEADER (only fsp_hdr)   112 bytes
             |---> XDES 0                        40  bytes
XDES/FSP_HDR-|---> XDES ...                      40  bytes
             |---> XDES 255                      40  bytes
             |---> FIL_TRAILER                   8   bytes


             |---> FSP_SPACE_ID                  4   bytes
             |---> FSP_NOT_USED                  4   bytes
             |---> FSP_SIZE                      4   bytes
             |---> FSP_FREE_LIMIT                4   bytes
             |---> FSP_SPACE_FLAGS               4   bytes
SPACE_HEADER-|---> FSP_FRAG_N_USED               4   bytes
             |---> FSP_FREE                      16   bytes
             |---> FSP_FREE_FRAG                 16  bytes
             |---> FSP_FULL_FRAG                 16  bytes
             |---> FSP_SEG_ID                    8   bytes
             |---> FSP_SEG_INODES_FULL           16  bytes
             |---> FSP_SEG_INODES_FREE           16  bytes 
	"""
	def __init__(self,*args,**kwargs):
		super().__init__(*args,**kwargs)
		self.fsp_status = False
		if self.FIL_PAGE_TYPE not in (9,8) : #FIL_PAGE_TYPE_XDES,FIL_PAGE_TYPE_FSP_HDR
			return None
		self.page_name = 'XDES'

		if self.FIL_PAGE_TYPE == 8:
			self.page_name = "FSP_HDR"
			self.FSP_SPACE_ID, self.FSP_NOT_USED, self.FSP_SIZE, self.FSP_FREE_LIMIT, self.FSP_SPACE_FLAGS, self.FSP_FRAG_N_USED = struct.unpack('>6L',self.read(24))
			self.FSP_FREE = FLST_BASE_NODE(self.read(16))
			self.FSP_FREE_FRAG = FLST_BASE_NODE(self.read(16))
			self.FSP_FULL_FRAG = FLST_BASE_NODE(self.read(16))
			self.FSP_SEG_ID = struct.unpack('>Q',self.read(8))
			self.FSP_SEG_INODES_FULL = FLST_BASE_NODE(self.read(16))
			self.FSP_SEG_INODES_FREE = FLST_BASE_NODE(self.read(16))


		#XDES
		self.XDES = []
		for x in range(256):
			self.XDES.append(XDES(self.read(40)))

		#SDI PAGE NUMBER for issue 5 https://github.com/ddcw/ibd2sql/issues/5
		self.offset += INFO_MAX_SIZE #SDI_OFFSET
		sdi_version = struct.unpack('>I',self.read(4))[0]
		if sdi_version == SDI_VERSION:
			sdi_page_no = struct.unpack('>I',self.read(4))[0]
			self.SDI_PAGE_NO = sdi_page_no
			self.fsp_status = True
		else:
			self.fsp_status = False
			#return False
