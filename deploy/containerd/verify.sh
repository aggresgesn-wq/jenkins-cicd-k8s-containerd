#!/usr/bin/env bash
# containerd 校验：服务、CRI socket、crictl info、cgroup 驱动；--pull 额外拉取 pause 镜像。
#
#   sudo ./deploy/containerd/verify.sh [--pull]
#
# 默认只读且不会修改节点配置；失败项以非 0 退出码结束，便于放进节点巡检。
set -uo pipefail

PULL_CHECK=0
case "${1:-}" in
  "") ;;
  --pull) PULL_CHECK=1 ;;
  -h|--help) echo "usage: $0 [--pull]"; exit 0 ;;
  *) echo "unknown option: $1" >&2; echo "usage: $0 [--pull]" >&2; exit 2 ;;
esac

FAILED=0
ok()   { echo "  [OK]   $*"; }
warn() { echo "  [WARN] $*"; }
fail() { echo "  [FAIL] $*"; FAILED=1; }

SOCK="/run/containerd/containerd.sock"
PAUSE="swr.cn-north-4.myhuaweicloud.com/ddn-k8s/registry.k8s.io/pause:3.9"

echo "==> 1. 服务状态"
if systemctl is-active --quiet containerd; then ok "containerd 运行中"; else fail "containerd 未运行：journalctl -u containerd -n 100"; fi
if systemctl is-enabled --quiet containerd; then ok "已设置开机自启"; else warn "未设置开机自启：systemctl enable containerd"; fi

echo "==> 2. CRI socket"
if [ -S "${SOCK}" ]; then ok "socket 存在：${SOCK}"; else fail "socket 不存在：${SOCK}"; fi

echo "==> 3. cgroup 驱动"
if containerd config dump 2>/dev/null | grep -q 'SystemdCgroup = true'; then
  ok "containerd SystemdCgroup = true"
else
  fail "containerd 未启用 SystemdCgroup（检查 /etc/containerd/config.toml）"
fi
if [ -f /var/lib/kubelet/config.yaml ]; then
  if grep -q 'cgroupDriver: systemd' /var/lib/kubelet/config.yaml; then
    ok "kubelet cgroupDriver = systemd"
  else
    fail "kubelet 未使用 systemd cgroup 驱动，与 containerd 不一致"
  fi
else
  warn "未找到 /var/lib/kubelet/config.yaml（节点可能未安装 kubelet）"
fi

echo "==> 4. crictl 连通性"
if command -v crictl >/dev/null 2>&1; then
  OUT="$(crictl --runtime-endpoint "unix://${SOCK}" info 2>&1 || true)"
  if printf '%s' "${OUT}" | grep -q '"RuntimeReady": true'; then
    ok "crictl info RuntimeReady=true"
  else
    fail "crictl info 异常：${OUT}"
  fi
else
  warn "未安装 crictl，可用 README 第 4 节命令安装后重试"
fi

echo "==> 5. pause 镜像"
if [ "${PULL_CHECK}" -eq 0 ]; then
  warn "跳过网络拉取（如需验证请使用 --pull）"
elif command -v crictl >/dev/null 2>&1; then
  if crictl --runtime-endpoint "unix://${SOCK}" pull "${PAUSE}" >/dev/null 2>&1; then
    ok "pause 镜像可拉取：${PAUSE}"
  else
    fail "pause 镜像拉取失败，检查节点到 swr.cn-north-4.myhuaweicloud.com 的连通性与 DNS"
  fi
else
  warn "跳过（无 crictl）"
fi

echo "==> 6. 磁盘与镜像回收"
if [ -d /var/lib/containerd ]; then
  echo "  /var/lib/containerd 使用：$(du -sh /var/lib/containerd 2>/dev/null | cut -f1)"
fi

echo
if [ "${FAILED}" -eq 0 ]; then
  echo "全部检查通过"
else
  echo "存在失败项，请按提示修复"
fi
exit "${FAILED}"
