# 监控与告警

本目录提供 webapp 的可观测性配置，应用侧已在 `/metrics` 暴露 Prometheus 指标。

## 指标

| 指标 | 类型 | 说明 |
| --- | --- | --- |
| `webapp_http_requests_total{method,endpoint,status}` | Counter | 请求总数，按路由规则统计（不含原始 URL，避免基数爆炸） |
| `webapp_http_request_duration_seconds{method,endpoint}` | Histogram | 请求耗时，用于 P95/P99 |
| `webapp_login_failures_total` | Counter | 登录失败次数 |
| `webapp_login_locked_total` | Counter | 因失败次数过多触发锁定的次数 |

> `/metrics` 不做应用层鉴权，依赖 NetworkPolicy 限制为集群内 Prometheus 抓取；如需暴露到集群外，请加 Ingress 白名单或反代鉴权。

## 接入方式

### 方式 A：Prometheus Operator（推荐）

```bash
kubectl apply -f deploy/monitoring/servicemonitor.yaml
kubectl apply -f deploy/monitoring/prometheusrule.yaml
```

`ServiceMonitor` 依赖应用 Service 的端口名 `http`（见 `deploy/k8s/service.yaml`）；`PrometheusRule` 的 `release` 标签需与 Prometheus 的 selector 一致。

### 方式 B：静态抓取

把 `prometheus-config.yaml` 中的 job 合并到 `prometheus.yml`：

```yaml
scrape_configs:
  - job_name: webapp
    metrics_path: /metrics
    static_configs:
      - targets: ["webapp.webapp.svc.cluster.local:5000"]
```

## 告警规则

`prometheusrule.yaml` 包含：

- `WebappHighErrorRate`：5xx 占比 > 5%，持续 10 分钟
- `WebappHighLatency`：P95 > 1s，持续 10 分钟
- `WebappLoginFailureSpike`：5 分钟失败 > 50 次
- `WebappLoginLockout`：10 分钟内多次账号锁定
- `WebappPodRestarting`：15 分钟重启 > 2 次
- `WebappHPAMaxedOut`：HPA 持续处于最大副本数

## 仪表盘

`grafana-dashboard.json` 可直接导入 Grafana（需先有 Prometheus 数据源），包含请求速率、P95 延迟、登录失败/锁定、副本数与重启四个面板。

## 日志

应用与 gunicorn 均输出到 stdout，由容器运行时采集：

- 设置 `LOG_FORMAT=json` 可输出单行 JSON，便于 Loki/ELK 解析。
- 审计日志写入 `SYOPERATIONLOG`，密码、Token、Cookie 等字段在落库前已脱敏（`app/operationlog.py`）。
- 建议在 Ingress/网关层再采集访问日志，并与 `trace_id`（后续可引入 OpenTelemetry）关联。
