from b2data import *
import sys
def test_time():
	data = [
		[(b'\x80\xc8\xb8\x00\x00\x00',5), '12:34:56.00000'],
		[(b'\x7f7H\x00\x00\x00',5),'-12:34:56.00000'],
		[(b'\x80\xc8\xb8\x01\xe0x',5),'12:34:56.12300'],
		[(b'\x80\xc8\xb8\x0fB6',5),'12:34:56.99999'],
		[(b'\x7f7G\xfe\x1f\x88',5),'-12:34:56.12300'],
		[(b'\x7f7G\xf0\xbd\xca',5),'-12:34:56.99999']
	]
	for x in data:
		if B2TIME(*x[0]) == repr(x[1]):
			print('PASS')
		else:
			sys.stdout.write('FAILD'+B2TIME(*x[0])+x[1]+'\n')
test_time()
