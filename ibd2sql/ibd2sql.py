import struct
import json
import glob
import sys
import os
from ibd2sql.innodb_page.sdi import SDI
from ibd2sql.innodb_page.page import PAGE
from ibd2sql.innodb_page.page import PAGE_READER
from ibd2sql.innodb_page.fsp import GET_FSP_STATUS_FROM_FLAGS
from ibd2sql.innodb_page.fsp import FSP
from ibd2sql.innodb_page.fsp import PARSE_ENCRYPTION_INFO
from ibd2sql.utils.keyring_file import READ_KEYRING
from ibd2sql.frm.frm2sdi import MYSQLFRM

from ibd2sql.innodb_page.inode import INODE
from ibd2sql.innodb_page.index import INDEX
from ibd2sql.innodb_page.table import TABLE

import ctypes
from multiprocessing import Process
from multiprocessing import Value
from multiprocessing import Lock

def GET_LEAF_PAGE_NO_FROM_SDI(pg,pageid):
	while True:
		data = pg.read(pageid)
		if data[64:66] == b'\x00\x00':
			break
		else:
			offset = 99
			offset += struct.unpack('>h',data[offset-2:offset])[0]
			dtype,table_id,pageid = struct.unpack('>LQL',data[offset:offset+16])
	return pageid

class IBDBASE(object):
	def __init__(self,filename,log,kd):
		self.status = False
		f = open(filename,'rb')
		data = f.read(1024)
		if len(data) != 1024:
			log.error(filename,'is too small ...')
			return None
		if data[24:26] != b'\x00\x08':
			log.info(f'{filename} version may be is too low') # 5.0 ?
			self.status = False
		FSP_SPACE_ID,FSP_NOT_USED,FSP_SIZE,FSP_FREE_LIMIT,FSP_SPACE_FLAGS,FSP_FRAG_N_USED = struct.unpack('>6L',data[38:62])
		self.fsp_flags = GET_FSP_STATUS_FROM_FLAGS(FSP_SPACE_FLAGS)

		self.logical_size = self.fsp_flags['logical_size']
		self.physical_size = self.fsp_flags['physical_size']
		self.page_size = self.physical_size
		self.compressed = self.fsp_flags['compressed']
		self.compression_ratio = self.logical_size//self.physical_size

		self.ENCRYPTION = True if self.fsp_flags['ENCRYPTION'] == 1 else False
		self.SDI = True if self.fsp_flags['SDI'] == 1 else False # True: >=8.0 False: <=5.7
		self.SHARED = True if self.fsp_flags['SHARED'] == 1 else False  # shared tablespace
		self.POST_ANTELOPE = self.fsp_flags['POST_ANTELOPE'] # innodb file format 0:compact/redundant 1:dynamic/compressed

		log.info(filename,'logical_size',self.logical_size)
		log.info(filename,'physical_size',self.physical_size)
		log.info(filename,'compressed',self.compressed)
		log.info(filename,'ENCRYPTION',self.ENCRYPTION)
		log.info(filename,'SDI',self.SDI)
		log.info(filename,'SHARED',self.SHARED)
		log.info(filename,'POST_ANTELOPE',self.POST_ANTELOPE)

		if os.path.getsize(filename)%self.physical_size != 0: # not faild
			log.warning(filename,'maybe have been damaged')

		f.seek(0,0)
		self.fsp = FSP(f.read(self.physical_size),self.logical_size,self.compression_ratio)
		f.close()

		self.key = None
		self.iv = None
		if self.ENCRYPTION:
			try:
				t = PARSE_ENCRYPTION_INFO(self.fsp.encryption_info,kd)
				self.key = t['key']
				self.iv = t['iv']
				log.info('key',self.key.hex())
				log.info('iv',self.iv.hex())
			except Exception as e:
				log.error(filename,'master_key not in',kd,'exception:',e)
				return None

		self.pg = PAGE_READER(page_size=self.physical_size,filename=filename,encryption=self.ENCRYPTION,key=self.key,iv=self.iv)
		self.sdi = None
		if self.SDI:
			#sdi = SDI(self.fsp.SDI_PAGE_NO,self.pg,'COMPRESSED' if self.compressed == 1 else '1')
			sdi = SDI(GET_LEAF_PAGE_NO_FROM_SDI(self.pg,self.fsp.SDI_PAGE_NO),self.pg,'COMPRESSED' if self.compressed == 1 else '1')
			try:
				self.sdi = sdi.get_sdi()
			except Exception as e:
				log.error(filename,'get sdi faild',e)
				return None

		self.status = True

	def test(self,):
		pass


