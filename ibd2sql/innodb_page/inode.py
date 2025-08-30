import struct

class INODE(object):
	"""
	INPUT:
		pg: page reader
		inode no: inode number, default 2
	RETURN:
		INODE LIST
	"""
	def __init__(self,pg,inodeno=2):
		self.pg = pg
		self.inodeno = inodeno
		self.seg = []
		self.init()

	def _segment(self,data):
		return {
			"FSEG_ID":struct.unpack('>Q',data[:8])[0],
			"FSEG_NOT_FULL_N_USED":struct.unpack('>L',data[8:12])[0],
			"FSEG_FREE":struct.unpack('>LLHLH',data[12:28]), # FLST_BASE_NODE_SIZE
			"FSEG_NOT_FULL":struct.unpack('>LLHLH',data[28:44]), # len=4 first: page=4 offset=2 last: page=4 offset=2
			"FSEG_FULL":struct.unpack('>LLHLH',data[44:60]),
			"FSEG_MAGIC":struct.unpack('>L',data[60:64])[0],
			"FSEG_FRAG_ARR":struct.unpack('>32L',data[64:192])
		}

	def init(self):
		nextpageno = self.inodeno
		while True:
			data = self.pg.read(nextpageno)
			INODE_PRE  = struct.unpack('>LH',data[38:44])
			INODE_NEXT = struct.unpack('>LH',data[44:50])
			nextpageno = INODE_NEXT[0]
			offset = 50
			for _ in range(self.pg.PAGE_SIZE//192//2):
				seg1 = self._segment(data[offset:offset+192]) # root node
				offset += 192
				seg2 = self._segment(data[offset:offset+192]) # first leaf node
				offset += 192
				if seg1['FSEG_MAGIC'] == 97937874:
					self.seg.append([seg1,seg2])
				else:
					break
			if nextpageno == 4294967295 or nextpageno == 0:
				break
