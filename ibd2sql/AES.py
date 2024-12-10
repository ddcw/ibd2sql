# aes ecb&cbc解密
# 参考: 
#      https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.197-upd1.pdf
#      https://github.com/ricmoo/pyaes

# Substitution Box
Sbox = [ 0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5, 0x30, 0x01, 0x67, 0x2b, 0xfe, 0xd7, 0xab, 0x76, 0xca, 0x82, 0xc9, 0x7d, 0xfa, 0x59, 0x47, 0xf0, 0xad, 0xd4, 0xa2, 0xaf, 0x9c, 0xa4, 0x72, 0xc0, 0xb7, 0xfd, 0x93, 0x26, 0x36, 0x3f, 0xf7, 0xcc, 0x34, 0xa5, 0xe5, 0xf1, 0x71, 0xd8, 0x31, 0x15, 0x04, 0xc7, 0x23, 0xc3, 0x18, 0x96, 0x05, 0x9a, 0x07, 0x12, 0x80, 0xe2, 0xeb, 0x27, 0xb2, 0x75, 0x09, 0x83, 0x2c, 0x1a, 0x1b, 0x6e, 0x5a, 0xa0, 0x52, 0x3b, 0xd6, 0xb3, 0x29, 0xe3, 0x2f, 0x84, 0x53, 0xd1, 0x00, 0xed, 0x20, 0xfc, 0xb1, 0x5b, 0x6a, 0xcb, 0xbe, 0x39, 0x4a, 0x4c, 0x58, 0xcf, 0xd0, 0xef, 0xaa, 0xfb, 0x43, 0x4d, 0x33, 0x85, 0x45, 0xf9, 0x02, 0x7f, 0x50, 0x3c, 0x9f, 0xa8, 0x51, 0xa3, 0x40, 0x8f, 0x92, 0x9d, 0x38, 0xf5, 0xbc, 0xb6, 0xda, 0x21, 0x10, 0xff, 0xf3, 0xd2, 0xcd, 0x0c, 0x13, 0xec, 0x5f, 0x97, 0x44, 0x17, 0xc4, 0xa7, 0x7e, 0x3d, 0x64, 0x5d, 0x19, 0x73, 0x60, 0x81, 0x4f, 0xdc, 0x22, 0x2a, 0x90, 0x88, 0x46, 0xee, 0xb8, 0x14, 0xde, 0x5e, 0x0b, 0xdb, 0xe0, 0x32, 0x3a, 0x0a, 0x49, 0x06, 0x24, 0x5c, 0xc2, 0xd3, 0xac, 0x62, 0x91, 0x95, 0xe4, 0x79, 0xe7, 0xc8, 0x37, 0x6d, 0x8d, 0xd5, 0x4e, 0xa9, 0x6c, 0x56, 0xf4, 0xea, 0x65, 0x7a, 0xae, 0x08, 0xba, 0x78, 0x25, 0x2e, 0x1c, 0xa6, 0xb4, 0xc6, 0xe8, 0xdd, 0x74, 0x1f, 0x4b, 0xbd, 0x8b, 0x8a, 0x70, 0x3e, 0xb5, 0x66, 0x48, 0x03, 0xf6, 0x0e, 0x61, 0x35, 0x57, 0xb9, 0x86, 0xc1, 0x1d, 0x9e, 0xe1, 0xf8, 0x98, 0x11, 0x69, 0xd9, 0x8e, 0x94, 0x9b, 0x1e, 0x87, 0xe9, 0xce, 0x55, 0x28, 0xdf, 0x8c, 0xa1, 0x89, 0x0d, 0xbf, 0xe6, 0x42, 0x68, 0x41, 0x99, 0x2d, 0x0f, 0xb0, 0x54, 0xbb, 0x16 ]

