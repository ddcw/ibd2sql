#!/usr/bin/env python3
# write by ddcw @https://github.com/ddcw
# web界面展示ibd的存储结构   v2.0 pre

BIND_HOST = '0.0.0.0'
BIND_PORT = 8080

"""
| IDX 0 |     | PAR | DETAIL | 
| IDX 0 |     | PRE | NEXT |
| IDX 1 |     
| IDX 2 | | REC | REC | REC | REC | REC | .... |
| IDX 3 |
| IDX 3 |

如果rec是node的话, 点击就进入下一层, 如果是rec的话, 点击就显示数据和基础信息

CHANGE LOG:
2024.11.04 准备ing
"""

import os,sys,signal
import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import json
from ibd2sql.ibd2sql import ibd2sql
from ibd2sql.innodb_page_index import *
from ibd2sql.innodb_page import *

argv = sys.argv

def print_usage():
	print(f'\nUSAGE: python3 {argv[0]} FILENAME\n')
	sys.exit(1)

if len(argv) != 2:
	print_usage()

filename = argv[1]
if not os.path.exists(filename):
	print(f'{filename} 不存在')
	print_usage()

def DEBUG(*args,**kwargs):
	pass

def signal_15_handler(sig,frame):
	print('AT^ AWSL ')
	sys.exit(0)


signal.signal(signal.SIGTERM, signal_15_handler) # kill -15
signal.signal(signal.SIGINT, signal_15_handler)  # ctrl+c


# ibd文件初始化
ddcw = ibd2sql()
ddcw.FILENAME = filename
ddcw.init()
INDEX = []
for x in ddcw.table.index:
	#print(x,ddcw.table.index[x]['element_col'], ddcw.table.column[1])
	INDEX.append([x,ddcw.table.index[x]['idx_type'],','.join([ ddcw.table.column[j[0]]['name'] for j in ddcw.table.index[x]['element_col']]), ddcw.table.index[x]['options']['root'] ]) # idxno, idx_type, idx_col, root-pageno
#print(INDEX)

DDL = ddcw.get_ddl()
if 1 not in ddcw.table.index: # 没得主键的话,就使用DB_ROW_ID
	ddcw.table.index[1] = {'name': None, 'comment': 'DB_ROW_ID', 'idx_type': 'PRIMARY ', 'element_col': [(0, 0, 2)], 'options': {'id': 'x', 'root': '4', 'space_id': 'x', 'table_id': 'x', 'trx_id': 'x'}, 'is_visible': True, 'is_row_id':True}
	ddcw.table.column[0] = {'name': 'DB_ROW_ID', 'is_autoincrement': False, 'type': 'int', 'isvar': False, 'size': 4, 'isbig': False, 'elements_dict': {}, 'varsize': 0, 'have_default': True, 'default': '0', 'comment': '', 'collation': 'latin1_swedish_ci', 'character_set': 'latin1', 'index_type': 'NONE', 'is_nullable': False, 'is_zerofill': False, 'is_unsigned': False, 'is_auto_increment': False, 'is_virtual': False, 'hidden': 1, 'char_length': 11, 'extra': None, 'instant': False, 'instant_value': '', 'instant_null': True, 'generation_expression': '', 'default_option': '', 'collation_id': 8, 'srs_id': 0, 'version_dropped': 0, 'version_added': 0, 'physical_pos': 1, 'ct': 'int','is_row_id':True}


