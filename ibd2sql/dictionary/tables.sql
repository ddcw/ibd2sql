-- mysql 5.7的系统表DDL
-- 参考
-- dict/dict0crea.cc
-- include/dict0boot.h
-- dict/dict0boot.cc
-- dict/dict0dict.cc
-- ...

-- index_id 1
drop table if exists sys_tables;
create table sys_tables(
	name varchar(654),
	id bigint unsigned,
	n_cols int unsigned,
	`type` int unsigned,
	mix_id bigint unsigned,
	mix_len int unsigned,
	cluster_name varchar(255),
	space int unsigned,
	primary key(name)
) engine=innodb row_format=redundant charset=latin1;

-- index_id 2
drop table if exists sys_columns;
create table sys_columns(
	table_id bigint unsigned,
	pos int unsigned,
	name varchar(255),
	mtype int unsigned, -- main data type
	prtype int unsigned, -- precise type: charset(16 bit),nullable,signed...
	len int unsigned,
	prec int unsigned,
	primary key(table_id,pos)
) engine=innodb row_format=redundant;

-- index_id 3
drop table if exists sys_indexes;
create table sys_indexes(
	table_id bigint unsigned,
	id bigint unsigned, -- indexid
	name varchar(255),
	n_fields int unsigned,
	`type` int unsigned,
	space int unsigned,
	page_no int unsigned,
	merge_threshold int unsigned,
	primary key(table_id,id)
) engine=innodb row_format=redundant;

-- index_id 4
drop table if exists sys_fields;
create table sys_fields(
	index_id bigint unsigned,
	pos int unsigned,
	col_name varchar(255),
	primary key(index_id,pos)
) engine=innodb row_format=redundant;

-- index_id 11
drop table if exists sys_foreign;
create table sys_foreign(
	name varchar(255),
	for_name varchar(255),
	ref_name varchar(255),
	n_cols int unsigned,
	primary key(name), -- index_id 11
	key(for_name), -- index_id 12
	key(ref_name) -- index_id 13
) engine=innodb row_format=redundant;

-- index_id 14 
drop table if exists sys_foreign_cols;
create table sys_foreign_cols(
	name varchar(255),
	pos int unsigned,
	for_col_name varchar(255),
	ref_col_name varchar(255),
	primary key(name, pos)
) engine=innodb row_format=redundant;

-- index_id 15 
drop table if exists sys_tablespaces;
create table sys_tablespaces(
	space int unsigned, -- index_id
	name varchar(255),
	flags int unsigned,
	primary key(space)
) engine=innodb row_format=redundant;

-- index_id 16 
drop table if exists sys_datafiles;
create table sys_datafiles(
	space int unsigned, -- index_id
	path varchar(255),
	primary key(space)
) engine=innodb row_format=redundant;

-- index_id 17 
drop table if exists sys_virtual;
create table sys_virtual(
	table_id bigint unsigned,
	pos int unsigned,
	base_pos int unsigned,
	primary key(table_id,pos,base_pos)
) engine=innodb row_format=redundant;