def GET_PARTITION_TABLE_SDIDATA(filename_t,log,kd):
	filename_re = filename_t.split('#')[0] + "#" + "*.ibd"
	for filename in glob.glob(filename_re):
		if filename == filename_t:
			continue
		if os.path.isfile(filename):
			ibdbase = IBDBASE(filename,log,kd)
			if ibdbase.status:
				if ibdbase.sdi is not None and len(ibdbase.sdi) == 2:
					return ibdbase.sdi[0]
	return None

def FORMAT_IBD_FILE(filename_list,sdi_file,keyring_file,log):
	"""
	INPUT:
		filename_list: ibd/frm/sdi file list
		sdi_file: sdi file(ibd/frm/sdi)
		keyring_file: keyring filename
		log: log

	RETURN:
		[
			{
				'filename':xx,
				'sdi':sdi info (dict),
				'key':key,
				'iv':'iv',
				'pagesize': page size(phy),
				'partition_name':''
			},
		]
	"""

	kd = {}
	if keyring_file is not None:
		with open(keyring_file,'rb') as f:
			kd = READ_KEYRING(f.read())

	global_sdi_info = None
	if sdi_file is not None:
		if sdi_file.endswith('.frm'):
			log.info(sdi_file,'maybe frm')
			global_sdi_info = sdidata = json.loads(MYSQLFRM(sdi_file)._get_sdi_json())
			log.info(sdi_file,'global_sdi_info is frm file')
		elif sdi_file.endswith('.sdi'):
			log.info(sdi_file,'maybe sdi')
			with open(sdi_file,'r') as f:
				global_sdi_info = json.load(f)
			if len(global_sdi_info) == 3:
				global_sdi_info = global_sdi_info[1]
			log.info(sdi_file,'global_sdi_info is sdi file')
		elif sdi_file.endswith('.ibd'):
			log.info(sdi_file,'maybe ibd')
			ibdbase = IBDBASE(sdi_file,log,kd)
			global_sdi_info = ibdbase.sdi[0]

	file_list = []
	for filename in filename_list:
		if filename[-3:] != 'ibd':
			log.error(filename,'not endswith .ibd, skip it')
			continue
		ibdbase = IBDBASE(filename,log,kd)
		if (ibdbase is None or not ibdbase.status) and len(filename_list) > 1:
			log.error('skip file:',filename)
			continue

		partition_name = None
		sdidata = None
		if not ibdbase.status or not ibdbase.SDI: #and ibdbase.fsp.FIL_PAGE_PREV in [0,4294967295] and ibdbase.fsp.FIL_PAGE_NEXT in [0,4294967295]: # 5.x
			log.info(filename,'is mysql 5, will get sdi....',)
			partition_offset = filename.find('#')
			frm_filename = ''
			if partition_offset > 0:
				frm_filename = filename[:partition_offset]+'.frm'
				partition_name = filename[partition_offset:-4]
				log.info(filename,'is partition table')
			else:
				frm_filename = filename[:-4]+'.frm'
			if os.path.exists(frm_filename):
				log.info(filename,'will use frm file:',frm_filename)
				sdidata = json.loads(MYSQLFRM(frm_filename)._get_sdi_json())
				log.info(filename,'ADD TABLE',sdidata['dd_object']['schema_ref'],sdidata['dd_object']['name'])
			else:
				log.warning('frm file',frm_filename,'not exists')
				if global_sdi_info is not None:
					log.warning(filename,'use global_sdi_info',sdi_file)
					sdidata = global_sdi_info
				else:
					log.error(filename,'have not sdi info, skip it')
					continue
		elif ibdbase.fsp.FIL_PAGE_PREV > 80000 and ibdbase.fsp.FIL_PAGE_NEXT == 1: # 8.x
			log.info(filename,'mysql version:',ibdbase.fsp.FIL_PAGE_PREV)
			if ibdbase.SHARED: # such as : mysql.ibd
				log.info(filename,'is shared')
				for x in ibdbase.sdi:
					if 'dd_object' not in x or 'schema_ref' not in x['dd_object']:
						continue
					log.info(filename,'ADD TABLE',x['dd_object']['schema_ref'],x['dd_object']['name'])
					file_list.append({
						'filename':filename,
						'sdi':x,
						'encryption':ibdbase.ENCRYPTION,
						'key':ibdbase.key,
						'iv':ibdbase.iv,
						'pagesize':ibdbase.physical_size,
						'partition_name':partition_name,
						'fsp_flags':ibdbase.fsp_flags,
					})
				continue
			else:
				sdi_count = len(ibdbase.sdi)
				if sdi_count == 1: # partition
					log.info(filename,'is partition table',)
					sdidata = GET_PARTITION_TABLE_SDIDATA(filename,log,kd)
					if sdidata is None:
						if global_sdi_info is None:
							log.error(filename,'can not find sdi info, skip it')
							continue
						else:
							sdidata = global_sdi_info
							log.info(filename,'use global sdi',sdi_file)
					else:
						log.info(filename,'ADD TABLE',sdidata['dd_object']['schema_ref'],sdidata['dd_object']['name'])
				elif sdi_count == 2:
					if 'schema_ref' in ibdbase.sdi[0]['dd_object']:
						sdidata = ibdbase.sdi[0]
					else:
						sdidata = ibdbase.sdi[1]
			
					log.info(filename,'ADD TABLE',sdidata['dd_object']['schema_ref'],sdidata['dd_object']['name'])
				else:
					log.error('unknown error when read sdi',sdi_count)
					continue
		else:
			log.error('skip file',filename,ibdbase.SDI,ibdbase.fsp.FIL_PAGE_PREV,ibdbase.fsp.FIL_PAGE_NEXT)
			continue

		file_list.append({
			'filename':filename,
			'sdi':sdidata,
			'encryption':ibdbase.ENCRYPTION,
			'key':ibdbase.key,
			'iv':ibdbase.iv,
			'pagesize':ibdbase.physical_size,
			'partition_name':partition_name,
			'fsp_flags':ibdbase.fsp_flags,
		})
	return file_list

