from ibd2sql.innodb_page.page import PAGE
import struct
import zlib
# row_format = compressed
def PAGE_ZIP_DECOMPRESS(data,isleaf=True,ispk=True):
	"""
	INPUT:  bdata (compressed page)
	RETURN: data (decompressed page)
	"""
	# fil_header + page_header
	unpage = data[:94]
	# number of records on the page
	n_dense = struct.unpack('>H',data[42:44])[0] & 32767
	n_recs = struct.unpack('>H',data[54:56])[0]
	# infimum & supremum
	unpage += struct.pack('>BBB',0x01,0x00,0x02)
	unpage += data[-2:]
	unpage += struct.pack('>8B',0x69, 0x6e, 0x66, 0x69, 0x6d, 0x75, 0x6d, 0x00)
	unpage += b'\x03'
	unpage += struct.pack('>12B',0x00,0x0b,0x00,0x00,0x73,0x75,0x70,0x72,0x65,0x6d,0x75,0x6d)
	# decompress data
	d = zlib.decompressobj()
	c = d.decompress(data[94:])
	toffset = c.find(b'\x01') + 1
	unpage += c[toffset:]
	compressed_offset = len(unpage) + 120
	# uncompressed data
	unpage += d.unused_data
	dataobj = PAGE()
	dataobj.init(unpage)
	dataobj._offset = len(data)
	dd = []
	page_dir = []
	# page_dir & rec_header
	for x in range(n_recs): # used record
		slot = struct.unpack('>H',dataobj.read_reverse(2))[0]
		deleted = False
		owned = False 
		if slot > 16384:
			owned = True
			slot -= 16384
			page_dir.append(slot)
		dd.append([slot,deleted,owned,slot])
	for j in range(n_dense-n_recs-2): # user record deleted
		slot = struct.unpack('>H',dataobj.read_reverse(2))[0]
		deleted = True
		owned = False 
		if slot > 16384:
			owned = True
			slot -= 16384
			page_dir.append(slot)
		dd.append([slot,deleted,owned,slot])
	_ = dd.sort()
	# trxid&rollptr
	trxid_rollptr = []
	for x in range(n_dense-2):
		trxid_rollptr.append(dataobj.read_reverse(13))
	# big char PASS
	# index
	offset = 0
	dataobj.offset = 0
	rdata = b''
	for x in range(len(dd)):
		c_offset = dd[x][0] - 5
		if compressed_offset < c_offset:
			c_offset += 1 if x < 64 else 2
		r_offset = c_offset - offset
		offset = c_offset
		rdata += dataobj.read(r_offset)
		rdata += b'\x00'*5 # record header
		rdata += b'\x00'*13 # rollptr
	return rdata
