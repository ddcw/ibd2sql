from ibd2sql.dictionary.sys_columns import sdi_sys_columns
from ibd2sql.dictionary.sys_datafiles import sdi_sys_datafiles
from ibd2sql.dictionary.sys_fields import sdi_sys_fields
from ibd2sql.dictionary.sys_foreign_cols import sdi_sys_foreign_cols
from ibd2sql.dictionary.sys_foreign import sdi_sys_foreign
from ibd2sql.dictionary.sys_indexes import sdi_sys_indexes
from ibd2sql.dictionary.sys_tablespaces import sdi_sys_tablespaces
from ibd2sql.dictionary.sys_tables import sdi_sys_tables
from ibd2sql.dictionary.sys_virtual import sdi_sys_virtual

def GET_SYS_TABLES_SDI():
	return {
		'sys_columns':sdi_sys_columns,
		'sys_datafiles':sdi_sys_datafiles,
		'sys_fields':sdi_sys_fields,
		'sys_foreign_cols':sdi_sys_foreign_cols,
		'sys_foreign':sdi_sys_foreign,
		'sys_indexes':sdi_sys_indexes,
		'sys_tablespaces':sdi_sys_tablespaces,
		'sys_tables':sdi_sys_tables,
		'sys_virtual':sdi_sys_virtual
	}

def GET_INDEXID_BY_TBLNAME(tblname):
	dd = {'sys_tables':1,'sys_columns':2,'sys_indexes':3,'sys_fields':4,'sys_foreign':11,'sys_foreign_cols':14,'sys_tablespaces':15,'sys_datafiles':16,'sys_virtual':17}
	return dd[tblname]
