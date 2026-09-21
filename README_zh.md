[English](https://github.com/ddcw/ibd2sql/blob/ibd2sql-v2.x/README.md)

# ibd2sql

[ibd2sql](https://github.com/ddcw/ibd2sql) 是一个解析MySQL数据文件的工具. 使用python3编写的,没得依赖包, 下载就能使用.

可用于表结构获取,数据恢复(delete/drop/truncate/rm)与学习.



# 下载和使用

## 下载
```shell
wget https://github.com/ddcw/ibd2sql/archive/refs/heads/ibd2sql-v2.x.zip
unzip ibd2sql-v2.x.zip
cd ibd2sql-ibd2sql-v2.x/
```

## 使用

```shell
python3 main.py your_file.ibd --sql --ddl
```

使用说明: [docs/USAGE.md](https://github.com/ddcw/ibd2sql/blob/ibd2sql-v2.x/docs/USAGE.md)

恢复被delete的数据: [docs/example_recovery_delete_row.md](https://github.com/ddcw/ibd2sql/blob/ibd2sql-v2.x/docs/example_recovery_delete_row.md)

恢复被drop的数据: [docs/example_recovery_drop_table.md](https://github.com/ddcw/ibd2sql/blob/ibd2sql-v2.x/docs/example_recovery_drop_table.md)

恢复被truncate的数据: [docs/example_recovery_truncate_table.md](https://github.com/ddcw/ibd2sql/blob/ibd2sql-v2.x/docs/example_recovery_truncate_table.md)



# 修改日志

| 版本 | 更新时间 | 简述                                    |
| ---- | -------- | --------------------------------------- |
| 2.x  | 2025.8   | 支持范围更广, 并且性能更高, 还支持并发! |
| 1.x  | 2024.1   | 支持所有数据类型,也支持5.7环境          |
| 0.x  | 2023.4   | 只支持8.0的部分情况                     |

完整的历史更新记录: [docs/CHANGELOG.md](https://github.com/ddcw/ibd2sql/blob/ibd2sql-v2.x/docs/CHANGELOG.md)



# 要求和支持范围

要求: Python >= 3.6

支持: MySQL 5.x, MySQL 8.x, MySQL 9.x



**数据备份更重要**, 事后恢复不是万能的.