class PAGE(page):
	def __init__(self,*args,**kwargs):
		super().__init__(*args,**kwargs)
		self.table = kwargs['table']
		self.idxno = kwargs['idxno']
		self.idx = self.table.index[self.idxno]
		self.f = kwargs['f']

	def read_rec_header(self):
		return record_header(self.readreverse(5))

	def read_rec_nullable(self,rheader):
		ROW_VERSION = -1
		if self.idxno == 1 and rheader.row_version_flag:
			ROW_VERSION = self._read_innodb_varsize()
		self.ROW_VERSION = ROW_VERSION
		if self.table.mysqld_version_id < 80029 and self.table.mysqld_version_id >=80012 and rheader.instant_flag and self.idxno == 1:
			self._COLUMN_COUNT = self._read_innodb_varsize()
		null_bitmask_count = 0
		if self.idxno == 1: # PK, leaf
			_t_COLUMN_COUNT = 2
			for _phno,colno in self.table.column_ph:
				_t_COLUMN_COUNT += 1
				col = self.table.column[colno]
				if rheader.row_version_flag:
					if (ROW_VERSION >= col['version_added'] and (col['version_dropped'] == 0 or col['version_dropped'] > ROW_VERSION)) or (col['version_dropped'] > ROW_VERSION and ROW_VERSION >= col['version_added']):
						null_bitmask_count += 1 if col['is_nullable'] else 0
				else:
					if rheader.instant_flag and _t_COLUMN_COUNT > self._COLUMN_COUNT:
						break
					null_bitmask_count += 1 if col['is_nullable'] else 0
			if not rheader.instant_flag:
				null_bitmask_count = self.table.null_bitmask_count
		else: # secondary key
			for colno,prefix_key,order in self.idx['element_col']:
				col = self.table.column[colno]
				if col['is_nullable']:
					null_bitmask_count += 1
		null_bitmask_len = int((null_bitmask_count+7)/8)
		null_bitmask = self._readreverse_uint(null_bitmask_len)
		self.null_bitmask = null_bitmask
		self.null_bitmask_offset = 0 # 当前使用的nullable
		#print(null_bitmask_count,null_bitmask,self.offset,self._offset)
		return null_bitmask

	def _read_nullable(self,colno):
		if not self.table.column[colno]['is_nullable']:
			return False
		isnull = True if self.null_bitmask&(1<<self.null_bitmask_offset) else False
		self.null_bitmask_offset += 1
		return isnull

	def _read_rec_varsize(self): # 我是谁, 我在这干嘛...
		pass

	def read_rec_key(self,rec_header):
		rdata = {}
		for colno,prefix_key,order in self.table.index[self.idxno]['element_col']:
			col = self.table.column[colno]
			isprefix = False if prefix_key == 0 else True
			if self.idxno != 1: # 二级索引要判断是否为空
				key = None if self._read_nullable(colno) else self.read_rec_col(colno)
			else: # 主键就不管那么多了
				key = self.read_rec_col(colno)
			rdata[colno] = {'key':key,'isprefix':isprefix}
		return rdata

	def read_rec_col(self,colno): # 只管读, 是否instant是read_rec_field来看的
		col = self.table.column[colno]
		if 'is_row_id' in col:
			return self._read_uint(6)
		n = col['size']
		is_unsigned = col['is_unsigned']
		if col['isvar']:
			size = self._read_innodb_varsize(col['char_length'])
			if size + self.offset > 16384:
				SPACE_ID,PAGENO,BLOB_HEADER,REAL_SIZE = struct.unpack('>3LQ',self.read(20))
				_tdata = first_blob(self.f,PAGENO)
			else:
				_tdata = self.read(size)
			if col['ct'] == "json":
				data = jsonob(_tdata[1:],int.from_bytes(_tdata[:1],'little')).init()
				data = json.dumps(data)
			elif col['ct'] == "geom":
				data = int.from_bytes(_tdata,'big',signed=False)
			elif col['ct'] == "vector":
				data = '0x'+_tdata.hex()
			else:
				data = char_decode(_tdata,col)
		elif col['ct'] in ['int','tinyint','smallint','bigint','mediumint']: 
			data = self.read_innodb_int(n,is_unsigned)
		elif col['ct'] == 'float':
			data = self.read_innodb_float(n)
		elif col['ct'] == 'double':
			data = self.read_innodb_double(n)
		elif col['ct'] == 'decimal':
			data = self.read_innodb_decimal(n,extra)
		elif col['ct'] == 'set':
			data = self._read_uint(n)
			_sn = 0
			_sdata = ''
			for x in col['elements_dict']:
				if 1<<_sn & data:
					_sdata += col['elements_dict'][x] + ","
				_sn += 1
			data = _sdata[:-1]
			data = repr(data)
		elif col['ct'] in ['enum','set']: 
			data = self._read_uint(n)
			data = repr(col['elements_dict'][data])
		elif col['ct'] == 'time':
			data = self.read_innodb_time(n)
		elif col['ct'] == 'datetime':
			data = self.read_innodb_datetime(n)
		elif col['ct'] == 'date':
			data = self.read_innodb_date(n)
		elif col['ct'] == 'timestamp':
			data = self.read_innodb_timestamp(n)
		elif col['ct'] == 'year':
			data = self._read_uint(n) + 1900
		elif col['ct'] == 'bit':
			data = self._read_uint(n)
		elif col['ct'] == 'binary':
			data = self._read_uint(n)
		elif col['ct'] == 'tinytext':
			s = int.from_bytes(self.readreverse(1),'big')
			data = self.read(s).decode()
		else:
			data = self.read(n)
		return data

	def read_rec_trx_rollptr(self):
		return {'trx':self._read_uint(6),'rollptr':self._read_uint(7)}

	def read_rec_pageid(self):
		return self._read_uint(4)

	def read_rec_field(self,rheader,pkdata):
		# 解析字段的时候,分为普通字段和instant字段
		rdata = {}
		ROW_VERSION = self.ROW_VERSION
		_t_COLUMN_COUNT = 2
		for _phno,colno in self.table.column_ph:
			if self.idxno <= 1:
				_t_COLUMN_COUNT += 1
			col = self.table.column[colno]
			if colno in pkdata and not pkdata[colno]['isprefix']: # 主键读过了, 就pas
				continue
			if col['is_virtual']:
				continue
			if rheader.instant_flag and _t_COLUMN_COUNT > self._COLUMN_COUNT :#and colno in rdata:
				rdata[colno] = None
				continue
			if rheader.row_version_flag:
				if (ROW_VERSION >= col['version_added'] and (col['version_dropped'] == 0 or col['version_dropped'] > ROW_VERSION)) or (col['version_dropped'] > ROW_VERSION and ROW_VERSION >= col['version_added']):
					if self._read_nullable(colno):
						rdata[colno] = None
					else:
						rdata[colno] = self.read_rec_col(colno)
				elif ROW_VERSION < col['version_added']:
					rdata[colno] = col['default'] if not col['instant_null'] else None
				else:
					rdata[colno] = None
			elif ( not rheader.instant_flag and col['instant']):
				rdata[colno] = col['default'] if not col['instant_null'] else None
			elif not rheader.instant and col['version_dropped'] > 0:
				rdata[colno] = None
			else:
				if self._read_nullable(colno):
					rdata[colno] = None
				else:
					rdata[colno] = self.read_rec_col(colno)
			
		return rdata
				

	def read_rec_pk(self,):
		rdata = {}
		for colno,prefix_key,order in self.table.index[1]['element_col']:
			col = self.table.column[colno]
			rdata[colno] = {'key':self.read_rec_col(colno),'isprefix':False if prefix_key == 0 else True}
		return rdata

	def read_row(self,):
		self._offset = self.offset


