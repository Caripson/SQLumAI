import re
from typing import List, Tuple, Optional


def decode_utf16le_best_effort(data: bytes) -> str:
    try:
        return data.decode("utf-16le", errors="ignore")
    except Exception:
        return ""


def extract_proc_and_params(payload: bytes) -> Tuple[Optional[str], List[Tuple[str, str]]]:
    """
    Best-effort extraction of RPC procedure name and named NVARCHAR-like parameters.
    Not a full TDS RPC parser. Heuristic: decode as UTF-16LE and look for @param and quoted values.
    """
    s = decode_utf16le_best_effort(payload)
    if not s:
        return None, []
    # Procedure name often appears as a readable string at the start
    proc = None
    m = re.search(r"([\w\.\[\]]{3,})\s*@", s)
    if m:
        proc = m.group(1)

    params: List[Tuple[str, str]] = []
    # Find all @param names
    for pm in re.finditer(r"@([A-Za-z0-9_]{1,64})", s):
        name = pm.group(1)
        # Search forward within a window for a quoted string as value
        window = s[pm.end(): pm.end() + 200]
        vm = re.search(r"'([^']{0,120})'", window)
        if vm:
            params.append((name, vm.group(1)))
    return proc, params

