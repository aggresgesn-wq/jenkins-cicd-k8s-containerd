# coding: utf-8
"""Gunicorn 生产环境配置。

启动方式（镜像工作目录为 /app）：

    gunicorn --config gunicorn.conf.py wsgi:app

可通过环境变量调整的参数：

* ``GUNICORN_WORKERS``          worker 数量，默认 4；
* ``GUNICORN_TIMEOUT``          请求超时（秒），默认 120；
* ``GUNICORN_GRACEFUL_TIMEOUT`` 优雅退出等待（秒），默认 30；
* ``LOG_LEVEL``                 日志级别，默认 info；
* ``FORWARDED_ALLOW_IPS``       信任的代理地址，默认 ``*``（仅部署在 ingress-nginx 之后时使用）。
"""

import os


def _env_int(name, default, minimum, maximum):
    """读取整型环境变量；非法值回退默认值，并做上下限保护。"""
    raw = os.environ.get(name)
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return default
    return max(minimum, min(value, maximum))


def _log_level():
    level = os.environ.get("LOG_LEVEL", "info").strip().lower()
    level = {"warn": "warning", "fatal": "critical"}.get(level, level)
    if level in {"debug", "info", "warning", "error", "critical"}:
        return level
    return "info"


# 监听地址：容器固定暴露 5000，Service 与探针均指向该端口。
bind = "0.0.0.0:5000"

# worker 数量：默认 4；设置上限避免环境变量误配导致 fork 风暴。
workers = _env_int("GUNICORN_WORKERS", 4, minimum=1, maximum=32)

# 当前应用是阻塞式 Flask，sync worker 行为最可预测，配合多副本横向扩展。
worker_class = "sync"

# 请求超时：Excel 导出、图片上传等场景可能较慢，默认放宽到 120 秒。
timeout = _env_int("GUNICORN_TIMEOUT", 120, minimum=30, maximum=600)

# 收到 SIGTERM 后等待存量请求完成的时间，必须小于 Pod 的 terminationGracePeriodSeconds。
graceful_timeout = _env_int("GUNICORN_GRACEFUL_TIMEOUT", 30, minimum=5, maximum=120)

# keep-alive 连接复用时间；sync worker 不启用长连接，保留该值便于后续切换到 gthread/异步 worker。
keepalive = 5

# 在 master 进程完成应用导入后再 fork：
# 应用初始化只创建对象、不建立数据库连接，preload 可显著降低多 worker 的内存占用；
# 如果以后在 import 阶段建立数据库连接或启动后台线程，应改为 False（或用 post_fork 重建资源）。
preload_app = True

# worker 心跳临时文件放到 /tmp：
# Kubernetes 中 /tmp 挂载 emptyDir，容器根文件系统保持 readOnlyRootFilesystem。
if os.path.isdir("/tmp"):
    worker_tmp_dir = "/tmp"

# 定期回收 worker，规避第三方库可能存在的内存泄漏；
# jitter 用于错开各 worker 的重启时间，避免同时下线。
max_requests = 1000
max_requests_jitter = 100

# 访问日志与错误日志统一输出到 stdout/stderr，由容器运行时采集。
accesslog = "-"
errorlog = "-"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(L)s xff="%({x-forwarded-for}i)s"'
loglevel = _log_level()

# 部署在 ingress-nginx 之后：信任其传入的 X-Forwarded-For / X-Forwarded-Proto，
# 保证 Flask 能识别原始客户端 IP 与 https scheme。
# 如果 Pod 可能被集群内其他来源直连，请用 FORWARDED_ALLOW_IPS 收紧为 ingress 的 Pod/节点网段。
forwarded_allow_ips = os.environ.get("FORWARDED_ALLOW_IPS", "*")

# 进程名，便于在容器内 ps/top 中识别。
proc_name = "webapp"
