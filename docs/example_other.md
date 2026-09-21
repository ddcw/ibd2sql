一些不好归类的场景.



# 查看被删除的用户

由于我们可以解析系统表,所以也能解析系统表中记录的用户信息,权限信息之类的.

```shell
# 获取被删除用户及其全局权限
python3 main.py /data/mysql_8037/mysqldata/mysql.ibd --set table=user --sql --delete
```

