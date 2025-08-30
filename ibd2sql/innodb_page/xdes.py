import struct

def GET_XDES_SIZE_COUNT(pagesize):
	FSP_EXTENT_SIZE = 1048576//pagesize if pagesize <= 16384 else 2097152//pagesize if pagesize <= 32768 else 4194304//pagesize
	XDES_COUNT = pagesize//FSP_EXTENT_SIZE
	XDES_SIZE = 24 + (FSP_EXTENT_SIZE*2+7)//8
	return XDES_SIZE,XDES_COUNT

class XDES(object):
	def __init__(self,data):
		self.data = data
		self.PAGE_SIZE = len(data)
		self.XDES_SIZE,self.XDES_COUNT = GET_XDES_SIZE_COUNT(self.PAGE_SIZE)
		self.init()

	def init(self):
		offset = 38
		xdes = []
		for x in range(self.XDES_COUNT):
			data = self.data[offset+i*self.XDES_SIZE:offset+i*self.XDES_SIZE+self.XDES_SIZE]
			xdes.append({
				'XDES_ID':struct.unpack('>Q',data[:8]),
				'XDES_FLST_NODE':struct.unpack('>LHLH',data[8:20]),
				'XDES_STATE':struct.unpack('>L',data[20:24]),
				'XDES_BITMAP':data[24:]
			})

