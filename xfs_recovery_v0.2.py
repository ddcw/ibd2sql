#!/usr/bin/env python3
# write by ddcw @https://github.com/ddcw
# 在xfs文件系统中恢复被drop的表的.
# 用法:
# 如果仅是测试的话, 可能得先刷盘, 不然磁盘可能没得你新建的表(实际环境使用请忽略). partprobe /dev/sdb
# python3 xfs_recovery.py /dev/sdb # 扫描被drop的表
# python3 xfs_recovery.py /dev/sdb inodeno /tmp/newfilename # 恢复被drop的表
# xfs文件系统里面到处都是magic
# 参考: 
#      https://cdn.kernel.org/pub/linux/utils/fs/xfs/docs/xfs_filesystem_structure.pdf
#      https://github.com/torvalds/linux/tree/master/fs/xfs

import struct
import sys,os
import subprocess
import zlib
import json
import datetime

# XFS SB
XFS_SB_MAGIC                    =   0x58465342 # b'XFSB'
XFS_SB_VERSION_1                =   1
XFS_SB_VERSION_2                =   2
XFS_SB_VERSION_3                =   3
XFS_SB_VERSION_4                =   4
XFS_SB_VERSION_5                =   5
XFS_SB_VERSION_NUMBITS          =   0x000f
XFS_SB_VERSION_ALLFBITS         =   0xfff0
XFS_SB_VERSION_ATTRBIT          =   0x0010
XFS_SB_VERSION_NLINKBIT         =   0x0020
XFS_SB_VERSION_QUOTABIT         =   0x0040
XFS_SB_VERSION_ALIGNBIT         =   0x0080
XFS_SB_VERSION_DALIGNBIT        =   0x0100
XFS_SB_VERSION_SHAREDBIT        =   0x0200
XFS_SB_VERSION_LOGV2BIT         =   0x0400
XFS_SB_VERSION_SECTORBIT        =   0x0800
XFS_SB_VERSION_EXTFLGBIT        =   0x1000
XFS_SB_VERSION_DIRV2BIT         =   0x2000
XFS_SB_VERSION_BORGBIT          =   0x4000
XFS_SB_VERSION_MOREBITSBIT      =   0x8000


global MAX_BLOCKS
MAX_BLOCKS = 0

# 解析sdi文件获取文件名(懒得做crc32c了)
def read_name_from_ibd(bdata):
	filename = ''
	if len(bdata) == 16384:
		#print('PAGE_TYPE:',struct.unpack('>H',bdata[24:26]))
		try:
			offset = struct.unpack('>h',bdata[97:99])[0] + 99
			dunzip_len,dzip_len = struct.unpack('>LL',bdata[offset+33-8:offset+33])
			unzbdata = zlib.decompress(bdata[offset+33:offset+33+dzip_len])
			dic_info = json.loads(unzbdata.decode())
			filename = f"{dic_info['dd_object']['schema_ref']}.{dic_info['dd_object']['name']}"
		except Exception as e:
			print(e)
			pass
	return filename

# 获取对象的属性
def get_instance_attr(aa):
	return {attr: getattr(aa, attr) for attr in dir(aa) if not callable(getattr(aa, attr)) and not attr.startswith("__") and attr != 'data'}


# s and ns to date
def xfs_timestamp_t(s,ns):
	return datetime.datetime.fromtimestamp(s).strftime('%Y-%m-%d %H:%M:%S ') + str(ns)

# 方便读指定格式的数据的
class DATA_BUFFER(object):
	def __init__(self,data):
		self.size = len(data)
		self.data = data
		self.offset = 0
		self._offset = 0 # 反向读的, 但本工具只做部分解析,所以不会使用到.

	def read(self,n):
		if self.offset + n > self.size:
			return None
		data = self.data[self.offset:self.offset+n]
		self.offset += n
		return data

	def read_int(self,n:int): # 均为无符号整型
		data = self.read(n)
		if data is None:
			return data
		tdata = [ x for x in data ]
		rdata = 0
		for x in range(n):
			rdata += tdata[x]<<((n-x-1)*8)
		return rdata