# Inverse Substitution Box
I_Sbox = [ 0x52, 0x09, 0x6a, 0xd5, 0x30, 0x36, 0xa5, 0x38, 0xbf, 0x40, 0xa3, 0x9e, 0x81, 0xf3, 0xd7, 0xfb, 0x7c, 0xe3, 0x39, 0x82, 0x9b, 0x2f, 0xff, 0x87, 0x34, 0x8e, 0x43, 0x44, 0xc4, 0xde, 0xe9, 0xcb, 0x54, 0x7b, 0x94, 0x32, 0xa6, 0xc2, 0x23, 0x3d, 0xee, 0x4c, 0x95, 0x0b, 0x42, 0xfa, 0xc3, 0x4e, 0x08, 0x2e, 0xa1, 0x66, 0x28, 0xd9, 0x24, 0xb2, 0x76, 0x5b, 0xa2, 0x49, 0x6d, 0x8b, 0xd1, 0x25, 0x72, 0xf8, 0xf6, 0x64, 0x86, 0x68, 0x98, 0x16, 0xd4, 0xa4, 0x5c, 0xcc, 0x5d, 0x65, 0xb6, 0x92, 0x6c, 0x70, 0x48, 0x50, 0xfd, 0xed, 0xb9, 0xda, 0x5e, 0x15, 0x46, 0x57, 0xa7, 0x8d, 0x9d, 0x84, 0x90, 0xd8, 0xab, 0x00, 0x8c, 0xbc, 0xd3, 0x0a, 0xf7, 0xe4, 0x58, 0x05, 0xb8, 0xb3, 0x45, 0x06, 0xd0, 0x2c, 0x1e, 0x8f, 0xca, 0x3f, 0x0f, 0x02, 0xc1, 0xaf, 0xbd, 0x03, 0x01, 0x13, 0x8a, 0x6b, 0x3a, 0x91, 0x11, 0x41, 0x4f, 0x67, 0xdc, 0xea, 0x97, 0xf2, 0xcf, 0xce, 0xf0, 0xb4, 0xe6, 0x73, 0x96, 0xac, 0x74, 0x22, 0xe7, 0xad, 0x35, 0x85, 0xe2, 0xf9, 0x37, 0xe8, 0x1c, 0x75, 0xdf, 0x6e, 0x47, 0xf1, 0x1a, 0x71, 0x1d, 0x29, 0xc5, 0x89, 0x6f, 0xb7, 0x62, 0x0e, 0xaa, 0x18, 0xbe, 0x1b, 0xfc, 0x56, 0x3e, 0x4b, 0xc6, 0xd2, 0x79, 0x20, 0x9a, 0xdb, 0xc0, 0xfe, 0x78, 0xcd, 0x5a, 0xf4, 0x1f, 0xdd, 0xa8, 0x33, 0x88, 0x07, 0xc7, 0x31, 0xb1, 0x12, 0x10, 0x59, 0x27, 0x80, 0xec, 0x5f, 0x60, 0x51, 0x7f, 0xa9, 0x19, 0xb5, 0x4a, 0x0d, 0x2d, 0xe5, 0x7a, 0x9f, 0x93, 0xc9, 0x9c, 0xef, 0xa0, 0xe0, 0x3b, 0x4d, 0xae, 0x2a, 0xf5, 0xb0, 0xc8, 0xeb, 0xbb, 0x3c, 0x83, 0x53, 0x99, 0x61, 0x17, 0x2b, 0x04, 0x7e, 0xba, 0x77, 0xd6, 0x26, 0xe1, 0x69, 0x14, 0x63, 0x55, 0x21, 0x0c, 0x7d ]

# Round Constants
Rcon = [ 0x00000000, 0x01000000, 0x02000000, 0x04000000, 0x08000000, 0x10000000, 0x20000000, 0x40000000, 0x80000000, 0x1b000000, 0x36000000, 0x6c000000, 0xd8000000, 0xab000000, 0x4d000000, 0x9a000000, 0x2f000000, 0x5e000000, 0xbc000000, 0x63000000, 0xc6000000, 0x97000000, 0x35000000, 0x6a000000, 0xd4000000, 0xb3000000, 0x7d000000, 0xfa000000, 0xef000000, 0xc5000000, 0x91000000, 0x39000000, ]

# 基础操作 
# GF(2^8)
def GMul(a,b):
	p = 0
	for _ in range(8):
		if b & 1:
			p ^= a
		hi_bit_set = a & 0x80
		a <<= 1
		a &= 0xff
		if hi_bit_set:
			a ^= 0x1b
		b >>= 1
	return p

# RotWord ([1,2,3,4] --> [2,3,4,1])
def RotWord(word):
	return word[1:] + word[:1]

# SubWord
def SubWord(word):
	return [ Sbox[x] for x in word ]

