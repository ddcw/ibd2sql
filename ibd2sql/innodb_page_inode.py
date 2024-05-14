from ibd2sql.innodb_page import *
import struct 
class inode(page):
	"""
----------------------------------------------------------------
|                      FIL_HEADER(38 bytes)                    |
----------------------------------------------------------------
|     INODE INFO(pre and next inode page)(12 bytes)            |
----------------------------------------------------------------
|               FSEG (SDI PAGE)(192 bytes)                     |
----------------------------------------------------------------
|               FSEG (SDI PAGE)(192 bytes)                     |
----------------------------------------------------------------
|   FSEG (general cluster index)(NONE LEAF PAGE)(192 bytes)    |
----------------------------------------------------------------
|   FSEG (general cluster index)(LEAF PAGE)     (192 bytes)    |
----------------------------------------------------------------
|          FSEG (index)(NONE LEAF PAGE)(192 bytes)             |
----------------------------------------------------------------
|         FSEG (index)(LEAF PAGE)     (192 bytes)              |
----------------------------------------------------------------
|                       ..............                         |
----------------------------------------------------------------
|                      FIL_TRAILER(8 bytes)                    |
----------------------------------------------------------------
	"""
	def __init__(self,*args,**kwargs):
		super().__init__(*args,**kwargs)
		if self.FIL_PAGE_TYPE != 3:
			return False
		self.MYSQL5 = kwargs['MYSQL5']
		self.page_name = 'INODE'
		self.EXTRA_PAGE = True #假装还有额外的Inode page
		self._init_inodeinfo()
		self._init_segment()

	def _init_inodeinfo(self):
		self.inode_pre = FIL_ADDR(self.read(6))
		self.inode_next = FIL_ADDR(self.read(6))
		self.inode_pre_page = self.inode_pre.FIL_ADDR_PAGE
		self.inode_pre_page_offset = self.inode_pre.FIL_ADDR_BYTE
		self.inode_next_page = self.inode_next.FIL_ADDR_PAGE
		self.inode_next_page_offset = self.inode_next.FIL_ADDR_BYTE
		if self.inode_next_page == 4294967295:
			self.EXTRA_PAGE = False


	def _segment(self):
		return {
			'FSEG_ID':self.read_uint8(),
			'FSEG_NOT_FULL_N_USED':self.read_uint4(),
			'FSEG_FREE':FLST_BASE_NODE(self.read(16)),
			'FSEG_NOT_FULL':FLST_BASE_NODE(self.read(16)),
			'FSEG_FULL':FLST_BASE_NODE(self.read(16)),
			'FSEG_MAGIC':self.read_uint4(),
			'FSEG_FRAG_ARR':[ self.read_uint4() for _ in range(32) ] #FSEG_FRAG_SLOT_SIZE = 4
			}

	def _init_segment(self):
		if not self.MYSQL5: # fix issue 17   mysql57没得sdi信息, 就不用去掉第一个index了
			self.FSEG_SDI = (self._segment(),self._segment())
		self.FSEG = [] #(non_leaf_page, leaf_page)
		for x in range(85):
			_fseg = self._segment()
			if _fseg['FSEG_ID'] and _fseg['FSEG_MAGIC'] == 97937874:
				self.FSEG.append(_fseg)
			else:
				break
		index_page = []
		for x in range(int(len(self.FSEG)/2)):
			index_page.append( (self.FSEG[x*2]['FSEG_FRAG_ARR'][0], self.FSEG[x*2+1]['FSEG_FRAG_ARR'][0]) )

		self.index_page = index_page #if leaf_page = -1 , it means NO LEAF PAGE