class SUPER_BLOCK(object):
	def __init__(self,data):
		self.status = True
		self.data = DATA_BUFFER(data)
		self.magic = self.data.read(4)
		if self.magic != b'XFSB':
			self.status = False
			return
		self.blocksize = self.data.read_int(4) # 每个block的大小, 默认4096
		self.dblocks = self.data.read_int(8)   # 该文件系统总的block数量.(所有AG的加起来).
		global MAX_BLOCKS
		MAX_BLOCKS = self.dblocks
		self.size = self.blocksize * self.dblocks
		self.rblocks = self.data.read_int(8)   # Number blocks in the real-time disk device.
		self.rextents = self.data.read_int(8)  # Number of extents on the real-time device.
		self.uuid = self.data.read(16).hex()   # 唯一标识fs的uuid
		self.logstart = self.data.read_int(8)  # First block number for the journaling log if the log is internal
		self.rootino = self.data.read_int(8)   # root inode number # 根目录的inode号 64
		self.rbmino = self.data.read_int(8)    # bitmap inode for realtime extents
		self.rsumino = self.data.read_int(8)   # summary inode for realtime bitmap
		self.rextsize = self.data.read_int(4)  # realtime extent size, blocks
		self.agblocks = self.data.read_int(4)  # 每个AG的block数量
		self.agcount = self.data.read_int(4)   # 一共有多少个AG
		self.rbmblocks = self.data.read_int(4) # number of rt bitmap blocks
		self.logblocks = self.data.read_int(4) # number of log blocks
		self.versionnum = self.data.read_int(2)# header version == XFS_SB_VERSION
		self.sectsize = self.data.read_int(2)  # 扇区  大小 512 byte
		self.inodesize = self.data.read_int(2) # inode 大小 512 byte
		self.inopblock = self.data.read_int(2) # 每个块的Inode数量. 8 (inodes per block)
		self.fname = self.data.read(12)        # file system name
		self.blocklog = self.data.read_int(1)  # log2 of sb_blocksize (需要使用多少bit来表示block数量)
		self.sectlog = self.data.read_int(1)   # log2 of sb_sectsize (需要使用多少bit来表示扇区的大小)
		self.inodelog = self.data.read_int(1)  # log2 of sb_inodesize (需要使用多少bit来表示inode的大小)
		self.inopblog = self.data.read_int(1)  # log2 of sb_inopblock (需要使用多少bit来表示inopblock)
		self.agblklog = self.data.read_int(1)  # log2 of sb_agblocks (需要使用多少bit来表示agblocks)
		self.rextslog = self.data.read_int(1)  # log2 of sb_rextents
		self.inprogress = self.data.read_int(1)# mkfs is in progress, don't mount
		self.imax_pct = self.data.read_int(1)  # 文件系统的%多少来记录Inode
		self.icount = self.data.read_int(8)    # 已经分配了的inode数量(全部AG加起来的)
		self.ifree = self.data.read_int(8)     # 还剩多少inode
		self.fdblocks = self.data.read_int(8)  # 还剩多少块
		self.frextents = self.data.read_int(8) # free realtime extents
		if XFS_SB_VERSION_QUOTABIT & self.versionnum:
			self.uquotino = self.data.read_int(8) # user quota inode
			self.gquotino = self.data.read_int(8) # group quota inode
			self.qflags = self.data.read_int(2)   # quota flags
		self.flags = self.data.read_int(1)     # Miscellaneous flags.
		self.shared_vn = self.data.read_int(1) # shared version number
		self.inoalignmt = self.data.read_int(4)# inode chunk alignment, fsblocks
		self.unit = self.data.read_int(4)      # stripe or raid unit
		self.width = self.data.read_int(4)     # stripe or raid width
		self.dirblklog = self.data.read_int(1) # log2 of dir block size (fsbs)
		self.logsectlog = self.data.read_int(1)# log2 of the log sector size
		self.logsectsize = self.data.read_int(2)#sector size for the log, bytes
		self.logsunit = self.data.read_int(4)  # stripe unit size for the log
		self.data.offset = 200
		self.features2 = self.data.read_int(4) # additional feature bits
		self.bad_features2 = self.data.read_int(4) 
		self.features_compat = self.data.read_int(4)
		self.features_ro_compat = self.data.read_int(4)
		self.features_incompat = self.data.read_int(4)
		self.features_log_incompat = self.data.read_int(4)
		self.crc = struct.unpack('<L',self.data.read(4))[0] # 小端
		self.spino_align = self.data.read_int(4)
		self.pquotino = self.data.read_int(4)
		self.lsn = self.data.read_int(4)
		self.meta_uuid = self.data.read(16).hex()
		self.agcountlog = self.agcount.bit_length() # 需要使用多少bit来表示ag的数量
		self.maxinode = int(self.dblocks*self.inopblock*self.imax_pct/100) # 最大的inode数量而不是最大的inode号

	def __str__(self):
		return str(get_instance_attr(self))
			
	def de_inode(self,inode):
		"""解析inode号的"""
		ag_log = self.agcountlog
		block_log = self.agblocks.bit_length()
		offset_log = self.inopblog
		count = ag_log + block_log + offset_log
		#print('count:',count,'ag length',ag_log)
		ag = int(bin(inode)[2:].zfill(count)[:ag_log],2)
		block = int(bin(inode)[2:].zfill(count)[ag_log:ag_log+block_log],2)
		offset = int(bin(inode)[2:].zfill(count)[-offset_log:],2)

		#offset_in_block = inode&(2**(self.inopblog-1))
		#block_no =  (inode&(2**(self.agblklog-1)-2**self.inopblog)) >> self.inopblog
		#ag_no = (inode&(2**(self.agcountlog-1)-2**(self.inopblog+self.inopblog))) >> (self.inopblog+self.agblklog)
		# 在那个AG, 在AG的哪个块, 在块的哪个位置(?/8), 实际的偏移量
		#return (ag_no,block_no,offset_in_block,(ag_no*self.agblocks+block_no)*self.blocksize+offset_in_block*self.inodesize)
		return (ag,block,offset,(ag*self.agblocks+block)*self.blocksize+offset*self.inodesize)
		
