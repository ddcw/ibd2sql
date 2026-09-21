# 介绍

[ibd2sql](https://github.com/ddcw/ibd2sql) 是一个解析MySQL数据文件的工具. 使用python3编写的,没得依赖包, 下载就能使用.

可用于数据恢复(delete/drop/truncate/rm)与学习.



# 使用

使用方法为:

```txt
python3 main.py IBD_FILE_LIST [--option --options ...]
```

比如:

```shell
# 解析指定数据文件
python3 main.py /data/db1/t1.ibd --ddl --sql

# 解析多个数据文件
python3 main.py /data/db1/t1.ibd /data/db1/t2.ibd --ddl --sql

# 解析某个目录下的所有数据文件
python3 main.py /data/db1/* --ddl --sql
```

各选项含义见: [docs/options.md](https://github.com/ddcw/ibd2sql/blob/ibd2sql-v2.x/docs/options.md)

基础用法见: [docs/example.md](https://github.com/ddcw/ibd2sql/blob/ibd2sql-v2.x/docs/example.md)

二次开发: [docs/dev.md](https://github.com/ddcw/ibd2sql/blob/ibd2sql-v2.x/docs/dev.md)




# 支持范围

支持mysql5.x,8.x,9.x等版本的所有数据类型,所有字符集,所有行格式.

支持压缩,加密表,innodb_page_size非标准的16K.

具体支持范围可见:[docs/supports.md](https://github.com/ddcw/ibd2sql/blob/ibd2sql-v2.x/docs/supports.md)



# 使用场景

恢复被delete的数据: [docs/example_recovery_delete_row.md](https://github.com/ddcw/ibd2sql/blob/ibd2sql-v2.x/docs/example_recovery_delete_row.md)

恢复被drop的数据: [docs/example_recovery_drop_table.md](https://github.com/ddcw/ibd2sql/blob/ibd2sql-v2.x/docs/example_recovery_drop_table.md)

恢复被truncate的数据: [docs/example_recovery_truncate_table.md](https://github.com/ddcw/ibd2sql/blob/ibd2sql-v2.x/docs/example_recovery_truncate_table.md)

恢复被rm的库/表: [docs/example_recovery_rm.md](https://github.com/ddcw/ibd2sql/blob/ibd2sql-v2.x/docs/example_recovery_rm.md)

恢复带有坏块的数据文件: [docs/example_recovery_from_bad_block.md](https://github.com/ddcw/ibd2sql/blob/ibd2sql-v2.x/docs/example_recovery_from_bad_block.md)

从碎片文件中恢复数据: [docs/example_recovery_frag_page.md](https://github.com/ddcw/ibd2sql/blob/ibd2sql-v2.x/docs/example_recovery_frag_page.md)


