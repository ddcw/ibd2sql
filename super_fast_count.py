#!/usr/bin/env python
# -*- coding: utf-8 -*-
# write by ddcw @https://github.com/ddcw
# 快速统计表行数的脚本

import os
import sys
import struct
import time

# 一些变量的初始化
PAGE_SIZE = 16384

# 后面内容就不可以修改了哈
FSP_EXTENT_SIZE = 1048576//PAGE_SIZE if PAGE_SIZE <= 16384 else 2097152//PAGE_SIZE if PAGE_SIZE <= 32768 else 4194304//PAGE_SIZE
XDES_COUNT = PAGE_SIZE//FSP_EXTENT_SIZE
XDES_SIZE = 24 + (FSP_EXTENT_SIZE*2+7)//8

argv = sys.argv
def USAGE():
	sys.stdout.write('\nUSAGE: python super_fast_count.py xxx.ibd\n')
	sys.exit(1)





if len(argv) != 2:
	USAGE()

filename = sys.argv[1]
if not os.path.exists(filename):
	sys.stdout.write(str(filename)+" is not exists\n")
	USAGE()

MAX_PAGE_ID = os.path.getsize(filename)//PAGE_SIZE
starttime = time.time()
with open(filename,'rb') as f:
	# 获取first leaf pageid, 本来可以使用ibd2sql去做的, 但为了兼容性, 就单独来做吧..
	fsp_data = f.read(PAGE_SIZE) # FSP, 要判断是否是8.x, 主要是有个SDI信息占了2 sgement
	f.seek(2*PAGE_SIZE)
	# fil_hedaer + space_header + XDES + keyring(+4)
	offset = 38 + 112 + XDES_COUNT*XDES_SIZE + 115
	HAVE_SDI = 0
	if fsp_data[offset:offset+4] == b'\x00\x00\x00\x01':
		HAVE_SDI = 1
	data = f.read(PAGE_SIZE)  # inode
	if data[24:26] != b'\x00\x03':
		sys.stdout.write(str(filename)+" is not ibd file\n")
		USAGE()

	offset = 38 + 12 + 192*2*HAVE_SDI + 192
	leaf_page_seg = data[offset:offset+192]
	PAGE_ID = 4294967295
	for x in struct.unpack('>32L',leaf_page_seg[64:192]):
		if x != 4294967295:
			PAGE_ID = x
			break
	# 开始遍历
	#OLD_NEXT_PAGE_NO = 0
	ROW_COUNT = 0
	while True:
		if PAGE_ID == 4294967295 or PAGE_ID > MAX_PAGE_ID:
			break
		f.seek(PAGE_ID*PAGE_SIZE)
		#OLD_NEXT_PAGE_NO = PAGE_ID
		data = f.read(PAGE_SIZE)
		PAGE_ID = struct.unpack('>4LQHQ',data[:34])[3] # FIL_PAGE_NEXT
		ROW_COUNT += struct.unpack('>9HQHQ',data[38:][:36])[-4] # PAGE_N_RECS
	stoptime = time.time()
	filesize = str(round(MAX_PAGE_ID*PAGE_SIZE/1024/1024/1024,2))+' GB'
	costtime = str(round(stoptime-starttime,2))+' seconds'
	sys.stdout.write('TOTAL ROWS: '+str(ROW_COUNT)+'\tCOST TIME: '+costtime+'\tFILESIZE:'+filesize+'\n')
