# write by ddcw @https://github.com/ddcw/ibd2sql:
import struct
def first_blob(f,pageno): # 这名字取得... 简单点吧
	"""
	input: f:  file desc  pageno FIL_PAGE_TYPE_LOB_FIRST NO
	output: binarydata
	"""
	firstpagno = pageno
	f.seek(pageno*16384,0)
	data = f.read(16384)
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
			f.seek(pageno*16384,0)
			rdata += f.read(16384)[49:49+datalen]
			#rdata += read_page(pageno)[39:39+datalen]
		next_entry_pageno,next_entry_offset = struct.unpack('>LH',entry[6:12])
		if next_entry_pageno >0 and next_entry_pageno < 4294967295:
			f.seek(next_entry_pageno*16384,0)
			entry = f.read(16384)[next_entry_offset:next_entry_offset+60]
		else:
			break
	return rdata

