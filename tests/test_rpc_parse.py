from src.tds.rpc_parse import decode_utf16le_best_effort, extract_proc_and_params


def test_decode_utf16le_best_effort():
    s = "dbo.proc @p='x'"
    data = s.encode("utf-16le")
    assert decode_utf16le_best_effort(data).startswith("dbo.proc")


def test_extract_proc_and_params_simple():
    s = "dbo.proc @name='John', @id='42'"
    payload = s.encode("utf-16le")
    proc, params = extract_proc_and_params(payload)
    assert proc.endswith("proc")
    names = dict(params)
    assert names.get("name") == "John" and names.get("id") == "42"