# 一共4种INDEX PAGE (1.cluster:non-leaf, 2.cluster:leaf  3.secondary:non-leaf, 4.secondary:leaf)
# pagetype是指是leaf还是non-leaf,是cluster还是secondary
def idx_page(idxno,pageno):
	if idxno not in ddcw.table.index:
		return
	idx = ddcw.table.index[idxno]
	if pageno == 0:
		pageno = idx['options']['root']
	ddcw.PAGE_ID = int(pageno)
	data = ddcw.read()
	#aa = index(data,table=ddcw.table, idx=ddcw.table.cluster_index_id, debug=DEBUG,f=ddcw.f)
	#sqls = []
	#sql = ddcw.SQL_PREFIX
	#for x in aa.read_row():
	#	sqls.append(f"{sql}{ddcw._tosql(x['row'])};")
	#return str(sqls)
	rdata = []
	pg = PAGE(data,f=ddcw.f,idxno=idxno,table=ddcw.table)
	pg.offset = 99
	while True:
		dd = {}
		offset = pg.offset
		pg.read_row()
		dd['offset'] = offset # 当前的偏移量
		rec_header = pg.read_rec_header()
		if rec_header.record_type == 3: # MAX
			break
		elif rec_header.record_type == 2: # min
			pg.offset = offset + rec_header.next_record
			continue
		dd['rec_header'] = {
			'instant_flag':rec_header.instant_flag,
			'row_version_flag':rec_header.row_version_flag,
			'deleted':rec_header.deleted,
			'min_rec':rec_header.min_rec,
			'owned':rec_header.owned,
			'heap_no':rec_header.heap_no,
			'record_type':rec_header.record_type,
			'next_record':rec_header.next_record,
		}
		#if not (idxno == 1 and rec_header.record_type == 1):
		nullable = pg.read_rec_nullable(rec_header)
		dd['nullable'] = nullable
		#int((ddcw.table.null_bitmask_count+7)/8)
		dd['key'] = pg.read_rec_key(rec_header)
		if idxno == 1 and rec_header.record_type == 0: # PK leaf
			dd['trx_rollptr'] = pg.read_rec_trx_rollptr()
			dd['field'] = pg.read_rec_field(rec_header,dd['key'])
		elif idxno == 1 and rec_header.record_type == 1: # PK none-leaf
			dd['pageid'] = pg.read_rec_pageid()
		elif idxno > 1 and rec_header.record_type == 0: # secondary key, leaf
			dd['pk'] = pg.read_rec_pk()
		elif idxno > 1 and rec_header.record_type == 1: # secondary key, none-leaf
			dd['pk'] = pg.read_rec_pk()
			dd['pageid'] = pg.read_rec_pageid()
		rdata.append(dd)

		pg.offset = offset + rec_header.next_record
	page_header = dict([ (x,getattr(pg.page_header,x)) for x in  pg.page_header.__dict__ if x.startswith('PAGE_') and x != 'PAGE_BTR_SEG_LEAF' and x != 'PAGE_BTR_SEG_TOP' ])
	page_header['PAGE_BTR_SEG_LEAF'] = {
		'SAPCE_ID':pg.page_header.PAGE_BTR_SEG_LEAF.SAPCE_ID,
		'PAGE_ID':pg.page_header.PAGE_BTR_SEG_LEAF.PAGE_ID,
		'PAGE_OFFSET':pg.page_header.PAGE_BTR_SEG_LEAF.PAGE_OFFSET,
		}
	page_header['PAGE_BTR_SEG_TOP'] = {
		'SAPCE_ID':pg.page_header.PAGE_BTR_SEG_TOP.SAPCE_ID,
		'PAGE_ID':pg.page_header.PAGE_BTR_SEG_TOP.PAGE_ID,
		'PAGE_OFFSET':pg.page_header.PAGE_BTR_SEG_TOP.PAGE_OFFSET,
		}
	return {
		'fil_header':dict([ (x,getattr(pg,x)) for x in  pg.__dict__ if x.startswith('FIL_PAGE') ]),
		'page_header':page_header,
		'data':rdata,
		'fil_trailer':{'CHECKSUM':pg.CHECKSUM,'FIL_PAGE_LSN':pg.FIL_PAGE_LSN},
		'pageno':pageno,
		'column':ddcw.table.column,
		}









