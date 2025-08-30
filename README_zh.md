# ibd2sql

[english](https://github.com/ddcw/ibd2sql/blob/ibd2sql-v2.x/README.md)

[ibd2sql](https://github.com/ddcw/ibd2sql) 是一个解析MySQL数据文件的工具. ~~老NB了~~. 使用python3编写的,没得依赖包, 下载就能使用, 所以也就不提供二进制包了.

当你只剩下IBD文件或者剩下半截数据文件的时候, 你可以使用`ibd2sql`去恢复其中的数据.



# 下载和使用

## 下载

**Linux**

```shell
wget https://github.com/ddcw/ibd2sql/archive/refs/heads/ibd2sql-v2.x.zip
unzip ibd2sql-v2.x.zip
cd ibd2sql-ibd2sql-v2.x/
```



**Windows**

点击下载: https://github.com/ddcw/ibd2sql/archive/refs/heads/ibd2sql-v2.x.zip



## 使用

**Linux**

```shell
python3 main.py your_file.ibd --sql --ddl
```



**Windows**

windows环境python3是叫做python,名字问题,小坑

```powershell
python main.py your_file.ibd --sql --ddl
```



## WEB 控制台

```
python3 main.py your_file.ibd --web
# 执行之后,就可以使用浏览器访问: http://你的IP地址:8080
```



完整的使用说明: [docs/USAGE.md](https://github.com/ddcw/ibd2sql/blob/ibd2sql-v2.x/docs/USAGE.md)



# 性能

环境说明: MySQL 8.0.28  Python 3.10.4 CPU MHz: 2688.011 

| ibd2sql VERSION | PARALLEL | RATE                   |
| --------------- | -------- | ---------------------- |
| 2.0             | 1        | 50941 行每秒, 25MB/s   |
| 2.0             | 8        | 209993 行每秒, 104MB/s |
| 1.12            | -        | 12037 行每秒, 6MB/s    |
| 0.3             | -        | 53998 行每秒, 26MB/s   |

2000W行数据,5GB大小, 开16并发,差不多2分半解析完. 由于CPU不多,磁盘性能也不行, 所以没测出来上限是多少 -_-



# 修改日志

| 版本 | 更新时间 | 简述                                    |
| ---- | -------- | --------------------------------------- |
| 2.x  | 2025.8   | 支持范围更广, 并且性能更高, 还支持并发! |
| 1.x  | 2024.1   | 支持所有数据类型,也支持5.7环境          |
| 0.x  | 2023.4   | 只支持8.0的部分情况                     |

完整的历史更新记录: [docs/CHANGELOG.md](https://github.com/ddcw/ibd2sql/blob/ibd2sql-v2.x/docs/CHANGELOG.md)



# 要求和支持范围

要求: Python >= 3.6

支持: MySQL 5.6, MySQL 5.7, MySQL 8.0, MySQL 8.4. MySQL 9.x



**数据备份更重要**, 事后恢复不是万能的.

