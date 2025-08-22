import asyncio
import logging
import os
import time
import contextlib
from src.policy.loader import load_rules
from src.policy.engine import PolicyEngine, Event
from src.metrics import store as metrics_store
from typing import Optional
try:
    from src.metrics.prom_registry import bytes_hist, latency_hist
except Exception:
    bytes_hist = None
    latency_hist = None

logger = logging.getLogger("tds_proxy")
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(name)s: %(message)s")


async def _pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, direction: str, conn_id: str, counter: dict):
    try:
        engine = None
        enforcement = os.getenv("ENFORCEMENT_MODE", "log")  # log|enforce
        sniff = os.getenv("ENABLE_SQL_TEXT_SNIFF", "false").lower() == "true"
        tds_parser_on = os.getenv("ENABLE_TDS_PARSER", "false").lower() == "true"
        if direction == "c2s" and (sniff or tds_parser_on):
            rules = load_rules()
            engine = PolicyEngine(rules, environment=os.getenv("ENVIRONMENT"))
        time_budget_ms = int(os.getenv("TIME_BUDGET_MS", "25"))
        max_rewrite_bytes = int(os.getenv("MAX_REWRITE_BYTES", "131072"))
        while not reader.at_eof():
            start_ts = time.time()
            data = await reader.read(65536)
            if not data:
                break
            try:
                if bytes_hist:
                    bytes_hist.observe(len(data))
            except Exception:
                pass
            tds_parser_on = os.getenv("ENABLE_TDS_PARSER", "false").lower() == "true"
            if tds_parser_on and direction == "c2s":
                try:
                    from src.tds.parser import type_name, EOM, extract_sqlbatch_text, parse_header
                    from src.tds.sqlparse_simple import extract_table_and_columns, extract_values, reconstruct_insert, reconstruct_update
                    from src.tds.rpc_parse import extract_proc_and_params
                    if "_sql_chunks" not in counter:
                        counter["_sql_chunks"] = []
                    # Reassembly-aware: maintain a c2s buffer for full packet parsing
                    buf = counter.get("_c2s_buf", b"") + data
                    out_passthrough: bytes = b""
                    i = 0
                    while True:
                        if len(buf) - i < 8:
                            break
                        hdr = parse_header(buf[i:i+8])
                        if not hdr:
                            break
                        typ, status, length, spid, pkt, window = hdr
                        if len(buf) - i < length:
                            break
                        payload = buf[i+8:i+length]
                        logger.debug(f"{conn_id} TDS {type_name(typ)} len={length} spid={spid} pkt={pkt}")
                        if typ == 0x01:  # SQL Batch
                            counter["_sql_chunks"].append(payload)
                            if status & EOM:
                                sql_text = extract_sqlbatch_text(counter["_sql_chunks"])
                                counter["_sql_chunks"] = []
                                if sql_text and engine is not None:
                                    from src.metrics import decisions as dec_store
                                    # Whole-statement decision (pattern/table rules)
                                    decision = engine.decide(Event(database=None, user=None, sql_text=sql_text, table=None, column=None, value=None))
                                    dec_store.append({"spid": spid, "action": decision.action, "reason": decision.reason, "confidence": decision.confidence, "rule_id": decision.rule_id, "sample": (sql_text[:200] or "")})
                                    if decision.rule_id:
                                        metrics_store.inc_rule_action(decision.rule_id, decision.action)
                                    if decision.action == "block" and enforcement == "enforce":
                                        # Check per-rule threshold gating
                                        r = engine.get_rule(decision.rule_id)
                                        if r and getattr(r, "min_hits_to_enforce", 0) > 0:
                                            cnts = metrics_store.get_rule_counters(decision.rule_id) or {}
                                            hits = int(cnts.get("block", 0) + cnts.get("autocorrect", 0) + cnts.get("rpc_autocorrect_inplace", 0))
                                            if hits < r.min_hits_to_enforce:
                                                metrics_store.inc("gated_by_threshold")
                                            else:
                                                metrics_store.inc("blocks")
                                                sql_text = None
                                        else:
                                            metrics_store.inc("blocks")
                                            sql_text = None
                                    else:
                                        # Column-level autocorrect: simple INSERT/UPDATE mapping
                                        table, cols = extract_table_and_columns(sql_text)
                                        from src.tds.sqlparse_simple import extract_multirow_values, reconstruct_multirow_insert
                                        multi_rows = extract_multirow_values(sql_text)
                                        if multi_rows and table and cols and all(len(r)==len(cols) for r in multi_rows):
                                            changed_any = False
                                            new_rows = []
                                            from agents.normalizers import suggest_normalizations
                                            for row in multi_rows:
                                                row_new = list(row)
                                                row_changed = False
                                                for idx, col in enumerate(cols):
                                                    col_selector = f"{table}.{col}"
                                                    d = engine.decide(Event(database=None, user=None, sql_text=sql_text, table=table, column=col_selector, value=row[idx]))
                                                    if d.action == "autocorrect":
                                                        sug = suggest_normalizations(row[idx])
                                                        if sug and sug.get("normalized") and sug["normalized"] != row[idx]:
                                                            before = row[idx]
                                                            after = sug["normalized"]
                                                            row_new[idx] = after
                                                            row_changed = True
                                                            metrics_store.inc("autocorrect_suggested")
                                                            dec_store.append({"spid": spid, "action": "autocorrect", "rule_id": d.rule_id, "reason": d.reason, "before": before, "after": after, "column": col_selector})
                                                            if d.rule_id:
                                                                metrics_store.inc_rule_action(d.rule_id, "autocorrect")
                                                changed_any = changed_any or row_changed
                                                new_rows.append(row_new)
                                            if changed_any and enforcement == "enforce":
                                                new_sql = reconstruct_multirow_insert(sql_text, new_rows)
                                                if new_sql:
                                                    sql_text = new_sql
                                        else:
                                            vals = extract_values(sql_text)
                                            if table and cols and vals and len(cols) == len(vals):
                                                changed = False
                                                new_vals = list(vals)
                                                for idx, col in enumerate(cols):
                                                    col_selector = f"{table}.{col}"
                                                    d = engine.decide(Event(database=None, user=None, sql_text=sql_text, table=table, column=col_selector, value=vals[idx]))
                                                    if d.action == "autocorrect":
                                                        # try normalizers
                                                        from agents.normalizers import suggest_normalizations
                                                        sug = suggest_normalizations(vals[idx])
                                                        if sug and sug.get("normalized") and sug["normalized"] != vals[idx]:
                                                            before = vals[idx]
                                                            after = sug["normalized"]
                                                            new_vals[idx] = after
                                                            changed = True
                                                            metrics_store.inc("autocorrect_suggested")
                                                            dec_store.append({"spid": spid, "action": "autocorrect", "rule_id": d.rule_id, "reason": d.reason, "before": before, "after": after, "column": col_selector})
                                                            if d.rule_id:
                                                                metrics_store.inc_rule_action(d.rule_id, "autocorrect")
                                                if changed and enforcement == "enforce":
                                                    # Reconstruct simple INSERT/UPDATE
                                                    new_sql = reconstruct_insert(sql_text, new_vals) or reconstruct_update(sql_text, cols, new_vals)
                                                    if new_sql:
                                                        sql_text = new_sql
                                    # Forward either modified sql_text, original, or nothing if blocked
                                    if sql_text is not None:
                                        payload_new = sql_text.encode("utf-16le")
                                        length_new = 8 + len(payload_new)
                                        header = bytes([0x01, EOM, (length_new >> 8) & 0xFF, length_new & 0xFF, (spid >> 8) & 0xFF, spid & 0xFF, 1, 0])
                                        out_passthrough += header + payload_new
                            # else: wait for EOM (do not forward partial batch)
                        elif typ == 0x03:  # RPC
                            # Reassemble and decide at EOM only
                            counter.setdefault("_rpc_chunks", []).append(payload)
                            if status & EOM:
                                metrics_store.inc("rpc_seen")
                                rpc_payload = b"".join(counter.get("_rpc_chunks", []))
                                counter["_rpc_chunks"] = []
                                proc, params = extract_proc_and_params(rpc_payload)
                                block_rpc = False
                                if engine is not None and params:
                                    from src.metrics import decisions as dec_store
                                    for name, val in params:
                                        ev = Event(database=None, user=None, sql_text=None, table=None, column=name, value=val)
                                        d = engine.decide(ev)
                                        dec_store.append({"spid": spid, "action": d.action, "rule_id": d.rule_id, "reason": d.reason, "param": name, "value": (val[:80] if isinstance(val,str) else val)})
                                        if d.action == "block":
                                            block_rpc = True
                                inplace = os.getenv("RPC_AUTOCORRECT_INPLACE", "true").lower() == "true"
                                if block_rpc and enforcement == "enforce":
                                    metrics_store.inc("rpc_blocked")
                                    # Drop this RPC call (do not forward)
                                elif inplace and enforcement == "enforce" and params:
                                    # Attempt in-place rewrite of UTF-16LE strings with same or shorter length (pad with spaces)
                                    payload_new = rpc_payload
                                    from agents.normalizers import suggest_normalizations
                                    changed = False
                                    for name, val in params:
                                        ev = Event(database=None, user=None, sql_text=None, table=None, column=name, value=val)
                                        d = engine.decide(ev)
                                        if d.action == "autocorrect":
                                            sug = suggest_normalizations(val)
                                            if not sug or not sug.get("normalized"):
                                                continue
                                            new_val = str(sug["normalized"]) or ""
                                            old_b = (val or "").encode("utf-16le", errors="ignore")
                                            new_b = new_val.encode("utf-16le", errors="ignore")
                                            if len(new_b) > len(old_b):
                                                if os.getenv("RPC_TRUNCATE_ON_AUTOCORRECT", "false").lower() == "true":
                                                    new_b = new_b[: len(old_b)]
                                                else:
                                                    continue
                                            if len(new_b) < len(old_b):
                                                pad = (len(old_b) - len(new_b)) // 2
                                                new_b = new_b + (" " * pad).encode("utf-16le")
                                            if old_b in payload_new:
                                                payload_new = payload_new.replace(old_b, new_b, 1)
                                                changed = True
                                                from src.metrics import decisions as dec_store
                                                dec_store.append({"spid": spid, "action": "rpc_autocorrect_inplace", "rule_id": d.rule_id, "reason": d.reason, "param": name, "before": val, "after": new_val})
                                                metrics_store.inc("rpc_autocorrect_inplace")
                                                if d.rule_id:
                                                    metrics_store.inc_rule_action(d.rule_id, "rpc_autocorrect_inplace")
                                    if changed:
                                        if os.getenv("RPC_REPACK_BUILDER", "false").lower() == "true":
                                            # Try to build a fresh RPC payload (best-effort) using builder
                                            try:
                                                from src.tds.rpc_build import build_rpc_payload
                                                from src.tds.rpc_types import load_param_types
                                                proc = proc or "sp_executesql"
                                                # Load explicit type mapping if available
                                                type_map = load_param_types()
                                                proc_map = type_map.get(proc.lower(), {})
                                                param_types = []
                                                for n, v in params:
                                                    t = proc_map.get(n.lstrip("@").lower())
                                                    if not t:
                                                        k = (suggest_normalizations(v) or {}).get("kind")
                                                        t = "int" if k == "int" else "nvarchar"
                                                    param_types.append((n, t))
                                                mapped = []
                                                for (n, v), (_, t) in zip(params, param_types):
                                                    typ = t.lower() if t.lower() in ("nvarchar", "int", "bit") else "nvarchar"
                                                    mapped.append((n, v, typ))
                                                payload_built = build_rpc_payload(proc, mapped)
                                                payload_new = payload_built
                                            except Exception:
                                                pass
                                        length_new = 8 + len(payload_new)
                                        header = bytes([0x03, EOM, (length_new >> 8) & 0xFF, length_new & 0xFF, (spid >> 8) & 0xFF, spid & 0xFF, 1, 0])
                                        out_passthrough += header + payload_new
                                    else:
                                        out_passthrough += buf[i:i+length]
                                else:
                                    out_passthrough += buf[i:i+length]
                        else:
                            out_passthrough += buf[i:i+length]
                        i += length
                    # Persist leftover bytes for next iteration
                    counter["_c2s_buf"] = buf[i:]
                    if out_passthrough:
                        if len(out_passthrough) > max_rewrite_bytes:
                            metrics_store.inc("rewrite_skipped_size")
                            out_passthrough = b""  # skip write
                        writer.write(out_passthrough)
                        await writer.drain()
                        counter[direction] = counter.get(direction, 0) + len(out_passthrough)
                    continue  # already handled writing for this iteration
                except Exception:
                    pass
            # Heuristic SQL sniffing: use simple ascii window
            if engine is not None and os.getenv("ENABLE_TDS_PARSER", "false").lower() != "true":
                try:
                    sample = data.decode("latin-1", errors="ignore")
                    # crude filter: look for keywords to avoid binary payloads
                    if any(k in sample.lower() for k in ("insert ", "update ", "delete ", "select ")):
                        decision = engine.decide(Event(database=None, user=None, sql_text=sample, table=None, column=None, value=None))
                        if decision.action == "block":
                            metrics_store.inc("blocks")
                            logger.warning(f"{conn_id} blocked by rule: {decision.reason}")
                            if enforcement == "enforce":
                                # close without forwarding
                                break
                        elif decision.action == "autocorrect":
                            metrics_store.inc("autocorrect_suggested")
                        else:
                            metrics_store.inc("allowed")
                except Exception:
                    pass
            # Safety: time budget to avoid CPU spikes
            if (time.time() - start_ts) * 1000.0 > time_budget_ms:
                metrics_store.inc("rewrite_skipped_budget")
            writer.write(data)
            await writer.drain()
            counter[direction] = counter.get(direction, 0) + len(data)
            try:
                if latency_hist:
                    latency_hist.observe((time.time() - start_ts) * 1000.0)
            except Exception:
                pass
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.debug(f"{conn_id} pipe error ({direction}): {e}")
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def handle_client(local_reader: asyncio.StreamReader, local_writer: asyncio.StreamWriter, upstream_host: str, upstream_port: int, conn_id: str):
    peer = local_writer.get_extra_info("peername")
    logger.info(f"{conn_id} connected from {peer}")
    counter: dict = {}
    try:
        remote_reader, remote_writer = await asyncio.open_connection(upstream_host, upstream_port)
    except Exception as e:
        logger.error(f"{conn_id} failed to connect upstream {upstream_host}:{upstream_port}: {e}")
        local_writer.close()
        await local_writer.wait_closed()
        return

    c2s = asyncio.create_task(_pipe(local_reader, remote_writer, "c2s", conn_id, counter))
    s2c = asyncio.create_task(_pipe(remote_reader, local_writer, "s2c", conn_id, counter))

    await asyncio.wait([c2s, s2c], return_when=asyncio.FIRST_COMPLETED)
    for t in (c2s, s2c):
        t.cancel()
        with contextlib.suppress(Exception):
            await t

    logger.info(f"{conn_id} closed bytes c2s={counter.get('c2s',0)} s2c={counter.get('s2c',0)}")


async def run_proxy(listen_host: str, listen_port: int, upstream_host: str, upstream_port: int, stop_event: Optional[asyncio.Event] = None):
    server = await asyncio.start_server(
        lambda r, w: handle_client(r, w, upstream_host, upstream_port, f"conn-{id(w)}"), listen_host, listen_port
    )
    sockets = ", ".join(str(s.getsockname()) for s in server.sockets or [])
    logger.info(f"Proxy listening on {sockets} -> {upstream_host}:{upstream_port}")
    async with server:
        if stop_event is None:
            await server.serve_forever()
        else:
            await stop_event.wait()
    logger.info("Proxy shutdown")