class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
	def do_GET(self):
		url_components = urllib.parse.urlparse(self.path)
		query = urllib.parse.parse_qs(url_components.query)
		path = url_components.path
		self.handle_html_request()

	def do_POST(self):
		content_length = int(self.headers['Content-Length'])
		post_data = self.rfile.read(content_length)
		data = json.loads(post_data)
		if self.path == '/opt':
			pageno = data['pageno']
			indxno = data['idxno']
			if indxno == 0:
				rdata = DDL
			else:
				rdata = idx_page(indxno,pageno)
		self.send_response(200)
		self.send_header('Content-type', 'text/html')
		self.end_headers()
		rbdata = json.dumps({'data':rdata,'status':True}).encode('utf-8')
		self.wfile.write(rbdata)

	def handle_html_request(self):
		self.send_response(200)
		self.send_header('Content-type', 'text/html')
		self.end_headers()
		html_content = '''

<html>
<head>
	<title>DDCW's ibd2sql web console</title>
	<meta charset="UTF-8">
	<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
	body {
		font-family: Arial, sans-serif;
		background-color:#d0d0d0;
	}
	.container{
		height:100%;
	}
	.nav{
		height: 100%;
		width: 180px;
		position: fixed;
		z-index: 1;
		top: 0;
		left: 0;
		// background-color: #111; 
		overflow-x: hidden;
		padding-top: 20%;
	}
	.content{
		margin-left: 180px;
	}

	button:hover{
		//color:#FFDE59;
		color:yellow;
	}
	button{
		background-color:#8CFF5B; height:50px;font-size:22px;marign:5px;
		//color: white;
		border:2px solid #007bff
	}
	#overlay {
		position: fixed;
		top: 0;
		left: 0;
		width: 100%;
		height: 100%;
		background-color: rgba(0, 0, 0, 0.5); /* 半透明背景 */
		display: none; /* 默认隐藏 */
		align-items: center;
		justify-content: center;
		z-index: 1000;
	}
	/* 模态框内容 */
	#popup{
		background-color: #fff;
		padding: 20px;
		border-radius: 4px;
		position: relative;
		min-width: 300px;
		text-align: center;
	}
	/* 关闭按钮 */
	#closebutton{
		position: absolute;
		top: 10px;
		right: 10px;
		background-color: transparent;
		border: none;
		font-size: 18px;
		cursor: pointer;
	}
	/* 模态框显示时 */
	#overlay.show {
		display: flex;
	}
        /* 箭头样式 */
        .arrow {
            width: 30px;
            height: 30px;
            margin-left: -5px; /* 调整箭头位置，使其与按钮靠近 */
            margin-right: -5px;
        }
        /* 调整箭头的颜色 */
        .arrow use {
            fill: #333;
        }

	/*叶子节点*/
	.record_type0{
		background-color:#cfefc1;
	}
	.record_type0:hover{color:red;}
	/*非叶子节点*/
	.record_type1{
		background-color:#90EE90;
	}
	.record_type1:hover{font-size:22px;}
	.bg_red{background-color:red}
</style>
<script>
	console.log('https://github.com/ddcw/ibd2sql')
	CURRENT_INDEX = 1;
	CURRENT_PAGE  = 1;
	function query_page(pageno){
		CURRENT_PAGE = pageno;
		data = {'pageno':pageno,'idxno':CURRENT_INDEX};
		var xhr = new XMLHttpRequest();
		xhr.open('POST', '/opt', true);
		xhr.setRequestHeader("Content-Type", "application/json");
		xhr.onreadystatechange = function () {
			if (xhr.readyState === 4 && xhr.status === 200) {
				var rdata = JSON.parse(xhr.responseText);
				if (rdata.status){
					//alert(JSON.stringify(rdata.data,null,2))
					if (typeof rdata.data === 'string'){
						v = "<textarea style='marign-top: 20%; ' rows='40' cols='120'>" + rdata.data + "</textarea>"
						document.getElementById('content').innerHTML = v
					}else{
						//alert(JSON.stringify(rdata.data,null,2))
						v = "<textarea style='marign-top: 20%; ' rows='40' cols='120'>" + JSON.stringify(rdata.data,null,2) + "</textarea>"
						//document.getElementById('content').innerHTML = v
						init_page(rdata.data)
					}
				}
			}
		}
		xhr.send(JSON.stringify(data));
	}

	function init_page(data){
		//初始化界面, 导航栏/idx 选中的idx要有颜色, 右边对应的page要展示出来
		pre_button = "<button "
		if (data.fil_header.FIL_PAGE_PREV < 4294967295){
			pre_button = "<button " + "title='点击前往上一页' onclick='query_page("+data.fil_header.FIL_PAGE_PREV+")'"
		}
		pre_button += ">前1页("+data.fil_header.FIL_PAGE_PREV+")</button>"
		next_button = "<button "
		if (data.fil_header.FIL_PAGE_NEXT < 4294967295){
			next_button = "<button " + "title='点击前往下一页' onclick='query_page("+data.fil_header.FIL_PAGE_NEXT+")'"
		}
		next_button += ">后1页("+data.fil_header.FIL_PAGE_NEXT+")</button>"
		//current_button_title = JSON.stringify(data.fil_header,null,2) + JSON.stringify(data.page_header,null,2) + JSON.stringify(data.fil_trailer,null,2)
		msg = {
			'fil_header':data.fil_header,
			'page_header':data.page_header,
			'fil_trailer':data.fil_trailer,
			'pageno':data.fil_trailer,
		}
		current_button = "<button onclick='showmsg("+JSON.stringify(msg)+")' title='"+"点击显示详情"+"'>"+"当前页:"+data.pageno+" 字段数量:" + data.data.length+"</button>"
		document.getElementById('content').innerHTML = "<div>" + pre_button + current_button + next_button + "</br></br></div><div id='haha'></div>"// + "<textarea rows=50 cols=100>" + JSON.stringify(data.data,null,2) + "</textarea>"
		container = document.getElementById('haha');
		data.data.forEach(function(item, index){
			var button = document.createElement('button');
			button.classList.add("record_type" + item['rec_header']['record_type'])
			if ('rec_header' in item){if ('deleted' in item['rec_header']){
			if (item['rec_header']['deleted']){
				button.classList.add(".bg_red")
			}}}
			v = ""
			for (const k in item.key){
				v += data.column[k]['name'] + ":" + item.key[k]['key'] + ","
			}
			if ('pageid' in item){
				button.addEventListener('click',function(){
					query_page(item['pageid'])
				});
				if ('pk' in item){
				for (const k in item.pk){
					v += data.column[k]['name'] + ":" + item.pk[k]['key'] + ","
				}}
			}else{
				button.addEventListener('click',function(){
					showmsg(JSON.stringify(item,null,2))
				});
				//全部字段显示出来不好看...
				//for (const k in item.field){
				//	v += data.column[k]['name'] + ":" + item.field[k] + ","
				//}

				// 叶子节点 普通索引还是显示主键吧.
				if ('pk' in item){
				for (const k in item.pk){
					v += data.column[k]['name'] + ":" + item.pk[k]['key'] + ","
				}}
			
			}
			button.innerHTML = v
			bttitile = 'OFFSET:'+item.offset
			if ('pageid' in item){bttitile+='  PAGEID:'+item['pageid']}
			button.title = bttitile
			container.appendChild(button);
			if (index < data.data.length -1) {
				var svgNS = "http://www.w3.org/2000/svg";
				var svg = document.createElementNS(svgNS, "svg");
				svg.setAttribute("class", "arrow");
				var use = document.createElementNS(svgNS, "use");
				use.setAttributeNS('http://www.w3.org/1999/xlink', 'href', '#arrowSymbol');
				svg.appendChild(use);
				container.appendChild(svg);
			}
		});
	}

	function showmsg(msg){
		if (typeof msg === 'string'){
			data = msg
		}else{data = JSON.stringify(msg,null,2)}
		document.getElementById('msg').innerHTML= data; //设置相关数据信息
		document.getElementById('overlay').classList.add('show'); //设置显示
		//document.getElementById('overlay').display = 'flex';
	}
	function closemsg(){
		document.getElementById('overlay').classList.remove('show');
	}

	function set_index(n){
		//alert(n)
		CURRENT_INDEX = n;
		query_page(0);
	}

	function init(){
		set_index(1)
	}
</script>
</head>
<body>
<div class='container'>
	<div class='nav' id='nav'>
		<button style='width:180px; background-color:#5E5BFF; height:50px;font-size:20px;marign:5px;' onclick='set_index(0)'>获取DDL</button></br>
		''' + "\n".join([ f"<button style='width:180px; background-color:#5DE2E7; height:50px;font-size:20px;marign:5px;' onclick='set_index({x[0]})'>{'INDEX' if x[1] == '' else 'PRIMARY' } ({x[2]})</button>"  for x in INDEX ]) + '''
	</div>
	<div class='content' id='content'>
		右边的page信息
	</div>
</div>
<svg style="display: none;">
    <symbol id="arrowSymbol" viewBox="0 0 30 30">
        <!-- 绘制箭头 -->
        <line x1="0" y1="15" x2="20" y2="15" stroke="#333" stroke-width="2"></line>
        <polygon points="20,10 30,15 20,20" fill="#333"></polygon>
    </symbol>
</svg>
<!-- 模态框展示信息 -->
<div id="overlay">
	<div id="popup">
		<button id="closebutton" onclick='closemsg()'>&times;</button>
		<textarea rows=40 cols=100 id="msg">这是一个自定义的提示框！</textarea>
	</div>
</div>
<script>
// 点击背景时,可以关闭
document.getElementById('overlay').addEventListener('click', function(event) {
	if (event.target === overlay) {
		closemsg()
	}
});
</script>
</body>
<script>
window.onload = function() {
    init()
};
</script>
</html>
'''
		self.wfile.write(html_content.encode('utf-8'))

def run(server_class=HTTPServer, handler_class=SimpleHTTPRequestHandler):
	server_address = (BIND_HOST,BIND_PORT)
	httpd = server_class(server_address, handler_class)
	msg = f'''
###############################
#     ibd2sql web console     #
###############################

http://{BIND_HOST}:{BIND_PORT}

'''
	print(msg)
	httpd.serve_forever()

if __name__ == '__main__':
	run() # 润

