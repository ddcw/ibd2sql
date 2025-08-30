import struct
def READ_KEYRING(data):
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
