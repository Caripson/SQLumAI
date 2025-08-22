import re
from typing import List, Tuple, Optional


def extract_table_and_columns(sql_text: str) -> Tuple[Optional[str], List[str]]:
    sql = sql_text.strip()
    m = re.search(r"insert\s+into\s+([\w\.\[\]]+)\s*\(([^\)]+)\)", sql, re.IGNORECASE)
    if m:
        table = m.group(1)
        columns = [c.strip(" []") for c in m.group(2).split(",")]
        return table, columns
    m2 = re.search(r"update\s+([\w\.\[\]]+)\s+set\s+(.+?)\s+where\s", sql, re.IGNORECASE | re.DOTALL)
    if m2:
        table = m2.group(1)
        assigns = m2.group(2)
        columns = []
        for part in assigns.split(","):
            left = part.split("=")[0].strip(" []")
            columns.append(left)
        return table, columns
    return None, []


def _split_csv_respecting_quotes(s: str) -> List[str]:
    out: List[str] = []
    buf = []
    in_q = False
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == "'":
            in_q = not in_q
            buf.append(ch)
        elif ch == "," and not in_q:
            out.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
        i += 1
    if buf:
        out.append("".join(buf).strip())
    return out


def extract_values(sql_text: str) -> List[str]:
    sql = sql_text.strip()
    m = re.search(r"insert\s+into\s+[\w\.\[\]]+\s*\([^\)]+\)\s*values\s*\(([^\)]+)\)", sql, re.IGNORECASE | re.DOTALL)
    if m:
        raw_vals = _split_csv_respecting_quotes(m.group(1))
        out: List[str] = []
        for v in raw_vals:
            if v.startswith("'") and v.endswith("'"):
                out.append(v[1:-1])
            else:
                out.append(v)
        return out
    m2 = re.search(r"update\s+[\w\.\[\]]+\s+set\s+(.+?)\s+where\s", sql, re.IGNORECASE | re.DOTALL)
    if m2:
        assigns = m2.group(1)
        out: List[str] = []
        for part in _split_csv_respecting_quotes(assigns):
            if "=" in part:
                _, right = part.split("=", 1)
                v = right.strip()
                if v.startswith("'") and v.endswith("'"):
                    out.append(v[1:-1])
                else:
                    out.append(v)
        return out
    return []


