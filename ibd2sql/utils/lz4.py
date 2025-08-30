# write by ddcw @https://github.com/ddcw/ibd2sql
# lz4 decompress (fast)
# references : https://github.com/lz4/lz4/blob/dev/doc/lz4_Block_format.md

"""
LZ4 compressed block is composed of sequences.
sequence = token + [length literals] +  literals + offset + [length match] + match
token: 1bytes, first 4-bits   length of literals
               last  4-bits   length of match
               each field ranges from 0 to 15, when 15, read more 1 bytes for length to add
literals: not-compressed bytes
offset  : 从解压后的数据的某个位置开始复制 match长度的数据
match   : 要复制的数据的长度
"""

# lz4 compress (TODO)
def compress(bdata):
	"""
	input:	bdata: 要压缩的数据
	return: data:  压缩之后的数据
	"""
	return bdata


# lz4 decompress
def decompress(bdata,decompress_size):
	"""
	input:
		bdata: compressed data
		decompress_size : decompress size
	return: data of decompressed
	ignore dict & prefix_size
	"""
	def read_to_less255(tdata,ip):
		length = 0
		while True:
			t = tdata[ip]
			ip += 1
			length += t
			if t != 255:
				break
		return length,ip
		
	ip = 0 # input pointer
	op = 0 # output pointer
	data = bytearray(decompress_size)
	
	while True:
		token = bdata[ip]
		ip += 1
		ll = token >> 4 # literals length
		if ll == 15:
			tll,ip = read_to_less255(bdata,ip)
			ll += tll
		data[op:op+ll] = bdata[ip:ip+ll] # literals 不可压缩的部分
		op += ll
		ip += ll
		if decompress_size-op < 12:
			if op == decompress_size:
				break
			else:
				raise ValueError('Invalid lz4 compress data.')
		offset = (bdata[ip+1]<<8) | bdata[ip]
		ip += 2
		ml = token & 15
		if ml == 15:
			tml,ip = read_to_less255(bdata,ip)
			ml += tml
		ml += 4
		match = op - offset
		data[op:op+ml] = data[match:match+ml]
		op += ml
	return bytes(data)

