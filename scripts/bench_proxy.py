#!/usr/bin/env python3
"""Tiny local benchmark for parser/encoder hot paths.
Measures simple SQL parse and RPC payload build throughput.
"""
import time
from src.tds.sqlparse_simple import extract_values
from src.tds.rpc_build import build_rpc_payload


def bench_parse(n=10000):
    sql = "INSERT INTO dbo.T (A,B) VALUES ('x', 1)"
    s = time.time()
    for _ in range(n):
        extract_values(sql)
    return time.time() - s


def bench_rpc(n=5000):
    params = [("@amount", "123.45", "decimal"), ("id", "550e8400-e29b-41d4-a716-446655440000", "uniqueidentifier")]
    s = time.time()
    for _ in range(n):
        build_rpc_payload("dbo.proc", params)
    return time.time() - s


def main():
    t1 = bench_parse()
    t2 = bench_rpc()
    print(f"parse: {t1:.3f}s for 10k; rpc: {t2:.3f}s for 5k")


if __name__ == "__main__":
    main()

