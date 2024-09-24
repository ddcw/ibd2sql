# write by ddcw @https://github.com/ddcw
# lz4解压(fast)
# 参考: https://github.com/lz4/lz4/blob/dev/doc/lz4_Block_format.md

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

# lz4压缩(TODO)
def compress(bdata):
	"""
	input:	bdata: 要压缩的数据
	return: data:  压缩之后的数据
	"""
	return bdata


# lz4解压
def decompress(bdata,decompress_size):
	"""
	input:
		bdata: 压缩数据
		decompress_size : 解压之后的大小
	return: data 解压之后的数据
	不考虑dict和prefix_size了
	"""
	def read_to_less255(tdata,ip):
		length = 0
		while True:
			#t = struct.unpack('<B',aa[ip:ip+1])[0]
			t = tdata[ip]
			ip += 1
			length += t
			if t != 255: # 小于255时,就读完了
				break
		return length,ip
		
	ip = 0 # input pointer  (bdata的指针)
	op = 0 # output pointer (data的指针)
	data = bytearray(decompress_size) # 要返回的数据有这么大
	
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
			if op == decompress_size: # 解压完了, 因为可能没得后面的match部分
				break
			else:
				raise ValueError('Invalid lz4 compress data.')
		#offset = struct.unpack('<H',bdata[ip:ip+2])[0]
		offset = (bdata[ip+1]<<8) | bdata[ip] # 位移真TM好用
		ip += 2
		ml = token & 15 # 后4bit是match length
		if ml == 15:
			tml,ip = read_to_less255(bdata,ip)
			ml += tml
		ml += 4 # 还得加4(minmatch)
		match = op - offset
		data[op:op+ml] = data[match:match+ml] # match实际上是指的原始数据位置的数据,而不是压缩之后的数据位置
		op += ml # 重复的数据只需要移动op就行,ip那没得要移动的.(match部分已经mv了)
	return bytes(data)

