import struct
UT_HASH_RANDOM_MASK  = 1463735687
UT_HASH_RANDOM_MASK2 = 1653893711
FIL_PAGE_OFFSET = 4
FIL_PAGE_FILE_FLUSH_LSN = 26
FIL_PAGE_DATA = 38
FIL_PAGE_END_LSN_OLD_CHKSUM = 8
def ut_fold_ulint_pair(n1,n2):
	return(((((n1 ^ n2 ^ UT_HASH_RANDOM_MASK2) << 8) + n1) ^ UT_HASH_RANDOM_MASK) + n2)

def ut_fold_binary(data):
	fold = 0
	for i in range(len(data)):
		fold = ut_fold_ulint_pair(fold, data[i])
	return fold

def calc_page_new_checksum(data):
	checksum = ut_fold_binary(data[4:26])+ut_fold_binary(data[38:-8])
	return checksum&0xFFFFFFFF

def CHECK_PAGE_OLD(data):
	if data[:4] == b'\x00\x00\x00\x00':
		return True
	else:
		return struct.unpack('>L',data[:4])[0] == calc_page_new_checksum(data)
