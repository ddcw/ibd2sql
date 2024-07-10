# 元数据

```
"se_private_data": "physical_pos=4;version_dropped=1;"
"se_private_data": "default=6363;physical_pos=6;table_id=4960;version_added=2;"
```



# 数据行

```
VARSIZE|null_bitmask|row_version/column_count|rec_header|key|trx&rollptr|data

8.0.12-28 若使用add column instant 则为column_count (1-2字节)
8.0.29 及其以上 若使用add/drop column instant, 则为row version

rec_header:
instant_flag: 1 bit (only <=8.0.28)
row_version_flag: 1bit (only >=8.0.29)
```



# 数据读取规则

当row version的版本比元数据里的版本新的时候, 以数据行的数据为主

当row version的版本比元数据里面的版本旧的时候: 若为drop, 则正常读取数据.; 若为add, 则读取元数据中的默认值.