def KeyExpansion(key):
	key_symbols = [ x for x in key ]
	Nb = 4
	Nk = 8  
	Nr = 14 #轮数, 128:10 192:12 256:14  只支持32bytes情况
	w = [0] * Nb * (Nr + 1)
	for x in range(Nk):
		w[x] = key_symbols[ 4*x : 4*(x+1) ]
	for i in range(Nk, Nb*(Nr+1)):
		temp = w[ i-1 ][:]
		if i % Nk == 0:
			temp = SubWord(RotWord(temp))
			temp[0] ^= Rcon[i // Nk] >> 24
		elif Nk > 6 and i % Nk == 4:
			temp = SubWord(temp)
		w[i] = [w_i ^ t_i for w_i, t_i in zip(w[i - Nk], temp)]
	return w

def AddRoundKey(state,w):
	for i in range(4):
		for j in range(4):
			state[j][i] ^= w[i][j]
	return state

def InvSubBytes(s):
	for i in range(4):
		for j in range(4):
			s[i][j] = I_Sbox[s[i][j]]
	return s

# 位移 ([0,1,2,3] --> [3,0,1,2])
def InvShiftRows(s):
	s[1][0], s[1][1], s[1][2], s[1][3] = s[1][3], s[1][0], s[1][1], s[1][2]
	s[2][0], s[2][1], s[2][2], s[2][3] = s[2][2], s[2][3], s[2][0], s[2][1]
	s[3][0], s[3][1], s[3][2], s[3][3] = s[3][1], s[3][2], s[3][3], s[3][0]
	return s

def InvMixColumns(s):
	for i in range(4):
		a = s[0][i]
		b = s[1][i]
		c = s[2][i]
		d = s[3][i]
		s[0][i] = GMul(a,14) ^ GMul(b,11) ^ GMul(c,13) ^ GMul(d,9)	
		s[1][i] = GMul(a,9) ^ GMul(b,14) ^ GMul(c,11) ^ GMul(d,13)
		s[2][i] = GMul(a,13) ^ GMul(b,9) ^ GMul(c,14) ^ GMul(d,11)
		s[3][i] = GMul(a,11) ^ GMul(b,13) ^ GMul(c,9) ^ GMul(d,14)
	return s

# AES解密
def AESDecrypt(block,key_schedule):
	Nb = 4
	Nr = len(key_schedule) // Nb - 1
	#state = [[0]*4]*4 # 这TM是引用...
	state = [[0] * 4 for _ in range(4)]
	for i in range(4):
		for j in range(4):
			state[j][i] = block[i*4 + j]
	state = AddRoundKey(state, key_schedule[Nr*Nb : (Nr+1)*Nb])
	for round in range(Nr-1, 0, -1):
		state = InvShiftRows(state)
		state = InvSubBytes(state)
		state = AddRoundKey(state, key_schedule[round*Nb : (round+1)*Nb])
		state = InvMixColumns(state)
	# 最后一轮比较特殊
	state = InvShiftRows(state)
	state = InvSubBytes(state)
	state = AddRoundKey(state, key_schedule[0 : Nb])
	decrypted_block = []
	for i in range(4):
		for j in range(4):
			decrypted_block.append(state[j][i])
	return bytes(decrypted_block)

# AES加密
def AESEncrypt(block, key_schedule):
	pass

# 测试 ecb 256
def aes_ecb_256_encrypt(key,data):
	pass

# 对外接口
def aes_ecb256_decrypt(key,data):
	"""
	输入:
		key:   key
		data:  加密后的数据
	返回:
		rdata: 解密后的数据
	"""
	rdata = b''
	expanded_key = KeyExpansion(key)
	for i in range(0,len(data),16):
		rdata += AESDecrypt(data[i:i+16], expanded_key)
	return rdata

def aes_cbc256_decrypt(key,data,iv):
	"""
	输入:
		key:   key
		data:  加密后的数据
		iv:    向量
	返回:
		rdata: 解密后的数据
	"""
	rdata = b''
	expanded_key = KeyExpansion(key)
	pre_block = iv
	for i in range(0,int(len(data)/16)*16,16): # 不足16的,就忽略掉
		block = data[i:i+16]
		decrypted_block = AESDecrypt(block, expanded_key)
		# cbc就是多这么个亦或
		plaintext_block = bytes([d^p for d,p in zip(decrypted_block,pre_block)])
		pre_block = block
		rdata += plaintext_block
	return rdata
	
import struct
def read_keyring(data):
	offset = 24
	kd = {}
	xor_str = '*305=Ljt0*!@$Hnm(*-9-w;:'.encode()
	while True:
		if data[offset:offset+3] == b'EOF':
			break
		total_length, key_id_length, key_type_length, user_id_length, key_length = struct.unpack_from('<QQQQQ', data, offset)
		offset += 40
		key_id = data[offset:offset+key_id_length].decode()
		offset += key_id_length
		key_type = data[offset:offset+key_type_length].decode()
		offset += key_type_length
		user_id = data[offset:offset+user_id_length]
		offset += user_id_length
		key = data[offset:offset+key_length]
		keyt = bytes([key[i] ^ xor_str[i%24] for i in range(len(key))])
		offset += key_length
		kd[key_id] = {'key':keyt,'key_type':key_type}
		if offset % 8 != 0:
			offset += 8 - (offset % 8)
	return kd

# ECB模式测试数据
#key =  b'\x8b\x87\xa2z\x18\x92\x11\xb9\xa9\xae\xa84\x87\x98\xb2\x11\xe7\x1e\x9dB7\xd6\x94?\x80\xb5\xeb\x0e\xb8\xcbr\xf9'
#data = b'p\xfd\xd0`j\xb8_\x91\xee{\xb7\xba\xfb\x99\xb5\xd3\x00iD\xd8\xb4\x12\xbd\xb2vO\\\xde\x14\xeeK\xa2\x98\x97\xab\xb7\xe8]\x94\xe9\x14\x8fXk)%_yy\x96\x1a\xb8\xea\xde\x92BS\x1c\xb7O\x81\x92\xaa\x83'
#decrypt_data = b'\xa3\xdb\xab\xeci\x06\x0bz\xd2\\P\xe7k\xa7l\xeb\xe7?D\xf5\x96\xd4\xc8\x8c\x0e\x9c1\xf1yq\xdf\x01\xd7"\x15\x03\xb4\x18:\x15w\xff\xfcq\x92\xb4\x81[S\xcd\n\x84\xbc;\xe0\xa5Rw\xa7\x92r@*\x83'
#decrypt_data2 = aes_ecb256_decrypt(key,data)
#print(decrypt_data == decrypt_data2)
#

# CBC模式
#key_info = decrypt_data[:32]
#iv = decrypt_data[32:48]
#key_info = b'\xa3\xdb\xab\xeci\x06\x0bz\xd2\\P\xe7k\xa7l\xeb\xe7?D\xf5\x96\xd4\xc8\x8c\x0e\x9c1\xf1yq\xdf\x01'
#iv = b'\xd7"\x15\x03\xb4\x18:\x15w\xff\xfcq\x92\xb4\x81['
#en_data = b"\xe2\xcc\xd2\xd8\x97Mp\x19<c\x80U\x04\x8b\xb3J\xdfzr<\xb4-\xc7;X\x92\xd0{\x82\xe5Crw\x9eb\\\x11\x11F\xc4\x9b\xa99\xdej\xb7\xcd\x9d\xfe\xe2[.\xd9=\xaev\xd6\x92\xf9\xfc\x83\x8a!\xd0\x10v.\xc2:\x1c\x84\x18\xe5\xa41\x00\xaa\x90\x94\xf5'\x19 \x990hwP~w\xb6\xa5\xeab\xa3\xd9\xfbh\xd6O<\x16\xa8\xf7\xa5yp\xae\x1f1\xfd\xdd~\xf7X\xbfq}\xae\xb5\x99\x82\xf8Co7\xf8\xf7W\x06\xd2\x0ce\xff\xa22\x7f\xdf\xca\x0e:\xca\xa0\xe2\xfav\xf66\x17\x89\xe6\xd9\xd6\xe4\xc8q\xd3\xce(\x8f\xbfd"
#de_data = b'\x00\x02\x00\xb0\x80\x04\x00\x00\x00\x00\x00\x9b\x00\x02\x00\x01\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xdbu\x00\x00\xc2\x92\x00\x00\x00\x02\x02r\x00\x00\xc2\x92\x00\x00\x00\x02\x01\xb2\x01\x00\x02\x00\x1cinfimum\x00\x03\x00\x0b\x00\x00supremum\x04\x00\x00\x00\x10\x00\x1c\x80\x00\x00\x01\x00\x00\x03`\xc2\x86\x82\x00\x00\x029\x01\x10ddcw\x04\x00\x00\x00\x18\xff\xd5\x80\x00\x00\x02\x00\x00\x03`\xc2\x89\x82\x00\x00\x01\xb9\x01\x10ddcw\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
#de_data2 = aes_cbc256_decrypt(key_info,en_data,iv)
#print(de_data == de_data2)
#print(de_data)
#print(de_data2)
