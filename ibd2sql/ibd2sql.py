#!/usr/bin/env python3

import datetime
from ibd2sql.innodb_page_sdi import *
from ibd2sql.innodb_page_spaceORxdes import *
from ibd2sql.innodb_page_inode import *
from ibd2sql.innodb_page_index import *
import sys


class ibd2sql(object):
	def __init__(self,*args,**kwargs):
		self.LIMIT = -1
		self.STATUS = False
		self.PAGESIZE = 16384
		#先初始化一堆信息.
		self.DEBUG = False
		self.DEBUG_FD = sys.stdout
		self.FILENAME = ''
		self.DELETE = False
		self.FORCE = False
		self.SET = False
		self.MULTIVALUE = False
		self.COMPLETE_SQL = False
		self.REPLACE = False
		self.WHERE1 = ''
		self.WHERE2 = (0,2**48)
		self.WHERE3 = (0,2**56)
		self.PAGE_ID = 0
		self.AUTO_DEBUG = True #自动DEBUG, 如果page解析有问题的话, 然后退出
		self.SQL_PREFIX = ''
		self.SQL = True
		self.IS_PARTITION = False #是否为分区表

		self.PAGE_MIN = 0
		self.PAGE_MAX = 2**32
		self.PAGE_START = -1
		self.PAGE_COUNT = -1
		self.PAGE_SKIP = -1


	def _init_table_name(self):
		try:
			self.debug(f"OLD TABLENAME:{self.tablename}")
		except:
			pass
		self.tablename = f"`{self.table.schema}`.`{self.table.table_name}`"
		self.debug(f"NEW TABLENAME:{self.tablename}")
		self._init_sql_prefix()

	def replace_schema(self,name):
		self.table.schema = name
		return self._init_table_name()

	def replace_name(self,name):
		self.table.table_name = name
		return self._init_table_name()

	def read(self):
		"""
		RETURN PAGE RAW DATA
		"""
		self.debug(f"ibd2sql.read PAGE: {self.PAGE_ID} ")
		self.f.seek(self.PAGESIZE*self.PAGE_ID,0)
		#self.PAGE_ID += 1
		return self.f.read(self.PAGESIZE)

	def _init_sql_prefix(self):
		#self.table.remove_virtual_column() #把虚拟字段干掉
		#self.SQL_PREFIX = f"{ 'REPLACE' if self.REPLACE else 'INSERT'} INTO {self.tablename}{'(`'+'`,`'.join([ self.table.column[x]['name'] for x in self.table.column ]) + '`)' if self.COMPLETE_SQL else ''} VALUES "
		SQL_PREFIX = f"{'REPLACE' if self.REPLACE else 'INSERT'} INTO {self.tablename}("
		for x in self.table.column:
			if self.table.column[x]['is_virtual'] or not self.COMPLETE_SQL:
				continue
			else:
				SQL_PREFIX += f"`{self.table.column[x]['name']}`,"
		SQL_PREFIX = SQL_PREFIX[:-1] + ") VALUES " if self.COMPLETE_SQL else SQL_PREFIX[:-1] + " VALUES "
		self.SQL_PREFIX = SQL_PREFIX

	def init(self):
		self.debug("DEBUG MODE ON")
		self.debug("INIT ibd2sql")
		self.debug("FORCE",self.FORCE)
		self.debug("SET",self.SET)
		self.debug("MULTIVALUE",self.MULTIVALUE)
		self.debug("AUTO_DEBUG",self.AUTO_DEBUG)
		self.debug(f"FILTER: \n\t{self.WHERE1}    \n\t{self.WHERE2[0]} < TRX < {self.WHERE2[1]}    \n\t{self.WHERE3[0]} < ROLLPTR < {self.WHERE3[1]}")
		self.STATUS = True
		self.debug(f"OPEN IBD FILE:",self.FILENAME)
		self.f = open(self.FILENAME,'rb')
		self.PAGE_ID = 0

		#first page
		self.PAGE_ID = 0
		self.debug("ANALYZE FIRST PAGE: FIL_PAGE_TYPE_FSP_HDR")
		self.space_page = xdes(self.read()) #第一页
		if not self.space_page.fsp_status:
			sys.stderr.write(f"\nrow_format = compressed or its damaged or its mysql 5.7 file\n\n")
			sys.exit(2)
		self.debug("ANALYZE FIRST PAGE FINISH")
		sdino = self.space_page.SDI_PAGE_NO
		self.debug("SDI PAGE NO:",sdino)

		#sdi page
		if self.IS_PARTITION:
			self.debug("THIS TABLE IS PARTITION TABLE")
			self.tablename = "PARTITION TABLE NO NAME"
			pass
		else:
			self.debug('ANALYZE SDI PAGE')
			self.PAGE_ID = sdino
			self.sdi = sdi(self.read(),debug=self.debug) #sdi页
			if not self.sdi:
				self.debug("ANALYZE SDI PAGE FAILED (maybe page is not 17853), will exit 2")
				sys.exit(2)
			self.debug('ANALYZE SDI PAGE FINISH')
			self.debug('SET ibd2sql.table = sdi.table (SDI的使命已结束 >_<)')
			self.table = self.sdi.table
			self.tablename = self.table.name
			self.debug("META INFO")
			for colno in self.table.column:
				self.debug(f"COLNO: {colno}  \n{self.table.column[colno]}")
			for idxno in self.table.index:
				self.debug(f"IDXNO: {colno}  \n{self.table.index[idxno]}")
			self.debug("INIT SQL PREFIX")
			self.debug("DDL:\n",self.table.get_ddl())
			self._init_sql_prefix() #初始化表前缀, 要获取到SDI信息才能做

		#inode page
		self.debug(f'ANALYZE PAGE INODE (PAGE_ID=2) (for get index)')
		self.PAGE_ID = 2 #inode
		self.inode = inode(self.read())
		self.debug("FIRST INDEX (Non-leaf and leaf page) :",self.inode.index_page[0]," (-1 is None)")
		self.first_no_leaf_page = self.inode.index_page[0][0]
		self.first_leaf_page = self.inode.index_page[0][1] 
		#self.debug("START FIND FIRST LEAF PAGE")
		if self.first_leaf_page < 3 or self.first_leaf_page >= 4294967295 or True:
			self.init_first_leaf_page()
		self.debug("FIRST LEAF PAGE ID:",self.first_leaf_page )
		self.debug("#############################################################################")
		self.debug("                  INIT ibd2sql FINISH                                        ")
		self.debug("#############################################################################\n\n")
		return True

	def init_first_leaf_page(self):
		_n = 0
		self.debug(f"INIT FIRST PAGE TO FIRST_NO_LEAF_PAGE ({self.first_no_leaf_page})")
		self.PAGE_ID = self.first_no_leaf_page
		while self.PAGE_ID < 4294967295 and self.PAGE_ID > 2:
			_n += 1
			self.debug(f'COUNT: {_n} FIND LEAF PAGE, CURRENT PAGE ID:',self.PAGE_ID)
			aa = find_leafpage(self.read(),table=self.table, idx=self.table.cluster_index_id, debug=self.debug)
			aa.pageno = self.PAGE_ID
			IS_LEAF_PAGE,PAGE_ID = aa.find()
			if IS_LEAF_PAGE:
				self.debug("FIND FINISH, PAGE_ID:",self.PAGE_ID,'\n')
				self.first_leaf_page = self.PAGE_ID
				break
			else:
				self.first_leaf_page = self.PAGE_ID = PAGE_ID
			

	def debug(self,*args):
		if self.DEBUG:
			msg = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [DEBUG] {' '.join([ str(x) for x in args ])}\n"
			self.DEBUG_FD.write(msg)

	def _get_index_page(self):
		pn = 0
		while self.PAGE_ID > 0 and self.PAGE_ID < 4294967295:
			pn += 1
			self.debug(f"CURRENT PAGE ID {self.PAGE_ID}     PAGE NO:{pn}")
			aa = page(self.read())
			self.PAGE_ID = aa.FIL_PAGE_NEXT

	def get_sql(self,):
		self.PAGE_ID = self.PAGE_START if self.PAGE_START  > 2 else self.first_leaf_page
		self.MULTIVALUE = False if self.REPLACE else self.MULTIVALUE #冲突
		if self.FORCE:
			self.debug("============================= WARNING ================================")
			self.debug("========================== FORCE IS TRUE =============================")
			self.debug("============================= WARNING ================================")
		self.debug("ibd2sql get_sql BEGIN:",self.PAGE_ID,self.PAGE_MIN,self.PAGE_MAX,self.PAGE_COUNT)
		while self.PAGE_ID > self.PAGE_MIN and self.PAGE_ID <= self.PAGE_MAX and self.PAGE_ID < 4294967295 and self.PAGE_COUNT != 0:
			self.debug("INIT INDEX OBJECT")
			aa = index(self.read(),table=self.table, idx=self.table.cluster_index_id, debug=self.debug)
			aa.DELETED = True if self.DELETE else False
			aa.pageno = self.PAGE_ID
			self.debug("SET FILTER",self.WHERE2,self.WHERE3)
			aa.mintrx = self.WHERE2[0]
			aa.maxtrx = self.WHERE2[1]
			aa.minrollptr = self.WHERE3[0]
			aa.maxrollptr = self.WHERE3[1]
			self.PAGE_ID = aa.FIL_PAGE_NEXT

			if self.PAGE_SKIP > 0:
				self.PAGE_SKIP -= 1
				self.debug("SKIP THIS PAGE")
				continue
			self.PAGE_COUNT -= 1

			sql = self.SQL_PREFIX
			if self.MULTIVALUE:
				try:
					_tdata = aa.read_row()
				except Exception as e:
					if self.FORCE:
						continue
					else:
						self.debug(e)
						break
				for x in _tdata:
					if self.LIMIT == 0:
						return None
					self.LIMIT -= 1
					sql += self._tosql(x['row']) + ','
				sql = (sql[:-1] + ';')
				print(sql)
				
			else:
				try:
					_tdata = aa.read_row()
				except Exception as e:
					if self.FORCE:
						continue
					else:
						self.debug(e)
						break
				for x in _tdata:
					if self.LIMIT == 0:
						return None
					self.LIMIT -= 1
					_sql = f"{sql}{self._tosql(x['row'])};"
					print(_sql)
			if self.PAGE_COUNT == 0:
				break
			

	def test(self):
		"""
		TEST ONLY
		"""
		#self.DEBUG = False
		self.debug('AUTO TEST\n\n\n##########################################################\n\t\tBEGIN TEST -_- \n##########################################################\n\n')
		#self.PAGE_ID = 4
		self.debug('CLUSTER INDEX ID:',self.table.cluster_index_id)
		self.debug('FIRST LEAF PAGE:',self.first_leaf_page)
		self.PAGE_ID = self.first_leaf_page

		self.debug('ANALYZE INDEX PAGE BEGIN: (FIRST LEAF PAGE):',self.PAGE_ID)
		#DATA
		_n = 0

		#self.replace_schema('db2')
		#aa = index(self.read(),table=self.table, idx=self.table.cluster_index_id, debug=self.debug)
		pc = -1 #页数限制, 方便DEBUG
		sp = 2329 #跳过的page数量  也是方便DEBUG的
		sp = 0
		#self.PAGE_ID = 2361
		self.MULTIVALUE = False if self.REPLACE else self.MULTIVALUE
		while self.PAGE_ID > 0 and self.PAGE_ID < 4294967295 and pc != 0:
			aa = index(self.read(),table=self.table, idx=self.table.cluster_index_id, debug=self.debug)
			sp -= 1
			if sp >= 0:
				self.PAGE_ID = aa.FIL_PAGE_NEXT
				continue
			#aa = index(self.read(),table=self.table, idx=self.table.cluster_index_id, )
			aa.pageno = self.PAGE_ID
			aa.mintrx = self.WHERE2[0]
			aa.maxtrx = self.WHERE2[1]
			sql = self.SQL_PREFIX
			if self.MULTIVALUE:
				for x in aa.read_row():
					sql += self._tosql(x['row']) + ','
					_n += 1
				print(sql[:-1],';')
			else:
				for x in aa.read_row():
					print(f"{sql}{self._tosql(x['row'])};")
					_n += 1
			self.PAGE_ID = aa.FIL_PAGE_NEXT
			pc -= 1
			#break
		self.debug('TOTAL ROWS:',_n)

	def get_ddl(self):
		return self.table.get_ddl()

	def _tosql(self,row):
		"""
		把 row 转为SQL, 不含INSERT INTO ;等  主要是数据类型引号处理
		"""
		sql = '('
		for colno in self.table.column:
			data = row[colno]
			if data is None:
				sql  = f"{sql}NULL, "
			elif self.table.column[colno]['ct'] in ['tinyint','smallint','int','float','double','bigint','mediumint','year','decimal',] :
				sql  = f"{sql}{data}, "
			elif (not self.SET) and (self.table.column[colno]['ct'] in ['enum','set']):
				sql  = f"{sql}{data}, "
			elif self.table.column[colno]['ct'] == 'binary':
				sql = f"{sql}{hex(data)}, " #转为16进制, 好看点,但没必要, 就int吧
			else:
				sql += repr(data) + ", "
	
		return sql[:-2] + ")"

	def _get_first_page(self,):
		pass

	def close(self):
		try:
			self.f.close()
		except:
			pass
		try:
			if self.DEBUG:
				self.DEBUG_FD.close()
		except:
			pass
		return True
