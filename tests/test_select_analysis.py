from scripts.aggregate_profiles import extract_columns
from src.tds.sqlparse_simple import extract_select_info


def test_select_extract_info_star_and_cols():
    sql1 = "SELECT * FROM dbo.Orders"
    tables, cols, star = extract_select_info(sql1)
    assert tables == ["dbo.Orders"] and star is True and cols == []

    sql2 = "SELECT Id, Amount FROM [dbo].[Payments] WHERE Amount > 0"
    tables2, cols2, star2 = extract_select_info(sql2)
    assert tables2 == ["dbo.Payments"] and star2 is False and cols2 == ["Id", "Amount"]


def test_extract_columns_for_insert_and_update():
    ins = "INSERT INTO dbo.T (A,B) VALUES ('x',1)"
    upd = "UPDATE dbo.T SET A='y' WHERE Id=1"
    assert extract_columns(ins) and extract_columns(upd)