# XFS_AGI_VERSION 1
class AGI(object):
	def __init__(self,data):
		self.status = True
		self.data = DATA_BUFFER(data)
		self.magic = self.data.read(4)
		if self.magic != b'XAGI':
			self.status = False
			return
		# AG信息
		self.versionnum = self.data.read_int(4)   # 1
		self.seqno = self.data.read_int(4)        # 这是第几个agi, 实际上就是第几个AG
		self.length = self.data.read_int(4)       # block的大小,  sb.agblocks
		# INODE 信息
		self.count = self.data.read_int(4)        # 已分配了的inode号
		self.root = self.data.read_int(4)         # root of inode btree 只需要这玩意, 其它的都不需要了(是AG里的block)
		self.level = self.data.read_int(4)        # levels in inode btree
		self.freecount = self.data.read_int(4)    # number of free inodes
		self.newino = self.data.read_int(4)       # new inode just allocated
		self.dirino = self.data.read_int(4)       # last directory inode chunk
		self.unlinked = self.data.read_int(4)     # Hash table of inodes which have been unlinked (still being referenced)
		self.data.offset = 296
		self.uuid = self.data.read(16).hex()
		self.crc = self.data.read_int(4)          # 没想到吧,这居然是大端字节序了.
		self.pad32 = self.data.read_int(4)
		self.lsn = self.data.read_int(8)
		self.free_root = self.data.read_int(4)
		self.free_level = self.data.read_int(4)
		self.iblocks = self.data.read_int(4)
		self.fblocks = self.data.read_int(4)
		
	def __str__(self,):
		return str(get_instance_attr(self))
		