def reconstruct_insert(sql_text: str, new_values: List[str]) -> Optional[str]:
    sql = sql_text
    m = re.search(r"(insert\s+into\s+[\w\.\[\]]+\s*\([^\)]+\)\s*values\s*\()([^\)]+)(\).*)", sql, re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    prefix, old_vals, suffix = m.groups()
    encoded = []
    for v in new_values:
        if re.match(r"^-?\d+(\.\d+)?$", v or ""):
            encoded.append(v)
        else:
            encoded.append("'" + v.replace("'", "''") + "'")
    return prefix + ", ".join(encoded) + suffix


def reconstruct_update(sql_text: str, columns: List[str], new_values: List[str]) -> Optional[str]:
    m = re.search(r"(update\s+[\w\.\[\]]+\s+set\s+)(.+?)(\s+where\s.+)", sql_text, re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    prefix, assigns, suffix = m.groups()
    parts = []
    for col, v in zip(columns, new_values):
        if re.match(r"^-?\d+(\.\d+)?$", v or ""):
            parts.append(f"{col} = {v}")
        else:
            escaped = (v or "").replace("'", "''")
            parts.append(f"{col} = '{escaped}'")
    return prefix + ", ".join(parts) + suffix


def extract_multirow_values(sql_text: str) -> Optional[List[List[str]]]:
    # INSERT ... VALUES (...),(...) ...
    m = re.search(r"insert\s+into\s+[\w\.\[\]]+\s*\([^\)]+\)\s*values\s*(.+)$", sql_text, re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    tail = m.group(1)
    rows: List[List[str]] = []
    depth = 0
    buf = []
    for ch in tail:
        if ch == "(":
            depth += 1
            if depth == 1:
                buf = []
                continue
        if ch == ")":
            depth -= 1
            if depth == 0:
                row = _split_csv_respecting_quotes("".join(buf))
                clean = []
                for v in row:
                    if v.startswith("'") and v.endswith("'"):
                        clean.append(v[1:-1])
                    else:
                        clean.append(v)
                rows.append(clean)
                buf = []
                continue
        if depth >= 1:
            buf.append(ch)
    return rows or None


def reconstruct_multirow_insert(sql_text: str, new_rows: List[List[str]]) -> Optional[str]:
    m = re.search(r"(insert\s+into\s+[\w\.\[\]]+\s*\([^\)]+\)\s*values\s*)(.+)$", sql_text, re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    prefix, _ = m.groups()
    row_strs = []
    for row in new_rows:
        encoded = []
        for v in row:
            if re.match(r"^-?\d+(\.\d+)?$", v or ""):
                encoded.append(v)
            else:
                encoded.append("'" + v.replace("'", "''") + "'")
        row_strs.append("(" + ", ".join(encoded) + ")")
    return prefix + ", ".join(row_strs)


# --- MVP4: Lightweight detectors for MERGE, BULK INSERT and SELECT ---

def detect_bulk_insert(sql_text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Detects simple BULK INSERT statements.
    Returns (target_table, source_path) when matched; otherwise (None, None).
    Examples supported:
      BULK INSERT dbo.Customers FROM 'C:\\data\\cust.csv' WITH (...)
    """
    sql = sql_text.strip()
    m = re.search(
        r"bulk\s+insert\s+([\w\.\[\]]+)\s+from\s+'([^']+)'",
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    if not m:
        return None, None
    table = m.group(1)
    path = m.group(2)
    return table, path


def detect_merge(sql_text: str) -> Tuple[Optional[str], List[str], List[str]]:
    """
    Detect a basic MERGE and extract target table, update column names and
    insert column names when present.

    Limitations: regex-based, aims for common layouts in T-SQL.
    Returns (target_table, update_cols, insert_cols).
    """
    sql = sql_text.strip()
    # MERGE INTO <target> AS t USING ...
    m = re.search(r"merge\s+into\s+([\w\.\[\]]+)", sql, re.IGNORECASE)
    if not m:
        return None, [], []
    target = m.group(1)
    # Normalize [dbo].[T] -> dbo.T
    target = target.replace("].[", ".").replace("[", "").replace("]", "")

    update_cols: List[str] = []
    insert_cols: List[str] = []

    # WHEN MATCHED THEN UPDATE SET a = b, c = d
    mu = re.search(
        r"when\s+matched\s+then\s+update\s+set\s+(.+?)\s+(when|output|;|$)",
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    if mu:
        assigns = mu.group(1)
        for part in _split_csv_respecting_quotes(assigns):
            left = part.split("=", 1)[0].strip()
            # Strip aliases and brackets: t.[Col] -> Col
            left = re.sub(r"^[\w]+\.", "", left)
            left = left.strip(" []")
            if left:
                update_cols.append(left)

    # WHEN NOT MATCHED THEN INSERT (A,B,...) VALUES (...)
    mi = re.search(
        r"when\s+not\s+matched\s+then\s+insert\s*\(([^\)]+)\)",
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    if mi:
        cols = [c.strip(" []") for c in mi.group(1).split(",")]
        insert_cols.extend([c for c in cols if c])

    return target, update_cols, insert_cols


def extract_select_info(sql_text: str) -> Tuple[List[str], List[str], bool]:
    """
    Very simple SELECT parser:
    - Returns (tables, columns, select_star)
    - Only handles single FROM target reliably; JOINs are folded by capturing
      the first identifier after FROM.
    - Column list is split on commas if not '*'; functions/aliases are kept raw.
    """
    sql = sql_text.strip()
    # Detect select list
    msel = re.search(r"select\s+(.*?)\s+from\s", sql, re.IGNORECASE | re.DOTALL)
    cols_raw = msel.group(1).strip() if msel else "*"
    select_star = cols_raw == "*"
    cols: List[str] = [] if select_star else [c.strip() for c in _split_csv_respecting_quotes(cols_raw)]

    # Detect main table after FROM
    mfrom = re.search(r"from\s+([\w\.\[\]]+)", sql, re.IGNORECASE)
    tables: List[str] = []
    if mfrom:
        tbl = mfrom.group(1)
        # Normalize [dbo].[T] -> dbo.T for consistency
        tbl = tbl.replace("].[", ".").replace("[", "").replace("]", "")
        tables.append(tbl)

    return tables, cols, select_star
