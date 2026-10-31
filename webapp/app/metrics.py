# coding: utf-8
"""Prometheus 指标。

未安装 prometheus_client 时自动降级为空实现，保证本地开发与测试不依赖该库。
"""

from __future__ import annotations

import time

from flask import request

try:  # pragma: no cover - 依赖缺失时走降级分支
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

    REQUESTS = Counter(
        "webapp_http_requests_total",
        "HTTP 请求总数",
        ["method", "endpoint", "status"],
    )
    LATENCY = Histogram(
        "webapp_http_request_duration_seconds",
        "HTTP 请求耗时（秒）",
        ["method", "endpoint"],
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    )
    LOGIN_FAILURES = Counter("webapp_login_failures_total", "登录失败次数")
    LOGIN_LOCKED = Counter("webapp_login_locked_total", "因失败次数过多被锁定的登录次数")
    ENABLED = True
except Exception:  # noqa: BLE001
    REQUESTS = LATENCY = LOGIN_FAILURES = LOGIN_LOCKED = None
    CONTENT_TYPE_LATEST = "text/plain"
    generate_latest = None
    ENABLED = False


def _endpoint_label() -> str:
    """使用路由规则而不是原始 URL，避免标签基数爆炸。"""
    rule = request.url_rule
    return rule.rule if rule is not None else "unmatched"


def init_app(app) -> None:
    if not ENABLED:
        app.logger.warning("prometheus_client 未安装，/metrics 已禁用")
        return

    @app.route("/metrics")
    def metrics():
        # 指标端点只暴露在集群内，由 NetworkPolicy 限制访问来源
        return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}

    @app.before_request
    def _start_timer():
        request._prom_start = time.perf_counter()

    @app.after_request
    def _record(response):
        start = getattr(request, "_prom_start", None)
        endpoint = _endpoint_label()
        REQUEST_OR_NONE = REQUESTS
        if REQUEST_OR_NONE is not None:
            REQUEST_OR_NONE.labels(request.method, endpoint, str(response.status_code)).inc()
        if start is not None and LATENCY is not None:
            LATENCY.labels(request.method, endpoint).observe(time.perf_counter() - start)
        return response


def record_login_failure(locked: bool) -> None:
    if not ENABLED:
        return
    LOGIN_FAILURES.inc()
    if locked:
        LOGIN_LOCKED.inc()
