

# 版本更新

| 版本   | 变更时间       | 说明                     | 备注                                       |
| ---- | ---------- | ---------------------- | ---------------------------------------- |
| v0.1 | 2023.4.27  | 第一个版本....              |                                          |
| v0.2 | 2023.08.30 | 支持更多数据类型               | 1. 修复year/tinyint的支持2. 符号支持(对于数字类型)3. 更多的数据类型支持4. 更多的表属性支持5. 美化输出6. 支持表名替换7. 支持--complete-insert |
| v0.3 | 2023.10.13 | 支持5.7升级到8.0的ibd文件      | 修复一些BUG                                  |
| v1.0 | 2024.01.05 | 支持debug支持更多类型和功能       | 1. 支持DEBUG2. 支持分区表3. 支持唯一索引4.支持虚拟列5. 支持instant6.支持约束和外键7. 支持限制输出8.支持前缀索引 |
| v1.1 | 2024.04.12 | 修复一些bug                | 1. 8.0.13 默认值时间戳2. 8.0.12 无hidden3. online ddl instant |
| v1.2 | 2024.04.25 | 新增空间坐标的支持              | 支持geometry[collection],[multi]point,[multi]linestring,[multi]polygon |
| v1.3 | 2024.05.11 | 支持mysql 5.7            | 本来准备做二级分区支持的, 但看了下, WC, 太复杂了-_- 那就更新个支持5.7的吧(其实结构和8.0是差不多的) (for issue 7) |
| v1.4 | 2024.05.21 | 修复已知BUG, 完善测试案例.支持溢出页. | 1. 修复已知BUG.  <br />2. 完善测试案例(支持5.6).<br />3. 完善相关文档.<br />4. 支持溢出页<br />5. 支持字段的ascii字符集.<br />6. 支持子分区(二级分区) |
| v1.5 | 2024.07.10 | instant相关BUG修复,vector数据类型的支持  | 1. 修复INSTANT相关的BUG(重写了相关代码).  <br />2. 支持mysql9.0新增的vector数据类型 <br />3.完善测试脚本 |
| v1.6 | 2024.09.19 | 修复一些BUG | 修复一些BUG |
| v1.7 | 2024.10.29 | 修复一些BUG并新增一些功能 | 1.修复已知BUG<br />2.支持压缩页的解析(zlib&lz4)<br />3.支持drop表的恢复<br />4.支持ucs2,utf16,utf32字符集 |
| v1.8 | 2024.11.09 | 并新增一些功能 | 1.新增web控制台查看ibd文件结构 <br />2.支持Keyring加密表的解析<br />3.支持mysql的所有字符集<br />4.支持lower_case_table_names参数的修改 <br />5. 支持redundant行格式的解析 <br />6. 修复已知BUG(比如decimal小数部分填充问题)|
| v1.9 | 2025.02.21 | 支持直接解析5.7的ibd文件| 1.修复已知BUG <br />2. 支持直接解析5.7的ibd文件|
| v1.10 | 2025.04.16 |修改已知BUG & 添加快速统计表行的脚本 |
| v1.11 | 2025.06.13 |修改已知BUG &  设置--foce 为遍历整个数据文件(1. 跳过坏块 2.ibd文件不完整 3. delete page被剔除btree+ |



# BUG修复 

1. [前缀索引](https://www.modb.pro/db/1700402156981538816)支持. 前缀索引完整数据在数据字段而不是KEY
2. [json/blob等大对象](https://www.modb.pro/db/626066)支持: 支持大对象
3. [5.7升级到8.0后找不到SDI](https://github.com/ddcw/ibd2sql/issues/5). :sdi pagno 记录在第一页
4. [bigint类型,注释,表属性](https://github.com/ddcw/ibd2sql/issues/2) : 支持更多数据类型, 和表属性
5. [只有1个主键和其它](https://github.com/ddcw/ibd2sql/issues/4) : 支持只有1个主键的情况, 并新增DEBUG功能
6. [默认值为时间戳](https://github.com/ddcw/ibd2sql/issues/8) : 支持默认值为时间戳, blob等字段的前缀索引
7. [8.0.12 无hidden](https://github.com/ddcw/ibd2sql/issues/10) : 取消hidden检查
8. [ONLINE DDL instant](https://github.com/ddcw/ibd2sql/issues/12) : record 1-2 bit is instant flag
9. [mysql 5.7 解析无数据](https://github.com/ddcw/ibd2sql/issues/17) : mysql 5.7无SDI PAGE, INODE不需要去掉第一个INDEX
10. [char字段为ascii](https://github.com/ddcw/ibd2sql/issues/9) : char字段如果是ascii字符集则不会额外记录字段长度
11. instant相关BUG和vector的支持
12. varchar <=255 时使用1bytes存储大小
13. instant nullable计算方式.
14. decimal小数部分以0开头时,未作填充
15. [超多列的情况][https://github.com/ddcw/ibd2sql/issues/28](https://github.com/ddcw/ibd2sql/issues/28)
16. [issue 16:decimal符号问题](https://github.com/ddcw/ibd2sql/issues/58)
17. [外键显示问题](https://github.com/ddcw/ibd2sql/issues/57)
