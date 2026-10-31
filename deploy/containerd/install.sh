#!/usr/bin/env bash
# 在 Linux 节点上安装并配置 containerd（Debian/Ubuntu 或 RHEL 系）。
#
#   sudo ./deploy/containerd/install.sh
#
# 幂等：重复执行只会重写配置并重启服务；旧配置会备份到 /etc/containerd/config.toml.bak.<时间戳>
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_SRC="${SCRIPT_DIR}/config.toml"
CONFIG_DST="/etc/containerd/config.toml"

[ "$(id -u)" -eq 0 ] || { echo "请用 root 或 sudo 运行" >&2; exit 1; }

echo "==> 检测发行版"
if command -v apt-get >/dev/null 2>&1; then
  PKG_MGR=apt
elif command -v dnf >/dev/null 2>&1; then
  PKG_MGR=dnf
elif command -v yum >/dev/null 2>&1; then
  PKG_MGR=yum
else
  echo "未识别的包管理器（需要 apt/dnf/yum）" >&2
  exit 1
fi

echo "==> 安装依赖并添加 Docker 官方仓库（containerd.io）"
if [ "${PKG_MGR}" = "apt" ]; then
  apt-get update -y
  apt-get install -y ca-certificates curl gnupg
  install -m 0755 -d /etc/apt/keyrings
  if [ ! -f /etc/apt/keyrings/docker.asc ]; then
    curl -fsSL https://download.docker.com/linux/$(. /etc/os-release && echo "${ID}")/gpg \
      -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc
  fi
  . /etc/os-release
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/${ID} ${VERSION_CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y containerd.io
else
  if [ ! -f /etc/yum.repos.d/docker-ce.repo ]; then
    curl -fsSL https://download.docker.com/linux/centos/docker-ce.repo \
      -o /etc/yum.repos.d/docker-ce.repo
  fi
  ${PKG_MGR} install -y containerd.io
fi

echo "==> 写入配置（SystemdCgroup=true，pause 镜像走国内同步站）"
mkdir -p /etc/containerd
if [ -f "${CONFIG_DST}" ]; then
  cp -a "${CONFIG_DST}" "${CONFIG_DST}.bak.$(date +%Y%m%d%H%M%S)"
fi
install -m 644 "${CONFIG_SRC}" "${CONFIG_DST}"
mkdir -p /etc/containerd/certs.d

echo "==> 启用并重启 containerd"
systemctl daemon-reload
systemctl enable containerd
systemctl restart containerd
systemctl is-active --quiet containerd

echo "==> 提示：kubelet 必须使用 cgroupDriver=systemd"
if [ -f /var/lib/kubelet/config.yaml ]; then
  grep -q 'cgroupDriver: systemd' /var/lib/kubelet/config.yaml \
    || echo "WARN: /var/lib/kubelet/config.yaml 未设置 cgroupDriver: systemd（参考 deploy/containerd/kubelet-cgroup.conf）"
fi

echo "==> 完成。执行 sudo ./deploy/containerd/verify.sh 做只读校验"
