# ibd2sql

[中文版介绍](https://github.com/ddcw/ibd2sql/blob/ibd2sql-v2.x/README_zh.md)

[ibd2sql](https://github.com/ddcw/ibd2sql) is tool of transform MySQL IBD file to SQL(data). Write using Python3 .

When you only have IBD data file or a portion of IBD data files left, you can use `ibd2sql` to parse the data within it.



# DOWNLOAD & USAGE

## download

**Linux**

```shell
wget https://github.com/ddcw/ibd2sql/archive/refs/heads/ibd2sql-v2.x.zip
unzip ibd2sql-v2.x.zip
cd ibd2sql-ibd2sql-v2.x/
```



**Windows**

click https://github.com/ddcw/ibd2sql/archive/refs/heads/ibd2sql-v2.x.zip to download



## usage

**Linux**

```shell
python3 main.py your_file.ibd --sql --ddl
```



**Windows**

Python3 is called Python on Windows

```powershell
python main.py your_file.ibd --sql --ddl
```



## WEB CONSOLE

```
python3 main.py your_file.ibd --web
# and then, you can visit http://yourip:8080 to view that ibd file
```



more usage: [docs/USAGE.md](https://github.com/ddcw/ibd2sql/blob/ibd2sql-v2.x/docs/USAGE.md)



# PERFORMANCE

env: MySQL 8.0.28  Python 3.10.4 CPU MHz: 2688.011 

| ibd2sql VERSION | PARALLEL | RATE                   |
| --------------- | -------- | ---------------------- |
| 2.0             | 1        | 50941 rows/s, 25MB/s   |
| 2.0             | 8        | 209993 rows/s, 104MB/s |
| 1.12            | -        | 12037 rows/s, 6MB/s    |
| 0.3             | -        | 53998 rows/s, 26MB/s   |



# CHANGE LOG

| VERSION | UPDATE | NOTE                                                       |
| ------- | ------ | ---------------------------------------------------------- |
| 2.x     | 2025.8 | Support for more situations and improvement in performance |
| 1.x     | 2024.1 | Supports complete data types and 5.7                       |
| 0.x     | 2023.4 | Only supports partial cases of 8.0                         |

detail: [docs/CHANGELOG.md](https://github.com/ddcw/ibd2sql/blob/ibd2sql-v2.x/docs/CHANGELOG.md)



# REQUIRE & SUPPORT

require: Python >= 3.6

support: MySQL 5.6, MySQL 5.7, MySQL 8.0, MySQL 8.4. MySQL 9.x

**Data backup is very important**