class INODE(object):
	def __init__(self,data):
		"""
		di_core: 96 B
		di_next_unlinked 4 B
		v5: 76 B
		di_u(data_fork)
			S_IFREG: data_extent 文件
			S_IFDIR: 目录或者大文件之类的.btree+
			S_IFLNK: 链接
			S_IFCHR and S_IFBLK: 其它
		"""
		self.status = True
		self.data = DATA_BUFFER(data)
		self.magic = self.data.read(2)
		if self.magic != b'IN': #inode的标志
			self.status = False
			return
		# INODE CORE 96
		self.di_mode = self.data.read_int(2)      # 文件类型和权限,如果文件被删了,就为空
		# 0400000 目录
		# 0100000 文件
		# 0200000 字符设备
		# 0600000 块设备
		# 0120000 链接
		# 0010000 fifo 
		self.di_mode_oct = oct(self.di_mode)
		self.di_version = self.data.read_int(1)  # 3 for v5
		self.di_format = self.data.read_int(1)   # 存储格式
		# XFS_DINODE_FMT_DEV     0   xfs_dev_t
		# XFS_DINODE_FMT_LOCAL   1   bulk data
		# XFS_DINODE_FMT_EXTENTS 2   struct xfs_bmbt_rec
		# XFS_DINODE_FMT_BTREE   3   struct xfs_bmdr_block
		# XFS_DINODE_FMT_UUID    4   added long ago, but never used
		self.di_onlink = self.data.read_int(2)   # old number of links to file
		self.di_uid = self.data.read_int(4)      # uid
		self.di_gid = self.data.read_int(4)      # gid
		self.di_nlink = self.data.read_int(4)    # number of links to file
		self.di_projid_lo = self.data.read_int(2)# lower  part of owner's project id (v2)
		self.di_projid_hi = self.data.read_int(2)# higher part of owner's project id (v2)
		self.di_v3_pad = self.data.read_int(8)   # v3 without NREXT64
		self.di_atime = xfs_timestamp_t(self.data.read_int(4),self.data.read_int(4))
		self.di_mtime = xfs_timestamp_t(self.data.read_int(4),self.data.read_int(4))
		self.di_ctime = xfs_timestamp_t(self.data.read_int(4),self.data.read_int(4))
		self.di_size = self.data.read_int(8)     # 文件大小, 如果被删了的话, 就为空
		self.di_nblocks = self.data.read_int(8)  # of direct & btree blocks used
		self.di_extsize = self.data.read_int(4)  # basic/minimum extent size for file
		#self.di_nextents = self.data.read_int(4) # if not NREXT64 
		#self.di_anextents = self.data.read_int(2)# if not NREXT64 
		self.__packed = (self.data.read_int(4),self.data.read_int(2))
		self.di_forkoff = self.data.read_int(1)  # attr fork offs, <<3 for 64b align
		self.di_aformat = self.data.read_int(1)  # format of attr fork's data
		self.di_dmevmask = self.data.read_int(4) # DMIG event mask
		self.di_dmstate = self.data.read_int(2)  # DMIG state info
		self.di_flags = self.data.read_int(2)    # Specifies flags associated with the inode
		self.di_gen = self.data.read_int(4)      # generation number
		# di_next_unlinked 4
		self.di_next_unlinked = self.data.read_int(4) # agi unlinked list ptr
		# v5的额外信息 76
		self.di_crc = struct.unpack('<L',self.data.read(4))[0]
		self.di_changecount = self.data.read_int(8)
		self.di_lsn = self.data.read_int(8)
		self.di_flags2 = self.data.read_int(8)
		self.di_cowextsize = self.data.read_int(4)
		self.di_pad2 = self.data.read(12)
		self.di_crtime = xfs_timestamp_t(self.data.read_int(4),self.data.read_int(4))
		self.di_ino = self.data.read_int(8)
		self.di_uuid = self.data.read(16).hex()

		# 解析数据了
		self.extent = []
		self.extent_size = 0
		self.ptrs = [] # 二维数组, 包含了offset的
		if self.di_format == 2: # extent
			for x in range(21):
				ebtr = self.data.read_int(16)
				#extentflag = ebtr>>127
				#startoff = (ebtr>>(127-54))&(2**55-1)
				#startblock = (ebtr>>(127-54-52))&(2**107-1)
				#blockcount = ebtr&(2**21-1)
				ebtr = bin(ebtr)[2:].zfill(128)
				extentflag = int(ebtr[:1],2)
				startoff = int(ebtr[1:55],2)
				startblock = int(ebtr[55:107],2) # (AGNO,BLOCKNO)
				blockcount = int(ebtr[107:128],2)
				ebtr = int(ebtr,2)
				if blockcount > 0:# and (startblock+blockcount) < MAX_BLOCKS: # 有block,且不能超过fs限制
					self.extent_size += blockcount*4096
					self.extent.append([startoff,startblock,blockcount,extentflag,ebtr])
			self.extent.sort()
			# 去掉旧的信息,可能其它文件使用过的
			_textent = []
			_tcount = 0
			for x in self.extent:
				if x[0] == _tcount:
					_textent.append(x)
					_tcount += x[2]
			self.extent_size = 4096*_tcount

		elif self.di_format == 3: # btr
			self.level = self.data.read_int(2)
			self.numrecs = self.data.read_int(2)
			ptrs = []
			keys = []
			for i in range(self.numrecs):
				keys = self.data.read_int(8)
				ptrs = struct.unpack('>Q',self.data.data[340+8*i:340+8*i+8])[0]
				self.ptrs.append([keys,ptrs])
			self.ptrs.sort()
			
		else:
			pass
		
		

	def __str__(self):
		return str(get_instance_attr(self))
		


