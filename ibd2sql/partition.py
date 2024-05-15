def subpartition(dd):
	"""
	1级只能是 range/list
	2级只能是 hash/key
	"""
	ddl = ""
	# 一级分区
	if dd['partition_type'] == 1: # HASH
		return ddl
	elif dd['partition_type'] == 3: # KEY
		return ddl
	elif dd['partition_type'] == 7: # RANGE
		ddl += f"/*!50100 PARTITION BY RANGE ({dd['partition_expression_utf8']})"
	elif dd['partition_type'] == 8 : # LIST
		ddl += f"/*!50100 PARTITION BY LIST ({dd['partition_expression_utf8']})"
	else:
		return ddl
	ddl += "\n"

	# 子分区
	if dd['subpartition_type'] == 1: # HASH
		ddl += f"SUBPARTITION BY HASH ({dd['subpartition_expression_utf8']})"
	elif dd['subpartition_type'] == 3: # KEY
		ddl += f"SUBPARTITION BY KEY ({dd['subpartition_expression_utf8']})"

	# 具体的partitions部分
	# 判断是否为 autopartition
	ISAUTO = True # 怎么判断呢, 就随缘吧 0.0
	pn = -1
	for p in dd['partitions']:
		pn += 1
		if f"p{pn}" != p['name']:
			ISAUTO = False
			break
		spn = -1
		for sp in p['subpartitions']:
			spn += 1
			if f"p{pn}sp{spn}" != sp['name']:
				ISAUTO = False
				break
	if ISAUTO:
		ddl += f"\nSUBPARTITIONS {len(dd['partitions'][0]['subpartitions'])}\n("
		if dd['partition_type'] == 7:
			ddl += ",\n".join([ f"PARTITION {x['name']} VALUES LESS THAN {'('+x['values'][0]['value_utf8']+')' if not x['values'][0]['max_value'] else 'MAXVALUE'}" for x in dd['partitions'] ]) + ")"
		elif dd['partition_type'] == 8:
			ddl += ",\n".join([ f"PARTITION {x['name']} VALUES IN ({','.join([ _x['value_utf8'] for _x in x['values']])})" for x in dd['partitions'] ]) + ")"
		ddl += " */"
	else:
		ddl += "(\n"
		for p in dd['partitions']:
			if dd['partition_type'] == 7:
				ddl += f"    PARTITION {p['name']} VALUES LESS THAN {'('+p['values'][0]['value_utf8']+')' if not p['values'][0]['max_value']  else 'MAXVALUE'}\n"
			elif dd['partition_type'] == 8:
				ddl += f"    PARTITION {p['name']} VALUES in ({','.join([ x['value_utf8'] for x in p['values']])})\n"
			_ddl = ""
			for sp in p['subpartitions']:
				_ddl += f"        SUBPARTITION {sp['name']} ENGINE = {sp['engine']},\n"
			ddl += "        (" + _ddl[8:-2] +  "),\n"

		ddl = ddl[:-2] + ")*/"	
	return ddl
