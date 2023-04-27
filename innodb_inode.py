#解析innodb 文件的 (8.0)
import struct

def flst(bdata):
	#FLST_NODE storage/innobase/include/fut0lst.ic #/* We define the field offsets of a node for the list */
	#FLST_PREV:6  FLST_NEXT:6
	FLST_PREV = struct.unpack('>LH',bdata[0:6])
	FLST_NEXT = struct.unpack('>LH',bdata[6:12])
	return (FLST_PREV,FLST_NEXT)

def flst_base(bdata):
	#FLST_BASE_NODE   storage/innobase/include/fut0lst.ic  #/* We define the field offsets of a base node for the list */
	#FLST_LEN:0-4  FLST_FIRST:4-(4 + FIL_ADDR_SIZE)  FLST_LAST:4+FIL_ADDR_SIZE:16
	#4+6+6
	#FIL_ADDR_SIZE = FIL_ADDR_PAGE(4) + FIL_ADDR_BYTE(2) #/** First in address is the page offset. */  Then comes 2-byte byte offset within page.*/
	FLST_LEN = struct.unpack('>L',bdata[:4])[0]
	FLST_FIRST = struct.unpack('>LH',bdata[4:10])
	FLST_LAST = struct.unpack('>LH',bdata[10:16])
	return (FLST_LEN,FLST_FIRST,FLST_LAST)
	
#storage/innobase/include/fsp0fsp.h
class inode(object):
	def __init__(self,bdata,FSP_EXTENT_SIZE=64): #按16384算,   1024*1024/16384 = 64 page
		i = 0
		lbdata = len(bdata)
		FLST_BASE_NODE_SIZE = 16
		FSEG_FRAG_ARR_N_SLOTS = int(FSP_EXTENT_SIZE / 2)
		FSEG_FRAG_SLOT_SIZE = 4
		FSEG_INODE_SIZE = 16 + 3*FLST_BASE_NODE_SIZE + FSEG_FRAG_ARR_N_SLOTS*FSEG_FRAG_SLOT_SIZE
		segment_list = []
		self.node_pre,self.node_next = flst(bdata[0:12])
		i += 12
		while True:
			if lbdata <= i+FSEG_INODE_SIZE-1:
				break
			FSEG_ID = struct.unpack('>Q',bdata[i:i+8])[0]
			if FSEG_ID == 0:
				i += FSEG_INODE_SIZE
				continue
			i += 8
			FSEG_NOT_FULL_N_USED = struct.unpack('>L',bdata[i:i+4])[0]
			i += 4
			FSEG_FREE = flst_base(bdata[i:i+FLST_BASE_NODE_SIZE])
			i += FLST_BASE_NODE_SIZE
			FSEG_NOT_FULL = flst_base(bdata[i:i+FLST_BASE_NODE_SIZE])
			i += FLST_BASE_NODE_SIZE
			FSEG_FULL = flst_base(bdata[i:i+FLST_BASE_NODE_SIZE])
			i += FLST_BASE_NODE_SIZE
			FSEG_MAGIC_N = bdata[i:i+4]
			i += 4
			FSEG_FRAG_ARR = [] #碎片页
			for x in range(FSEG_FRAG_ARR_N_SLOTS):
				FSEG_FRAG_ARR.append(struct.unpack('>L',bdata[i:i+FSEG_FRAG_SLOT_SIZE])[0])
				i += FSEG_FRAG_SLOT_SIZE
			segment_list.append({'FSEG_ID':FSEG_ID,'FSEG_NOT_FULL_N_USED':FSEG_NOT_FULL_N_USED,'FSEG_FREE':FSEG_FREE,'FSEG_NOT_FULL':FSEG_NOT_FULL,'FSEG_FULL':FSEG_FULL,'FSEG_MAGIC_N':FSEG_MAGIC_N,'FSEG_FRAG_ARR':FSEG_FRAG_ARR})
		self.segment_list = segment_list
		self.root_pages = [ x['FSEG_FRAG_ARR'][0] for x in segment_list ] #并非都是非叶子节点
		self.sdi_page = self.root_pages[0]
		self.index = []
		for x in range(1,int(len(self.root_pages)/2)):
			self.index.append({'no_leaf':self.root_pages[x*2],'leaf':self.root_pages[x*2+1]})

	def __str__(self,):
		return f'SEGMENT COUNTS:{len(self.segment_list)}  INDEX_COUNT:{len(self.index)}  INODE_PRE:{self.node_pre[0] if self.node_pre[0] != 4294967295 else None}  INODE_NEXT:{self.node_next[0] if self.node_next[0] != 4294967295 else None}'
