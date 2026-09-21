mysql中被delete的数据,会在对应的行上打上deleted标记, 而不会立即真正删除,所以我们还是可以恢复的. 使用方法即额外加上`--delete`即可.

如果一个页中的数据全部被delete了,那么该页就不在btr+中了, 只遍历btr+是无法获取到全部被delete的数据,所以得加上`--force`从而获取数据文件中全部被delete的数据.

```shell
# 在btr+中,仅获取被delete的数据.
python3 main.py /data/mysql_8037/mysqldata/db1/t20260920.ibd --sql --delete

# 在btr+中,获取被delete和未被delete的数据
python3 main.py /data/mysql_8037/mysqldata/db1/t20260920.ibd --sql --delete with

# 在btr+中,获取被delete和未被delete的数据,使用replace代替insert
python3 main.py /data/mysql_8037/mysqldata/db1/t20260920.ibd --sql --delete with --replace

# 在btr+中,获取被delete和未被delete的数据,使用replace代替insert,且包含字段名
python3 main.py /data/mysql_8037/mysqldata/db1/t20260920.ibd --sql --delete with --replace --complete-insert


# 在整个ibd文件中,仅获取被delete的数据.
python3 main.py /data/mysql_8037/mysqldata/db1/t20260920.ibd --sql --delete --force

# 在整个ibd文件中,获取被delete和未被delete的数据
python3 main.py /data/mysql_8037/mysqldata/db1/t20260920.ibd --sql --delete with --force

# 在整个ibd文件中,获取被delete和未被delete的数据,使用replace代替insert
python3 main.py /data/mysql_8037/mysqldata/db1/t20260920.ibd --sql --delete with --replace --force

# 在整个ibd文件中,获取被delete和未被delete的数据,使用replace代替insert,且包含字段名
python3 main.py /data/mysql_8037/mysqldata/db1/t20260920.ibd --sql --delete with --replace --complete-insert --force

# 在整个ibd文件中,仅获取被delete的数据.从第4页开始
python3 main.py /data/mysql_8037/mysqldata/db1/t20260920.ibd --sql --delete --force --set leafno=4
```



备注: 无法做到100%恢复被delete的数据. 如果被delete的数据对应的空间如果被回收了,则无法通过ibd文件进行恢复, 此时需要备份或者日志.