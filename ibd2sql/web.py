from http.server import HTTPServer, BaseHTTPRequestHandler
from ibd2sql.ibd2sql import FIND_LEAF_PAGE_FROM_ROOT
from ibd2sql.innodb_page.page import PAGE_READER
from ibd2sql.innodb_page.inode import INODE
from ibd2sql.innodb_page.index import INDEX
from ibd2sql.innodb_page.table import TABLE
import urllib.parse
import datetime
import signal
import struct
import json
import sys
import os


"""
------------------     -------------------------------------------------
| <select table> |     |                    [UP_PAGE]                  |
|                |     |     [PRE PAGE]  [CURREN PAGE]   [NEXT PAGE]   |
| [DDL]          |     -------------------------------------------------
| [idx 01]       |     
| [idx 02]       |     -------------------------------------------------
| [idx 03]       |    | <row 0>   <row 1> ....                         |
| [idx 04]       |    | <row n>                                        |
| ....           |    | .....                                          |
------------------    --------------------------------------------------
"""

def signal_15_handler(sig,frame):
        print('AT^ AWSL ')
        sys.exit(0)
	        
signal.signal(signal.SIGTERM, signal_15_handler) # kill -15
signal.signal(signal.SIGINT, signal_15_handler)  # ctrl+c

class MY_HANDLER(BaseHTTPRequestHandler):
	"""
	idx:[
		[
			[non-leaf, leaf], # idx1
			[non-leaf, leaf], # idx2
			
		], # filename 1
		[], # filename 2
	]
	"""
	IDX = None

	def do_GET(self):
		url_components = urllib.parse.urlparse(self.path)
		query = urllib.parse.parse_qs(url_components.query)
		path = url_components.path
		self.handle_html_request()

	def do_POST(self):
		content_length = int(self.headers['Content-Length'])
		post_data = self.rfile.read(content_length)
		data = json.loads(post_data)
		rdata  = ''
		status = True
		level = -2
		next_pageid = 4294967295
		pre_pageid = 4294967295
		pageno = 4294967295
		key = [] # idx key
		if self.path == '/opt':
			fileno = int(data['fileno'])
			idxno  = data['idxno']
			pageno = data['pageno']
			level  = data['level']
			if level == -3: # root no
				level = self.IDX[fileno]['idx'][idxno]['level']
			if level == 0: # leaf
				if self.IDX[fileno]['idx'][idxno]['leaf'].read_page(pageno):
					key = self.IDX[fileno]['idx'][idxno]['key']
					rdata = self.IDX[fileno]['idx'][idxno]['leaf'].get_all_rows()
					next_pageid = self.IDX[fileno]['idx'][idxno]['leaf'].read_page_id_next()
					pre_pageid = self.IDX[fileno]['idx'][idxno]['leaf'].read_page_id_pre()
				else:
					status = False
			elif level == -1: # ddl
				rdata = self.IDX[fileno]['ddl']
			elif level > 0: # non leaf
				if self.IDX[fileno]['idx'][idxno]['root'].read_page(pageno):
					key = self.IDX[fileno]['idx'][idxno]['key']
					rdata = self.IDX[fileno]['idx'][idxno]['root'].get_all_rows()
					next_pageid = self.IDX[fileno]['idx'][idxno]['root'].read_page_id_next()
					pre_pageid = self.IDX[fileno]['idx'][idxno]['root'].read_page_id_pre()
				else:
					status = False
			else: # unknown error
				rdata = f'unknown error, request:{data}'
		elif self.path == '/file_base': # return idx base
			fileno = int(data['fileno'])
			rdata = [ {'name':x['name'],'pageno':x['rootno'],'level':x['level'],'key':x['key']} for x in self.IDX[fileno]['idx']]
		self.send_response(200)
		self.send_header('Content-type', 'text/html')
		self.end_headers()
		rbdata = json.dumps({'data':rdata,'status':status,'level':level,'pre':pre_pageid,'next':next_pageid,'pageno':pageno,'ddl':self.IDX[fileno]['ddl'],'current':pageno,'key':key}).encode('utf-8')
		self.wfile.write(rbdata)
				

	def handle_html_request(self):
		self.send_response(200)
		self.send_header('Content-type', 'text/html')
		self.end_headers()
		html_content = """

<html><head><meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
	<title>DDCW's ibd2sql 2.x web console</title>
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
		// padding-top: 20%;
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
	console.log('ibd2sql 2.x')
	console.log('https://github.com/ddcw/ibd2sql')
	CURRENT_FILE = 0;
	CURRENT_INDEX = 0;
	CURRENT_PAGE  = 0;
	CURRENT_PAGE_PRE = 0;
	CURRENT_PAGE_NEXT = 0;
	CURRENT_PAGE_TOP = 0;
	CURRENT_LEVEL = 0;
	CURRENT_DDL = '';
	CURRENT_PAGE_DETAIL = '';
	UP_PAGE = [4294967295,];
	function query_data(opt){
		//alert(CURRENT_PAGE)
		data = {'fileno':CURRENT_FILE,'pageno':CURRENT_PAGE,'idxno':CURRENT_INDEX,'level':CURRENT_LEVEL};
		var xhr = new XMLHttpRequest();
		xhr.open('POST', opt, true);
		xhr.setRequestHeader("Content-Type", "application/json");
		xhr.onreadystatechange = function () {
			if (xhr.readyState === 4 && xhr.status === 200) {
				var rdata = JSON.parse(xhr.responseText);
				if (rdata.status){
					//alert(JSON.stringify(rdata.data,null,2))
					if (typeof rdata.data === 'string'){
						v = "<textarea style='marign-top: 20%; ' rows='40' cols='120'>" + rdata.data + "</textarea>"
						//document.getElementById('content').innerHTML = v
						showmsg(rdata.data)
					}else{
						CURRENT_DDL = rdata.ddl
						CURRENT_LEVEL = rdata.level
						CURRENT_PAGE = rdata.current
						CURRENT_PAGE_PRE = rdata.pre
						CURRENT_PAGE_NEXT = rdata.next
						CURRENT_PAGE_DETAIL = rdata
						if (opt == '/file_base'){
							init_select(rdata)
							//init_page(rdata)
							document.getElementById('idxno').children[0].click()
						}
						else if(opt == '/opt'){
							init_page(rdata)
						}
						else(showmsg(rdata))
					}
				}
			}
		}
		xhr.send(JSON.stringify(data));
	}

	function showddl(){
		showmsg(CURRENT_DDL)
	}

	function init_select(data){
		idx_button = ''
		data.data.forEach(function(item, index){
			idx_button = idx_button + "<button style='width:180px; background-color:#5DE2E7; height:50px;font-size:20px;marign:5px;' onclick='init_index("+index+","+item.pageno+","+item.level+")' title='"+item.key+"'>"+item.name+"("+item.key+")</button>";
		});
		CURRENT_PAGE = data.data[0].pageno
		CURRENT_LEVEL = data.data[0].level
		document.getElementById('idxno').innerHTML= idx_button;
	}

	function init_page(data){

		//showmsg(data);
		// init banner
		//alert(CURRENT_PAGE)
		page_current = CURRENT_PAGE;
		page_top = UP_PAGE.at(-1);
		page_pre = data.pre;
		page_next = data.next;
		//showmsg([page_current,page_top,page_pre,page_next]);
		document.getElementById('query_page_top').innerHTML = '<button title="parent page('+page_top+')" onclick="query_page_top()">UP-PAGE('+page_top+')</button>'
		document.getElementById('select_page').innerHTML = '<button title="pre page" onclick="query_page_bro('+page_pre+')">PRE-PAGE('+page_pre+')</button>' + 
		'<button title="level:'+ data.level + '" onclick="show_current_page()">CURRENT-PAGE(' + page_current + ') ROWS('+data.data.length+')</button>' + 
		'<button title="next page" onclick="query_page_bro('+page_next+')">NEXT-PAGE('+page_next+')</button>'
		
		// init page
		container = document.getElementById('page_detail');
		container.innerHTML = '';
		data.data.forEach(function(item, index){
			var button = document.createElement('button');
			button.classList.add("record_type" + data.level);
			if (item.deleted) {
				button.classList.add(".bg_red");
			}
			v = ""
			for (const k in item.data){
				if (data.key.includes(k)){
					v += k+":"+item.data[k].data + "\t"
				}
			}
			if (CURRENT_LEVEL > 0){ // non leaf page
				button.addEventListener('click',function(){
					query_page_child(item['pageid'])
				})
				button.title = "pageid:"+item.pageid
			}else{
				button.addEventListener('click',function(){
					showmsg(item)
				})
				button.title = "pageid:"+page_current
			}
			
			button.innerHTML = v
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
			//showmsg(data)
			
		})

	}

	function show_current_page(){
		showmsg(CURRENT_PAGE_DETAIL)
	}

	function showmsg(msg){
		if (typeof msg === 'string'){
			data = msg
		}else{data = JSON.stringify(msg,null,2)}
		document.getElementById('msg').innerHTML= data; //设置相关数据信息
		document.getElementById('overlay').classList.add('show'); //设置显示
	}

	function closemsg(){document.getElementById('overlay').classList.remove('show');}

	function init_index(idxno,pageno,level){
		//showmsg([idxno,pageno,level,])
		CURRENT_INDEX = idxno;
		CURRENT_LEVEL = level;
		CURRENT_PAGE = pageno;
		for (item of document.getElementById('idxno').children){
			item.style.border='2px solid #007bff';
		}
		query_page_bro(pageno);
		document.getElementById('idxno').children[idxno].style.border='2px solid red';
		//showmsg(idxno,pageno,level);
	}

	function query_page_bro(pageno){
		if (pageno < 4294967295){
			CURRENT_PAGE = pageno;
			query_data('/opt');
		}
	}

	function query_page_child(pageno){
		UP_PAGE.push(CURRENT_PAGE);
		//CURRENT_PAGE = pageno;
		CURRENT_LEVEL = CURRENT_LEVEL - 1
		query_page_bro(pageno);
	}

	function query_page_top(){
		if (UP_PAGE.at(-1) == 4294967295){
			showmsg('current page('+CURRENT_PAGE+') is root')
			return ''
		}
		CURRENT_LEVEL = CURRENT_LEVEL + 1;
		query_page_bro(UP_PAGE.pop());
	}

	function init_file(fileno){
		CURRENT_FILE = fileno;
		query_data('/file_base');
	}
</script>
</head>
<body>

<div class="container">
	<div class="nav" id="nav">
		<div id='fileno'>
			<select id="fileno", onchange="init_file(this.options[this.options.selectedIndex].value)">
""" + "\n".join([ f"<option value='{x}'>{self.IDX[x]['schema']}.{self.IDX[x]['name']}</option>" for x in range(len(self.IDX)) ]) + """
			</select>
			</br></br></br></br>
		</div>
		<div id='ddl'><button style="width:180px; background-color:#5E5BFF; height:50px;font-size:20px;marign:5px;" onclick="showddl()">GET DDL</button></div>
		<div id="idxno">
			<button style="width:180px; background-color:#5DE2E7; height:50px;font-size:20px;marign:5px;" onclick="query_page_bro(1)">PRIMARY (id)</button>
		</div>
	</div>


	<div class="content" id="content">
		<div align="center" id="query_page_top"><button title="up" onclick="query_page_top()">UP(pageid)</button></div>
		<div align="center" id="select_page">
			<button title="pre page" onclick="query_page_bro(1152)">PRE-PAGE(1152)</button>
			<button>CURRENT-PAGE(123) ROWS(3213)</button>
			<button title="next page" onclick="query_page_bro(495)">NEXT-PAGE(495)</button>
			<br><br>
		</div>
		<div id="page_detail">
			<button class="record_type0" title="OFFSET:8302">k:50161,id:12311,</button>
			<svg class="arrow"><use href="#arrowSymbol"></use></svg>
			<button class="record_type0" title="OFFSET:6404">k:50169,id:97092,</button>
			<svg class="arrow"><use href="#arrowSymbol"></use></svg>
			<button class="record_type0" title="OFFSET:7860">k:50169,id:98244,</button>
		</div>
	</div>
</div>

<svg style="display: none;">
    <symbol id="arrowSymbol" viewBox="0 0 30 30">
        <!-- draw arrow -->
        <line x1="0" y1="15" x2="20" y2="15" stroke="#333" stroke-width="2"></line>
        <polygon points="20,10 30,15 20,20" fill="#333"></polygon>
    </symbol>
</svg>
<!-- display overlay -->
<div id="overlay" class="">
	<div id="popup">
		<button id="closebutton" onclick="closemsg()">×</button>
		<textarea rows="40" cols="100" id="msg">{
			text
		}
		</textarea>
	</div>
</div>
<script>
// close overlay when onclick
document.getElementById('overlay').addEventListener('click', function(event) {
	if (event.target === overlay) {
		closemsg()
	}
});
</script>

<script>window.onload = function() {init_file(0)}</script>
</body></html>
"""
		self.wfile.write(html_content.encode('utf-8'))


