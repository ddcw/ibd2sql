#!/usr/bin/env python3
# write by ddcw @https://github.com/ddcw
# 修改lower_canse_table_names的.
# 用法:
# python3 modify_lower_case_table_names.py mysql.ibd  # 查看当前的lower_case_table_names的值
# python3 modify_lower_case_table_names.py mysql.ibd newfilename.ibd 1 # 设置lower_case_table_names=1, 并保存到newfilename.ibd

import struct
import sys
import os
from ibd2sql.blob import first_blob

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

def useage():
	print(f"\n\tUsage: python3 {sys.argv[0]} /PATH/mysql.ibd # 查看")
	print(f"\tUsage: python3 {sys.argv[0]} /PATH/mysql.ibd /PATH/new_mysql.ibd 1 # 设置lower_case_table_names=1\n")
	sys.exit(0)

argv = sys.argv
if len(argv) not in [2,4]:
	useage()
filename = argv[1]
if not os.path.exists(filename):
	print(filename,'不存在啊!')
	sys.exit(1)

f = open(filename,'rb')
f.seek(4*16384,0)
data = f.read(16384)
offset = 99 + struct.unpack('>h',data[97:99])[0] + 13 + 10
pageid = struct.unpack('>L',data[offset:offset+4])[0] # LCTN所在的first_lob页
aa = first_blob(f,pageid)
aadict = dict([ x.split('=') for x in aa[:aa.find(b'\\')].decode().split(';')])

if len(argv) == 4: # 修改, 暂时不支持
	newfilename = argv[2]
	newvalue = int(argv[3])
	if newvalue not in [1,0]:
		print('lower_case_table_names取值范围是1或者0.')
		sys.exit(2)
	if os.path.exists(newfilename):
		print(newfilename,'不应该存在的.')
		sys.exit(3)
	f.seek(0,0)
	current_pageid = -1
	KEY = b'LCTN='+str(aadict['LCTN']).encode()
	with open(newfilename,'wb') as f2:
		while True:
			if data == b'':
				break
			current_pageid += 1
			data = f.read(16384)
			if current_pageid == pageid: # 只考虑LCTN在first_blob情况下的修改(因为懒...)
				_offset = data.find(KEY)
				data = data[:_offset+5] + str(newvalue).encode() + data[_offset+6:]
				c1 = calculate_crc32c(data[4:26])
				c2 = calculate_crc32c(data[38:16384-8])
				cb = struct.pack('>L',(c1^c2)&(2**32-1))
				data = cb + data[4:16384-8] + cb + data[16384-4:]
			f2.write(data)
	print(f'set lower_case_table_names={newvalue} into new file({newfilename}) finish.')

else: # 查看
	print('lower_case_table_names:',aadict['LCTN'])
f.close()
sys.exit(0)