class IBD2SQL(object):
	def __init__(self,pg,pageid,force=False,v=None):
		self.pg = pg
		self.pageid = pageid
		self.pageid = pageid
		self.force = force
		self.v = v
		if force and v is None:
			self._read_page = self._read_page_add1
		elif force and v is not None:
			self._read_page = self._read_page_share_add1
		elif not force and v is None:
			pass
		elif not force and v is not None:
			self._read_page = self._read_page_share

	def read(self):
		data = self._read_page()
		if len(data) != self.pg.PAGE_SIZE:
			return False,data
		else:
			return True,data

	def _read_page(self,):
		data = self.pg.read(self.pageid)
		self.pageid = struct.unpack('>L',data[12:16])[0]
		return data

	def _read_page_share(self,): # parallel
		pass

	def _read_page_add1(self,): # force
		data = self.pg.read(self.pageid)
		self.pageid += 1
		return data

	def _read_page_share_add1(self,): # force & parallel
		pass

def FIND_LEAF_PAGE_FROM_ROOT(pg,pageid,table,page_type='PK_NON_LEAF',idxid=0):
	idx = INDEX()
	idx.init_index(table=table,idxid=idxid,pg=pg,page_type=page_type)
	while True:
		data = pg.read(pageid)
		if data[64:66] == b'\x00\x00':
			break
		idx.init_data(data)
		pageid = idx.get_all_rows()[0]['pageid']
	return pageid

def ROTAED_FILE(f,log,action='w'):
	filename = f.name
	findex = filename.find('.p0')
	f.close()
	if findex > 0 and len(filename[findex:]) == 10:
		newfilename = filename[:findex+2] + str(int(filename[findex+2:])+1).zfill(8)
	else:
		newfilename = filename + ".p00000001"
		os.rename(filename,filename + ".p00000000")
	log.info('rotate new file, name:',newfilename)
	newf = open(newfilename,action)
	return newf

