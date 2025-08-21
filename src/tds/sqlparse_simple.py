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
            parts.append(f"{col} = '{v.replace("'","''")}'")
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
