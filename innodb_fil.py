import page_type
import struct

PAGE_SIZE = 16384

innodb_page_name = {}
for x in dir(page_type):
	if x[:2] != '__':
		innodb_page_name[getattr(page_type,x)] = x

class page(object):
	def __init__(self,bdata):
		self.FIL_PAGE_SPACE_OR_CHKSUM, self.FIL_PAGE_OFFSET, self.FIL_PAGE_PREV, self.FIL_PAGE_NEXT, self.FIL_PAGE_LSN, self.FIL_PAGE_TYPE, self.FIL_PAGE_FILE_FLUSH_LSN = struct.unpack('>4LQHQ',bdata[:34])
		self.FIL_PAGE_SPACE_ID = struct.unpack('>L',bdata[34:38])[0]

		self.CHECKSUM, self.FIL_PAGE_LSN = struct.unpack('>2L',bdata[-8:])

def page_summary(filename,page_size=16384):
	pages = {}
	for x in innodb_page_name:
		pages[x] = 0
	with open(filename,'rb') as f:
		while True:
			bdata = f.read(page_size)
			if bdata == b'':
				break
			data = page(bdata)
			pages[data.FIL_PAGE_TYPE] += 1
	rpages = {}
	for x in pages:
		if pages[x] > 0:
			rpages[innodb_page_name[x]] = pages[x]
	return rpages