def IBD2SQL_SINGLE(table,file_base,opt,filename_pre,log,parser):
	writed_size = 0 # rotaed
	writed_rows = 0
	usehex = True if 'hex' in opt else False
	if 'lines-terminated-by' in opt:
		enclosed_by = opt['lines-terminated-by']
	elif parser.SQL == 'data':
		enclosed_by = '\n'
	else:
		enclosed_by = ';\n'
	fields_terminated = opt['fields-terminated-by'] if 'fields-terminated-by' in opt else ','
	LIMIT = parser.LIMIT if parser.LIMIT is not None else -1 # limit
	OUTPUT_FILESIZE = parser.OUTPUT_FILESIZE
	FORCE = parser.FORCE
	HAVE_DATA = True
	HAVE_DELETED = False
	if parser.DELETED == 'only' or parser.DELETED == True:
		HAVE_DELETED = True
		HAVE_DATA = False
	if parser.DELETED == 'with':
		HAVE_DELETED = True
	PAGE_INDEX_ID = b'\x00'*8
	pg = PAGE_READER(page_size=file_base['pagesize'],filename=file_base['filename'],encryption=file_base['encryption'],key=file_base['key'],iv=file_base['iv'])
	# inode
	inode = INODE(pg)
	if 'rootno' in opt:
		rootno = int(opt['rootno'])
	elif file_base['fsp_flags']['SHARED']:
		rootno = int(file_base['sdi']['dd_object']['indexes'][0]['root'])
	else:
		rootno = inode.seg[0][0]['FSEG_FRAG_ARR'][0] if file_base['fsp_flags']['SDI'] == 0 else inode.seg[1][0]['FSEG_FRAG_ARR'][0]
	#if file_base['fsp_flags']['SDI'] == 1: # 8.x
	#	rootno = inode.seg[1][0]['FSEG_FRAG_ARR'][0]
	log.info(file_base['filename'],file_base['sdi']['dd_object']['name'],'ROOT PAGEID:',rootno)
	# FIND LEAF PAGE
	if 'leafno' in opt:
		leafno = int(opt['leafno'])
	else:
		leafno = FIND_LEAF_PAGE_FROM_ROOT(pg,rootno,table)
	log.info(file_base['filename'],'LEAF PAGEID:',leafno)
	leaf_page_data = pg.read(leafno)
	PAGE_INDEX_ID = leaf_page_data[66:74]
	if parser.PARALLEL <= 1: # single
		# f write
		if filename_pre != '':
			filename = os.path.join(filename_pre,f'{table.schema}.{table.name}{file_base["partition_name"] if file_base["partition_name"] is not None else ""}_{os.getpid()}')+'_sql.sql'
			if parser.SQL == 'data':
				print(f"-- LOAD DATA INFILE {repr(filename)} INTO TABLE `{table.schema}`.`{table.name}` FIELDS TERMINATED BY {repr(fields_terminated)} OPTIONALLY ENCLOSED BY \"'\" LINES TERMINATED BY '\\n';")
			f = open(filename,'a')
			print('SQL filename,',filename)
		else:
			f = sys.stdout
			log.info('output is stdout')
			
		# parser the rest data
		pageid = leafno
		idx = INDEX()
		idx.init_index(table=table,idxid=0,pg=pg,page_type='PK_LEAF',replace=parser.REPLACE,complete=parser.COMPLETE_INSERT,multi=parser.MULTI_VALUE,fields_terminated=fields_terminated,decode=not usehex)
		if parser.SQL == 'data':
			idx.get_sql = idx.get_data
		if FORCE:
			pages = os.path.getsize(file_base['filename'])//file_base['pagesize'] - 3
			pg.pageid = 3
			for _ in range(pages):
				log.info('READ PAGE ID:',pg.pageid)
				data = pg.read()
				if data[24:26] != b'E\xbf' or data[64:66] != b'\x00\x00' or PAGE_INDEX_ID != data[66:74]:
					continue
				idx.init_data(data)
				row = []
				if HAVE_DATA:
					row += idx.get_sql(False)
				if HAVE_DELETED:
					row += idx.get_sql(True)
				for sql in row:
					if LIMIT > 0:
						f.write(sql+enclosed_by)
						LIMIT -= 1
					else:
						return None
		else:
			while pageid < 4294967295:
				data = pg.read(pageid)
				log.info('READ PAGE ID:',pageid)
				if data == b'':
					log.error(f'read page({pageid}) faild, will exit')
					break
				pageid = struct.unpack('>L',data[12:16])[0] 
				idx.init_data(data)
				row = []
				if HAVE_DATA:
					row += idx.get_sql(False)
				if HAVE_DELETED:
					row += idx.get_sql(True)
				for sql in row:
					if LIMIT > 0:
						writed_size += f.write(sql+enclosed_by)
						LIMIT -= 1
						if writed_size >= OUTPUT_FILESIZE:
							f = ROTAED_FILE(f,log)
							writed_size = 0
					else:
						return None
		if filename_pre != '':
			f.close()
	else: # multi
		log.info('PARALLEL:',parser.PARALLEL)
		pageid = Value(ctypes.c_uint32, 0)
		pageid.value = 3 if parser.FORCE else leafno
		lock = Lock()
		worker = {}
		for x in range(parser.PARALLEL):
			worker[x] = Process(target=IBD2SQL_WORKER,args=(x,pageid,lock,log,filename_pre,HAVE_DATA,HAVE_DELETED,table,parser,file_base,PAGE_INDEX_ID,enclosed_by,fields_terminated))
		for x in range(parser.PARALLEL):
			worker[x].start()
		for x in range(parser.PARALLEL):
			worker[x].join()
	return		

