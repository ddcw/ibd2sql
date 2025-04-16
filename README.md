# INTRODUCE

[中文版介绍](https://github.com/ddcw/ibd2sql/blob/main/README_zh.md)

[ibd2sql](https://github.com/ddcw/ibd2sql) is tool of transform mysql ibd file to sql(data). It can parse *IBD* files into *SQL* statements. ibd2sql written with Python is commonly used to learn *IBD* files and data recovery.



# FEATURE

~~Simple and useful !~~

Security: as long as the file has **read** permission.

Comprehensiveness: **all** column types in mysql 5.x or 8.x or 9.x

Simple: using Python to write packages without third-party dependencies.

Useful: parse data with mark of deleted (--delete).





# DOWNLOAD & USAGE

v1.10 url : [https://github.com/ddcw/ibd2sql/archive/refs/tags/v1.10.tar.gz](https://github.com/ddcw/ibd2sql/archive/refs/tags/v1.10.tar.gz)



## download

**Linux**

```shell
wget https://github.com/ddcw/ibd2sql/archive/refs/heads/main.zip
unzip main.zip
cd ibd2sql-main
```

**Windows**

click [https://github.com/ddcw/ibd2sql/archive/refs/heads/main.zip](https://github.com/ddcw/ibd2sql/archive/refs/heads/main.zip) to download



## usage

**Linux**

```shell
python3 main.py /PATH/your_dir/xxxx.ibd --sql --ddl
# or use redirection to save data
python3 main.py /PATH/your_dir/xxxx.ibd --sql --ddl > xxx.sql
```

**Windows**

Python3 is called Python on Windows

Path usage '\\' instead of '/'



```shell
python main.py F:\t20240627\test\ddcw_char_ascii.ibd --sql --ddl
```

**WEB CONSOLE**
```shell
python3 ibd2sql_web.py /PATH/your_dir/xxxx.ibd
# and then, you can visit http://yourip:8080 to view that ibd file
```

more usage:  [docs/USAGE.md](https://github.com/ddcw/ibd2sql/blob/main/docs/USAGE.md)



# Example

env linux:

```shell
# suggestion cp file to anothor OS/FS
SHELL> cp -ra /data/mysql_3314/mysqldata/db1/test_ibd2sql.ibd /tmp

SHELL> python3 main.py /tmp/test_ibd2sql.ibd --ddl --sql
CREATE TABLE IF NOT EXISTS `db1`.`test_ibd2sql`(
    `id` int NULL,
    `name` varchar(127) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci ;
INSERT INTO `db1`.`test_ibd2sql` VALUES (1, 'ddcw');
INSERT INTO `db1`.`test_ibd2sql` VALUES (2, 'ibd2sql v1.5');

```

more example: [docs/ALLTEST.md](https://github.com/ddcw/ibd2sql/blob/main/docs/ALLTEST.md)



# CHANGE LOG

| VERSION | UPDATE     | NOTE                                     |
| ------- | ---------- | ---------------------------------------- |
| v0.1    | 2023.4.27  | first version                            |
| v0.2    | 2023.08.30 | support more data types                  |
| v0.3    | 2023.10.13 | support parse file from 5.x upgrade to 8.x |
| v1.0    | 2024.01.05 | add debug and support more data types    |
| v1.1    | 2024.04.12 | fix some bugs                            |
| v1.2    | 2024.04.25 | add support of geometry data types       |
| v1.3    | 2024.05.11 | add support 5.x                          |
| v1.4    | 2024.05.21 | add support extra page and subpartition  |
| v1.5    | 2024.07.10 | add support vector data types and fix INSTANT bug |
| v1.6    | 2024.09.19 | fix some bugs |
| v1.7    | 2024.10.29 | fix some bugs&support compress page&support recovery **drop table** & support ucs2,utf16,utf32 charset |
| v1.8    | 2024.11.09 | support keyring plugin encryption & all character set|
| v1.9    | 2025.02.21 | fix some bugs & support direct parsing of 5.x files|
| v1.10    | 2025.04.16 | fix some bugs & add super_fast_count.py|

detail: [docs/CHANGELOG.md](https://github.com/ddcw/ibd2sql/blob/main/docs/CHANGELOG.md)



# REQUIRE & SUPPORT

require: python3

support range: mysql5.x 8.x 9.x
