import argparse
import sys,os
import innodb_fil
import innodb_sdi
import innodb_inode
import innodb_type
import innodb_index
import struct


def _argparse():
	parser = argparse.ArgumentParser(add_help=True, description='解析mysql8.0的ibd文件')
	parser.add_argument('--version', '-v', '-V', action='store_true', dest="VERSION", default=False,  help='show version')
	parser.add_argument('--sumary', '-s', action='store_true', dest="SUMMARY", default=True,  help='print summary info(ddl and index info)')
	parser.add_argument('--ddl', '-d', action='store_true', dest="DDL", default=False,  help='print ddl')
	parser.add_argument('--sql', action='store_true', dest="SQL", default=False,  help='print data with sql (without ddl)')
	parser.add_argument('--data', action='store_true', dest="DATA", default=False,  help='print data like [[],[]]')
	parser.add_argument('--delete', action='store_true', dest="DELETED", default=False,  help='print data with flag:deleted')
	parser.add_argument('--row', action='store_true', dest="ROW", default=False,  help='print rows in filename without deleted')
	#parser.add_argument('--parallel','-p', action='store', dest="PARALLEL", default=4,  help='parse to data/sql with N threads.(default 4) TODO')

	parser.add_argument(dest='FILENAME', help='ibd filename')

	if parser.parse_args().VERSION:
		print("VERSION: v0.1 for mysql8.0")
		sys.exit(0)

	return parser.parse_args()

if __name__ == '__main__':
	parser = _argparse()
	filename = parser.FILENAME
	if not os.path.exists(filename):
		#print(f'no file {filename}')
		raise f'no file {filename}'

	if parser.SUMMARY and not (parser.DDL or parser.SQL or parser.DATA or parser.DELETED):
		data = innodb_fil.page_summary(filename)
		print(f"PAGE SUMMARY: { 'USED PERCENT:'+str(round(100-(data['FIL_PAGE_TYPE_ALLOCATED'])*100/sum([data[x] for x in data]),2))+'%' if 'FIL_PAGE_TYPE_ALLOCATED' in data else '' }")
		for x in data:
			print(f"{x}\t{data[x]}")
		print('')

		idata = b''
		sdata = b''
		with open(filename, 'rb') as f:
			f.seek(2*16384,0)
			idata = f.read(16384)
			sdata = f.read(16384)

		#DDL(sdi)
		ddl = innodb_sdi.sdi(sdata)
		print(ddl.get_ddl(),'\n')

		#打印行数量
		if parser.ROW:
			rows = 0
			dic = innodb_sdi.sdi(filename).get_dic()
			columns = dic['dd_object']['columns']
			_columns = []
			for col in columns:
				if col['name'] in ['DB_TRX_ID','DB_ROLL_PTR','DB_ROW_ID']:
					continue
				_columns.append(col)
			columns = []
			lcolumns = len(columns)
			for x in range(len(_columns)):
				isvar,size,dtype = innodb_type.innodb_isvar_size(_columns[x])
				columns.append({'name':_columns[x]['name'], 'isvar':isvar, 'size':size, 'dtype':dtype})

			pk = []
			for x in dic['dd_object']['indexes'][0]['elements']:
				if x['length'] < 4294967295:
					pk.append(x['column_opx'])
			pageno = innodb_index.first_leaf(filename,columns,pk)
			with open(filename, 'rb') as f:
				while True:
					f.seek(pageno*16384,0)
					bdata = f.read(16384)
					if bdata == b'':
						break
					pageno = struct.unpack('>L',bdata[12:16])[0]
					if struct.unpack('>H',bdata[24:26])[0] == 17855:
						rows += struct.unpack('>H',bdata[38+16:38+18])[0]
			print('ROWS:',rows)
		sys.exit(0)

	if parser.DDL:
		print('\n',innodb_sdi.sdi(filename).get_ddl(),'\n')

	if parser.SQL or parser.DATA or parser.DELETED:
		dic = innodb_sdi.sdi(filename).get_dic()
		columns = dic['dd_object']['columns']
		_columns = []
		for col in columns:
			if col['name'] in ['DB_TRX_ID','DB_ROLL_PTR','DB_ROW_ID']:
				continue
			_columns.append(col)
		columns = []
		lcolumns = len(columns)
		for x in range(len(_columns)):
			isvar,size,dtype = innodb_type.innodb_isvar_size(_columns[x])
			columns.append({'name':_columns[x]['name'], 'isvar':isvar, 'size':size, 'dtype':dtype})

		pk = []
		for x in dic['dd_object']['indexes'][0]['elements']:
			if x['length'] < 4294967295:
				pk.append(x['column_opx'])

			
		#读取INDEX页
		with open(filename,'rb') as f:

			#先找到主键索引叶子节点第一个PAGE(不一定在碎片页中, 毕竟第一页可能多次更新就没用了...)
			#非叶子节点还是固定的, 就在第4页(从0开始算). 也可以从sdi信息读主键索引的root
			pageno = innodb_index.first_leaf(filename,columns,pk)
					
			while True:
				if pageno > 4294967295:
					break
				f.seek(pageno*16384,0)
				bdata = f.read(16384)
				if len(bdata) <16384:
					break
				page = innodb_fil.page(bdata)
				pageno = page.FIL_PAGE_NEXT
				if page.FIL_PAGE_TYPE != 17855:
					continue
				if parser.DELETED:
					for x in innodb_index.index_deleted(bdata,pk,columns):
						if parser.DATA:
							print(x)
						else:
							print(f'insert into {dic["dd_object"]["schema_ref"]}.{dic["dd_object"]["name"]} values("'+'","'.join([ str(i) for i in x ])+'");') 
				else:
					for x in innodb_index.index(bdata,pk,columns):
						if parser.DATA:
							print(x)
						else:
							print(f'insert into {dic["dd_object"]["schema_ref"]}.{dic["dd_object"]["name"]} values("'+'","'.join([ str(i) for i in x ])+'");') 
				#break