def IBD2SQL_WORKER(p,pageid,lock,log,filename_pre,HAVE_DATA,HAVE_DELETED,table,parser,file_base,PAGE_INDEX_ID,enclosed_by,fields_terminated):
	infopre = f'PROCESS {p} (pid:{os.getpid()}):'
	writed_size = 0
	log.info(infopre,'START')
	if filename_pre != '':
		filename = os.path.join(filename_pre,f'{table.schema}.{table.name}{file_base["partition_name"] if file_base["partition_name"] is not None else ""}_p{p}_{os.getpid()}')+'_sql.sql'
		f = open(filename,'a')
		print(infopre,'SQL filename,',filename)
	else:
		f = sys.stdout
		log.info(infopre,'output is stdout')
	idx = INDEX()
	pg = PAGE_READER(page_size=file_base['pagesize'],filename=file_base['filename'],encryption=file_base['encryption'],key=file_base['key'],iv=file_base['iv'])
	idx.init_index(table=table,idxid=0,pg=pg,page_type='PK_LEAF',replace=parser.REPLACE,complete=parser.COMPLETE_INSERT,multi=parser.MULTI_VALUE,fields_terminated=fields_terminated)
	if parser.SQL == 'data':
		idx.get_sql = idx.get_data
	pages = os.path.getsize(file_base['filename'])//file_base['pagesize']
	data = b'\x00'*file_base['pagesize'] 
	pgid = 0
	while True:
		with lock:
			pgid = pageid.value
			if pgid > pages or pgid == 4294967295:
				break
			data = pg.read(pgid)
			if parser.FORCE:
				pageid.value = pgid + 1
			else:
				pageid.value = struct.unpack('>L',data[12:16])[0]
			if data[24:26] != b'E\xbf' or data[64:66] != b'\x00\x00' or PAGE_INDEX_ID != data[66:74]:
				continue
		idx.init_data(data)
		row = []
		if HAVE_DATA:
			row += idx.get_sql(False)
		if HAVE_DELETED:
			row += idx.get_sql(True)
		for sql in row:
			writed_size += f.write(sql+enclosed_by)
			if writed_size >= parser.OUTPUT_FILESIZE:
				f = ROTAED_FILE(f,log)
				writed_size = 0
	if filename_pre != '':
		f.close()

	log.info(infopre,'FINISH')


def IBD2SQL_MULTI(table,file_base,opt,filename_pre,log,parser):
	pass