class XFS(object):
	def __init__(self,filename):
		self.filename = filename

	def init(self):
		self.f = open(self.filename,'rb')
		self.sb = SUPER_BLOCK(self.read())
		return self.sb.status

	def read(self,n=-1):
		if n == -1:
			return self.f.read(4096)
		else:
			self.f.seek(4096*n,0)
			return self.f.read(4096)

	def inode_node(self,agno,blockid):
		"""遍历inode的node节点, 如果是node就递归,是文件就解析"""
		data = self.read(agno*self.sb.agblocks+blockid)
		bb_magic = data[:4]
		bb_level,bb_numrecs,bb_leftsib,bb_rightsib = struct.unpack('>HHLL',data[4:16])
		idx = 16
		if bb_magic == b'IAB3': # V5
			bb_blkno,bb_lsn = struct.unpack('>QQ',data[16:32])
			bb_uuid = data[32:48].hex()
			bb_owner = struct.unpack('>L',data[48:52])
			bb_crc = struct.unpack('<L',data[52:56])
			idx = 56
			#print(bb_uuid)
		else:
			print(bb_magic)
			return

		#print(bb_magic,bb_level,bb_numrecs,bb_leftsib,bb_rightsib)
		if bb_level == 1: # node
			keys = struct.unpack(f'>{bb_numrecs}L',data[idx:idx+bb_numrecs*4])
			# 2076 = (4096-56)/2 + 56 即key和ptr对半分剩下的空间,放一堆的话变一点就全变了..
			ptrs = struct.unpack(f'>{bb_numrecs}L',data[2076:2076+bb_numrecs*4])
			#print(keys,ptrs)
			for bid in ptrs:
				self.inode_node(agno,bid)
		elif bb_level == 0: # leaf
			for i in range(bb_numrecs):
				startino,freecount,free = struct.unpack('>LLQ',data[idx:idx+16])
				# startino 是ag内的inode.是相对的
				idx += 16
				#print(agno,startino,freecount,free)
				for j in range(64):
					if free&(1<<j) == 1: # 0存在, 1不存在
						continue
					blockid = (startino+j)//self.sb.inopblock
					blockoffset = (startino+j)%self.sb.inopblock
					self.inode_leaf(agno,blockid,blockoffset)

	def inode_leaf(self,agno,blockid,blockoffset):
		"""判断叶子节点被删除的文件的, 如果是ibd, 就print"""
		tdata = self.read(agno*self.sb.agblocks+blockid)
		data = tdata[blockoffset*512:blockoffset*512+512]
		inode = INODE(data)
		if inode.di_mode == 0 and inode.extent_size > 0 and inode.di_size ==0: # 被删除的文件
			#print(inode)
			if inode.extent_size % 16384 == 0 and inode.extent_size > 4*16384: # 对16K取整就判断是否为ibd文件
				filename = self.check_ibd(inode) # 如果返回名字就是, 否则就可能是
				if filename is None: # 返回空表示crc32没校验通过
					pass
					#print('被删除文件的INODE:',inode.di_ino)
				elif filename == '':
					print(f'inode:{inode.di_ino} 可能是5.7的ibd文件(或者5.7升级到8.0的)')
				else:
					print(f'inode:{inode.di_ino} filename:{filename}.ibd')
			else:
				pass #占茅坑不拉屎的
				print('inode:',inode.di_ino)

	def read_from_bmbt(self,ptrs,level):
		if level == 2: # multiple level
			pass # 目前没遇到, 虽然和下面一样,只不过多递归一次

		elif level == 1: # single level tree 
			nptrs = []
			for offset,blockno in ptrs:
				data = self.read(blockno)
				mgaic = data[:4]
				bb_level,bb_numrecs = struct.unpack('>HH',data[4:8])
				leftsib,rightsib = struct.unpack('>QQ',data[8:24])
				bno,lsn = struct.unpack('>QQ',data[24:40])
				uuid = data[40:56].hex()
				owner,crc32 = struct.unpack('>QL',data[56:68])
				tdata = DATA_BUFFER(data)
				tdata.offset = 72
				for i in range(bb_numrecs):
					ebtr = tdata.read_int(16)
					ebtr = bin(ebtr)[2:].zfill(128)
					extentflag = int(ebtr[:1],2)
					startoff = int(ebtr[1:55],2)
					startblock = int(ebtr[55:107],2)
					blockcount = int(ebtr[107:128],2)
					ebtr = int(ebtr,2)
					nptrs.append([startoff,startblock,blockcount,extentflag,ebtr])
				#print(len(nptrs))
				#self.read_from_bmbt(nptrs,bb_level)
				#return nptrs
			for p in self.read_from_extent(nptrs):
				yield p

		elif level == 0: # 读数据咯 (还是使用yield)
			#print('读书',ptrs)
			#return self.read_from_extent(ptrs)
			#for x in self.read_from_extent(ptrs):
			#	print(1)
			#	yield x
			pass


	def read_from_extent(self,extent):
		for startoff,startblock,blockcount,extentflag,ebtr in extent:
			for i in range(blockcount):
				#print('READ BLOCK ID',startblock+i)
				agno = startblock>>self.sb.agblklog
				block_id = startblock&(2**self.sb.agblklog-1)
				offset = agno*self.sb.agblocks+block_id+i
				try:
					yield self.read(offset) 
				except Exception as e:
					break


	def check_ibd(self,inode):
		if inode.di_format == 2:
			reader = self.read_from_extent(inode.extent)
		else:
			reader = self.read_from_bmbt(inode.ptrs,inode.level)
		c = 0
		data = b''
		for x in reader:
			data += x
			c += 1
			if c == 16*4:
				break
		#for i in range(4):
		#	print(data[16384*i:16384*i+16384][24:26])
		#print(len(data))
		data = data[3*16384:4*16384] # 第3页, 即SDI PAGE
		if data[:4] != data[-8:-4]:
			return None # 不是ibd文件
		elif data[24:26] == b'E\xbd': # 17853 sdi page
			filename = read_name_from_ibd(data)
		else:
			filename = ''
		return filename

	def leaf_ptr(self):
		"""如果是btr的leaf,就这"""
		pass

	def view_inode_info(self,inodeno):
		agno,blockid,blockoffset,offset = self.sb.de_inode(inodeno)
		self.f.seek(offset)
		inode = INODE(self.f.read(512))
		print(inode)

	def recovery(self,inodeno,filename):
		"""# 根据inode恢复文件"""
		agno,blockid,blockoffset,offset = self.sb.de_inode(inodeno)
		self.f.seek(offset)
		inode = INODE(self.f.read(512))
		#print(inode)
		if inode.di_mode > 0:
			print('这个文件没有被删除啊',inode)
			return 
		if inode.di_format == 3:
			reader = self.read_from_bmbt(inode.ptrs,inode.level)
		elif inode.di_format == 2:
			reader = self.read_from_extent(inode.extent)
		else:
			print('UNKNOWN INODE',inode)
			return 
		with open(filename,'wb') as f:
			for x in reader:
				f.write(x)

	def scan(self,):
		""" 扫描磁盘找被删除的ibd文件, 并打印相关信息"""
		""" 无法直接扫描inode,因为inode号不是连续的,毕竟可以通过inodeno计算inode位置了"""
		""" 人越是工于心计,于是容易失败"""
		for agno in range(self.sb.agcount):
			data = self.read(self.sb.agblocks*agno)
			agi = AGI(data[1024:1024+512])
			#print('ROOT:',agi.root,'LEVEL:',agi.level)
			self.inode_node(agno,agi.root)
	
