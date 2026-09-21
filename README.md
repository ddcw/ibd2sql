[中文版介绍](https://github.com/ddcw/ibd2sql/blob/ibd2sql-v2.x/README_zh.md)

# ibd2sql

[ibd2sql](https://github.com/ddcw/ibd2sql) is tool of transform MySQL IBD file to SQL(data). Write using Python3 .

When you only have IBD data file or a portion of IBD data files left, you can use `ibd2sql` to parse the data within it.

Or when you drop/truncate some table, you can also use `ibd2sql` to parse the remaining data on the disk



# DOWNLOAD & USAGE

## download

```shell
wget https://github.com/ddcw/ibd2sql/archive/refs/heads/ibd2sql-v2.x.zip
unzip ibd2sql-v2.x.zip
cd ibd2sql-ibd2sql-v2.x/
```

## usage

```shell
python3 main.py your_file.ibd --sql --ddl
```

More usage: [docs/USAGE.md](https://github.com/ddcw/ibd2sql/blob/ibd2sql-v2.x/docs/USAGE.md)

Recovery deleted data: [docs/example_recovery_delete_row.md](https://github.com/ddcw/ibd2sql/blob/ibd2sql-v2.x/docs/example_recovery_delete_row.md)

Recovery dropped data: [docs/example_recovery_drop_table.md](https://github.com/ddcw/ibd2sql/blob/ibd2sql-v2.x/docs/example_recovery_drop_table.md)

Recovery truncated data: [docs/example_recovery_truncate_table.md](https://github.com/ddcw/ibd2sql/blob/ibd2sql-v2.x/docs/example_recovery_truncate_table.md)



# CHANGE LOG

| VERSION | UPDATE | NOTE                                                       |
| ------- | ------ | ---------------------------------------------------------- |
| 2.x     | 2025.8 | Support for more situations and improvement in performance |
| 1.x     | 2024.1 | Supports complete data types and 5.7                       |
| 0.x     | 2023.4 | Only supports partial cases of 8.0                         |

detail: [docs/CHANGELOG.md](https://github.com/ddcw/ibd2sql/blob/ibd2sql-v2.x/docs/CHANGELOG.md)



# REQUIRE & SUPPORT

require: Python >= 3.6

support: MySQL 5.x, MySQL 8.x, MySQL 9.x

**Data backup is very important**

