import struct
import sys,os
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

			
def calculate_crc32c(data):
	crc = 0xFFFFFFFF
	for byte in data:
		crc = crc32_slice_table[(crc ^ byte) & 0xFF] ^ (crc >> 8)
	return crc ^ 0xFFFFFFFF

crc32_slice_table = create_crc32c_table()
crc32c = calculate_crc32c
