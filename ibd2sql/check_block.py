import os
from ibd2sql.utils.crc32c import *
def check_block(filename,PAGE_SIZE):
	HAVE_BAD_BLOCK = False
	with open(filename,'rb') as f:
		for pageid in range(os.path.getsize(filename)//PAGE_SIZE):
			if not CHECK_PAGE(f.read(PAGE_SIZE)):
				HAVE_BAD_BLOCK = True
				print('BAD PAGE NO:',pageid)
	if not HAVE_BAD_BLOCK:
		print('NO BAD PAGE.')