def test():
	with open('/dev/sdb','rb') as f:
		data = f.read(4096)
		sb = SUPER_BLOCK(data[:512])
		print('ROOT INODE NO:',sb.rootino) # 文件系统的/的inode号. 
		#print(sb)
		#f.seek(8*4096)
		#aa = f.read(512)
		#print(INODE(aa))
		cc = sb.de_inode(71)
		print(cc)
		f.seek(cc[-1])
		aa = f.read(512)
		bb = INODE(aa)
		print(bb)
		cc = bb.read_from_bmbt(inode.ptrs,inode.level)
		#print(bb.extent,bb)
		#print(AGI(data[1024:1024+512]))
		#for agno in range(sb.agcount):
		#	print('遍历 AG ',agno)


argv = sys.argv
if len(argv) == 1 or len(argv) > 4: #or len(argv) == 3:
	print('USAGE: python3 ',argv[0],' devicename [inode] [filename]')
	sys.exit(1)
else:
	devicename = argv[1]
	if not os.path.exists(devicename):
		print(devicename,' 不存在!')
		sys.exit(1)

if len(argv) >= 3 and len(argv) <= 4 or len(argv) == 2:
	if len(argv) > 2:
		inodeno = int(argv[2])
	if len(argv) > 3:
		filename = argv[3]
	if len(argv) == 4 and os.path.exists(filename):
		print(filename,' 文件存在, 请换个名字')
		sys.exit(2)
	ddcw = XFS(devicename)
	if ddcw.init():
		if ddcw.sb.versionnum & XFS_SB_VERSION_5 == 0:
			print('只支持xfs v5')
			sys.exit(3)
		if len(argv) == 2:
			ddcw.scan()
		elif len(argv) == 3: # indoe查看
			ddcw.view_inode_info(inodeno)
		else: # 文件恢复
			ddcw.recovery(inodeno,filename)
