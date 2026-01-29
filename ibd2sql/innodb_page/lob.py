import struct
import zlib

# FIL_PAGE_TYPE_ZBLOB
def FIRST_ZBLOB(pg,pageno):
	rdata = b''
	d = zlib.decompressobj()
	while True:
		data = pg.read(pageno)
		pre,nex = struct.unpack('>LL',data[8:16])
		rdata += d.decompress(data[38:])
		if nex == 4294967295:
			break
		else:
			pageno = nex
	return rdata

def FIRST_BLOB(pg,pageno):
	"""
	INPUT:
		pg: page reader
		pageno: page number
	RETURN:
		binary data of blob
	"""
	firstpagno = pageno
	data = pg.read(firstpagno)
	entry = data[96:96+60]
	rdata = b''
	while True:
		if len(entry) < 12:
			break
		pageno,datalen,lobversion = struct.unpack('>3L',entry[-12:])
		datalen = datalen>>16
		if pageno == 0:
			break
		elif pageno == firstpagno:
			rdata += data[696:696+datalen]
		else:
			rdata += pg.read(pageno)[49:49+datalen]
		next_entry_pageno,next_entry_offset = struct.unpack('>LH',entry[6:12])
		if next_entry_pageno >0 and next_entry_pageno < 4294967295:
			entry = pg.read(next_entry_pageno)[next_entry_offset:next_entry_offset+60]
		else:
			break
	return rdata
