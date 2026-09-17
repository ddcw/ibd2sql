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

def FIRST_BLOB(pg,pageno,real_size=None):
	"""
	INPUT:
		pg: page reader
		pageno: page number
		real_size: BTR_EXTERN_LEN value from the clustered record
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
			# FIL_PAGE_DATA is offset 38 and the uncompressed LOB page
			# header is 8 bytes, so LOB payload starts at offset 46.
			lob_page = pg.read(pageno)
			rdata += lob_page[49:49+datalen]
		next_entry_pageno,next_entry_offset = struct.unpack('>LH',entry[6:12])
		if next_entry_pageno >0 and next_entry_pageno < 4294967295:
			entry = pg.read(next_entry_pageno)[next_entry_offset:next_entry_offset+60]
		else:
			break

	if real_size is not None and len(rdata) != real_size:
		raise ValueError(
			f"LOB size mismatch: expected {real_size} bytes, got {len(rdata)} bytes"
		)
	return rdata
