import struct
def create_crc32c_table():
    poly = 0x82f63b78
    table = []
    for i in range(256):
        crc = i
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ poly
            else:
                crc >>= 1
        table.append(crc)
    return table
crc32_slice_table = create_crc32c_table()
def calculate_crc32c(data):
	crc = 0xFFFFFFFF
	for byte in data:
		crc = crc32_slice_table[(crc ^ byte) & 0xFF] ^ (crc >> 8)
	return crc ^ 0xFFFFFFFF


def CHECK_PAGE(data):
	if data[:4] == b'\x00\x00\x00\x00'  and data[26:28] == b'\x00\x00':
		return True
	checksum_field1 = struct.unpack('>L',data[:4])[0]
	checksum_field2 = struct.unpack('>L',data[-8:-4])[0]
	c1 = calculate_crc32c(data[4:26])
	c2 = calculate_crc32c(data[38:-8])
	return True if checksum_field1 == checksum_field2 == (c1^c2)&(2**32-1) else False

def REPACK_PAGE(data):
	c1 = calculate_crc32c(data[4:26])
	c2 = calculate_crc32c(data[38:-8])
	c3 = struct.pack('>L',(c1^c2)&(2**32-1))
	return c3 + data[4:-8] + c3 + data[-4:]
