from prometheus_client import Counter, Histogram

metric_counter = Counter(
    "sqlumai_metric_total",
    "SQLumAI counters (key or rule/action)",
    labelnames=("key", "rule", "action"),
)

bytes_hist = Histogram(
    "sqlumai_bytes",
    "Bytes forwarded per write",
    buckets=(64, 256, 1024, 4096, 16384, 65536, 262144, 1048576),
)

latency_hist = Histogram(
    "sqlumai_latency_ms",
    "Processing latency per iteration (ms)",
    buckets=(0.5, 1, 2, 5, 10, 20, 50, 100, 250),
)

def inc_counter(key: str, rule: str | None = None, action: str | None = None, by: int = 1):
    metric_counter.labels(key=key or "", rule=rule or "", action=action or "").inc(by)

