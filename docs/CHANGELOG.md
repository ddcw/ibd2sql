# CHANGE LOG



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