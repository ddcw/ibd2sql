# CHANGE LOG


## 2026.11.04
1. 修复一些frm的bug:
	1. nodefault+nullable不跳过null位
	2. 分区表+长comment
	3. ddl中5.6.4及其以下版本中datetime/time/timestamp默认值
2. 新增一些frm的支持:
	1. 5.5环境的分区表(legacy_db_type=20)
	3. ddl支持compression属性(对解析ibd没有帮助,只对ddl完整性有帮助,但我们8.x的都展示了compression属性,那这也顺便解析下吧,即使要改一大堆代码-_-)

## 2026.11.03
1. frm支持生成列
	1. 位置: orig_gcol_screen_pos = disk_buff+read_length-gcol_screen_length
	2. 每个生成列的结构:
		byte 1   : 固定为1
		byte 2,3 : 生成列表达式的长度
		byte 4   : 0:virtual  1:stored
		byte 5.. : 实际的表达式
	3. 带有生成列之后,frm存储方式就有区别了
		1. virtual的默认值放在最后的
		2. 对应的default_value_null_bitmask也得重构下
2. 生成列展示规则
	1. insert不包含生成列(建议和--complete一起使用,不然会出现列数量不匹配)
	2. virtual的生成列不存储
	3. 生成列也有null属性

## 2026.11.02
1. 修复了DDL的一些BUG
	1. ON DELETE 和 ON UPDATE是可以都设置的
	2. 8.0.16 check支持的ENFORCED属性
	3. 表和索引支持KEY_BLOCK_SIZE属性
	4. DDL展示字符集规则如下:
		1. 和表字符集不一样
		2. 指定数据类型(16, 22, 23, 24, 25, 26, 27, 28, 29)且字符集不为binary(除非是enum/set)
2. 修复了DML的BUG:当mysql版本大于等于9.1时,instant ddl连续次数超过64 (正经人谁跑这么多???)

## 2026.10.30
```txt
1. 修复了一些frm的bug
	1. set/enum 默认值错位/复用(set/enum是会公用默认值存储的)
	2. date/datetime/timestamp/year 默认值
	3. decimal小数0的默认值
	4. varbinary默认值为''
	5. 整数的符号判断取反了
	6. time默认值
	7. bit默认值
	8. FULLTEXT和SPATIAL flag取反了
	9. default CURRENT_TIMESTAMP(n)精度丢失
	10. 5.x中timestamp显示要求null属性
	11. 索引注释错位
	12. spatial索引丢失

2. 修复了json类型的一些bug
	1. json支持decimal对象
	2. json可能为空

3. 修复了一些set/enum的bug
	1. set 元素太多,边界问题,死循环

4. 修复了一些其它bug
	1. year类型为0的时候,不应该返回1900
	2. --set schema匹配的时候应该是schema_ref而不是tablespace_ref
	3. decimal(m,0)时,不显示'.'
	4. time可能差1秒
	5. 区分了default null和default ''
	6. 支持RANGE COLUMNS 和 LIST COLUMNS
	7. 二进制类型默认值
	8. geometry不需要手动补srsid
	9. varbinary含null默认值
```

## 2.4(2026.09.21)
1. 完善文档
2. 修复BUG: 索引注释关键字COMMENT
3. 修复BUG: enum/set默认值
4. 修复BUG: 解析5.x的frm文件时,需要考虑默认使用第一个非空唯一索引作为主键
5. 修复BUG: --set port=INT
6. 修复BUG: json中某字符串是可能大于16K的



## 2.3(2026.05.26)
2.3
1. 修复BUG: var & not null & row_format=compressed
2. 支持zblob
3. 移除了MERGE_THRESHOLD(为了兼容5.6 ibdata1)
4. 修复BUG: 当innodb_page_size=65K时,rec_next溢出问题
5. 支持win环境恢复drop的表 (--scan \\.\E:)
6. 支持从系统表提取非deleted的表信息(--set deleted=except)
7. 修复BUG: decimal整数部分为空
8. 修复BUG: frm中:默认值在enum/set之后;binary类型为29;binary为空时返回''而不是0x




## 2.2(2026.01.8)
2.2
1. 修复已知BUG
2. 支持ibdata1文件解析
3. 支持drop/truncate表的恢复

## 2.1 (2025.10.24)
2.1 
1. 修复了一些BUG
2. 支持对碎片页的解析.
3. 增加<尽可能的提取坏块中的数据>


## 2.0 (2025.08.30)

2.x系列的第一个版本, 重构了大部分代码, 性能提升也是很明显的, 最重要的是加了并发功能, 上限无限高.  而且还支持解析多个文件和mysql.ibd这样一个文件多个表的情况. 

try it !



## 历史版本信息

| VERSION | UPDATE     | NOTE                                                         |
| ------- | ---------- | ------------------------------------------------------------ |
| v0.1    | 2023.4.27  | first version                                                |
| v0.2    | 2023.08.30 | support more data types                                      |
| v0.3    | 2023.10.13 | support parse file from 5.x upgrade to 8.x                   |
| v1.0    | 2024.01.05 | add debug and support more data types                        |
| v1.1    | 2024.04.12 | fix some bugs                                                |
| v1.2    | 2024.04.25 | add support of geometry data types                           |
| v1.3    | 2024.05.11 | add support 5.x                                              |
| v1.4    | 2024.05.21 | add support extra page and subpartition                      |
| v1.5    | 2024.07.10 | add support vector data types and fix INSTANT bug            |
| v1.6    | 2024.09.19 | fix some bugs                                                |
| v1.7    | 2024.10.29 | fix some bugs&support compress page&support recovery **drop table** & support ucs2,utf16,utf32 charset |
| v1.8    | 2024.11.09 | support keyring plugin encryption & all character set        |
| v1.9    | 2025.02.21 | fix some bugs & support direct parsing of 5.x files          |
| v1.10   | 2025.04.16 | fix some bugs & add super_fast_count.py                      |
| v1.11   | 2025.06.13 | fix some bugs & make `--force` to view page one by one for skip BAD BLOCK |
| v1.12   | 2025.08.30 | fix some bugs and improve performance by over 20%            |
| v2.0    | 2025.08.30 | improved performance and support concurrency            |
| v2.1    | 2025.10.24 | fix some bugs & add `--set bad-pages=fast/try/skip`            |
| v2.2    | 2026.01.08 | fix some bugs & support parser ibdata1  & add scan disk to recover dropped/truncated table          |
| v2.3    | 2026.05.26 | fix some bugs & support recover dropped/truncated table for win         |
| v2.4    | 2026.09.21 | fix some bugs & improve doc         |
