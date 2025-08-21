from src.tds.sqlparse_simple import (
    detect_bulk_insert,
    detect_merge,
    extract_select_info,
)


def test_detect_bulk_insert_simple():
    sql = "BULK INSERT dbo.Customers FROM 'C:\\data\\cust.csv' WITH (FIELDTERMINATOR=',')"
    table, path = detect_bulk_insert(sql)
    assert table.lower() == 'dbo.customers'
    assert path.endswith('cust.csv')


def test_detect_merge_update_and_insert():
    sql = (
        "MERGE INTO [dbo].[Target] AS t USING dbo.Source s ON t.Id = s.Id "
        "WHEN MATCHED THEN UPDATE SET t.Email = s.Email, t.[Phone] = s.Phone "
        "WHEN NOT MATCHED THEN INSERT (Id, Email) VALUES (s.Id, s.Email);"
    )
    target, upd_cols, ins_cols = detect_merge(sql)
    assert target.lower() == 'dbo.target'
    assert set(upd_cols) == {"Email", "Phone"}
    assert ins_cols == ["Id", "Email"]


def test_extract_select_info_star_and_columns():
    sql1 = "SELECT * FROM dbo.Users WHERE IsActive = 1"
    tables, cols, star = extract_select_info(sql1)
    assert star is True and tables == ["dbo.Users"] and cols == []

    sql2 = "SELECT Id, Email FROM [dbo].[Users]"
    tables2, cols2, star2 = extract_select_info(sql2)
    assert star2 is False and tables2 == ["dbo.Users"] and cols2 == ["Id", "Email"]