class IBD2SQL_WEB(INDEX):
	def read_page_id_next(self,):
		return struct.unpack('>L',self.data[12:16])[0]
	def read_page_id_pre(self,):
		return struct.unpack('>L',self.data[8:12])[0]
	def read_page(self,pageid):
		data = self.pg.read(pageid)
		if data != b'':
			self.init_data(data)
			return True
		else:
			return False
	def read_page_next(self,):
		return self.read_page(self.read_page_id_next())
	def read_page_pre(self):
		return self.read_page(self.read_page_id_pre())
	

def RUN_IBD2SQL_WEB(file_list,opt,log,server_class=HTTPServer, handler_class=MY_HANDLER):
	BIND_HOST = '0.0.0.0' if 'host' not in opt else opt['host']
	BIND_PORT = 8080      if 'port' not in opt else opt['port']
	log.info(f'listen {BIND_HOST}:{BIND_PORT}')
	IDX = []
	for file_base in file_list:
		table = TABLE(file_base['sdi'])
		pg = PAGE_READER(page_size=file_base['pagesize'],filename=file_base['filename'],encryption=file_base['encryption'],key=file_base['key'],iv=file_base['iv'])
		log.info('init',file_base['filename'])
		inode = INODE(pg)
		inode = inode.seg[1:] if file_base['fsp_flags']['SDI'] == 1 else inode.seg[0:]
		idx = []
		for x in table.index:
			idxname = table.index[x]['name']
			log.info('init',file_base['filename'],'idxname:',idxname)
			is_primary = True if idxname == 'PRIMARY' else False
			rootno = inode[x][0]['FSEG_FRAG_ARR'][0] if table.mysql_version_id <= 50744 else int(table.index[x]['root'])
			try:
				leafno = FIND_LEAF_PAGE_FROM_ROOT(pg,rootno,table,'PK_NON_LEAF' if is_primary else 'KEY_NON_LEAF',x)
			except Exception as e:
				log.info(e,'skit it')
				continue
			rootdata = pg.read(rootno)
			leafdata = pg.read(leafno)
			idx_root = IBD2SQL_WEB()
			idx_root.init_index(table=table,idxid=x,pg=pg,page_type='PK_NON_LEAF' if is_primary else 'KEY_NON_LEAF' )
			idx_root.init_data(rootdata)
			idx_leaf = IBD2SQL_WEB()
			idx_leaf.init_index(table=table,idxid=x,pg=pg,page_type='PK_LEAF' if is_primary else 'KEY_LEAF' )
			idx_leaf.init_data(leafdata)
			#if rootno == leafno:
			#	idx_root = idx_leaf
			#key = [ table.column[y['column_opx']]['name'] for y in table.index[x]['elements'] ]
			key = []
			for y in table.index[x]['elements']:
				kname = table.column[y['column_opx']]['name']
				if kname in ['DB_TRX_ID','DB_ROLL_PTR']:
					break
				key.append(kname)
			idx.append({
				'rootno':rootno,
				'leafno':leafno,
				'root':idx_root,
				'leaf':idx_leaf,
				'primary':is_primary,
				'name':idxname,
				'idxno':x,
				'level':struct.unpack('>H',rootdata[64:66])[0],
				'key':key
			})
		filename = file_base['filename']
		IDX.append({
			'filename':file_base['filename'],
			'idx':idx,
			'schema':table.schema,
			'name':table.name,
			'ddl':table.get_ddl(False,False,False)
		})

#	for i in range(10):
#		if IDX[0]['idx'][0]['leaf'].read_page_next():
#			print(IDX[0]['idx'][0]['leaf'].get_all_rows())
#		else:
#			break

	handler_class.IDX = IDX 

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

