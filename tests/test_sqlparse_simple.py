from src.tds.sqlparse_simple import (
    extract_table_and_columns,
    extract_values,
    reconstruct_insert,
    reconstruct_update,
    extract_multirow_values,
    reconstruct_multirow_insert,
)


def test_insert_extract_and_reconstruct():
    sql = "INSERT INTO dbo.T (A,B) VALUES ('x', '2')"
    table, cols = extract_table_and_columns(sql)
    assert table.lower() == 'dbo.t' and cols == ['A','B']
    vals = extract_values(sql)
    assert vals == ['x','2']
    new = reconstruct_insert(sql, ['y','3'])
    assert "VALUES ('y'" in new and '3' in new


def test_update_extract_and_reconstruct():
    sql = "UPDATE dbo.T SET A = 'x', B= 2 WHERE Id=1"
    table, cols = extract_table_and_columns(sql)
    assert table.lower() == 'dbo.t'
    vals = extract_values(sql)
    assert vals == ['x','2']
    new = reconstruct_update(sql, cols, ['z','5'])
    assert "SET A = 'z', B = 5" in new


def test_multirow():
    sql = "INSERT INTO T (A,B) VALUES ('x',1), ('y',2)"
    rows = extract_multirow_values(sql)
    assert rows == [['x','1'], ['y','2']]
    rebuilt = reconstruct_multirow_insert(sql, rows)
    assert 'VALUES (\'x\', 1), (\'y\', 2)' in rebuilt
