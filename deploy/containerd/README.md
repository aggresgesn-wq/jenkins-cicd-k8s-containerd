# containerd 安装、配置与验证（Linux）

Kubernetes 的容器运行时由 containerd 提供。本目录把“集群前置条件”变成可复现的脚本与配置，而不是一句“请自行安装”。

> 适用：kubeadm 自建集群、或需要核对节点运行时的场景。托管 Kubernetes（ACK/TKE/EKS 等）由云厂商维护 containerd，跳过安装，但仍可用 `verify.sh` 做检查。默认不拉取镜像；显式传入 `--pull` 才会执行网络拉取验证。

## 1. 目录内容

| 文件 | 说明 |
| --- | --- |
| `install.sh` | 在 Ubuntu/Debian（apt）或 Rocky/Alma/openEuler（dnf/yum）上安装 containerd.io、启用服务、写入配置 |
| `config.toml` | containerd 2.x 配置模板：CRI 插件、`SystemdCgroup=true`、pause 镜像走国内同步站 |
| `verify.sh` | 默认只读校验服务、CRI socket、`crictl info`、cgroup 驱动；`--pull` 额外验证 pause 镜像拉取 |
| `kubelet-cgroup.conf` | kubelet 侧 `cgroupDriver: systemd` 片段示例 |

## 2. 安装

```bash
# 以 root 执行
sudo ./deploy/containerd/install.sh

# 已加入集群且确需变更 cgroup 配置时，在维护窗口重启并检查 kubelet
sudo systemctl restart kubelet
sudo systemctl is-active kubelet

# 默认只读校验；需要验证节点外网/镜像站连通性时加 --pull
sudo ./deploy/containerd/verify.sh
sudo ./deploy/containerd/verify.sh --pull
```

`install.sh` 会：

1. 配置 Docker 官方 apt/yum 仓库并安装 `containerd.io`；
2. 备份已有 `/etc/containerd/config.toml`，写入本目录模板；
3. `systemctl enable --now containerd`；
4. 输出 kubelet 需要的 `cgroupDriver` 提示。

## 3. 关键配置

`config.toml` 中必须关注三项：

```toml
[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc.options]
  SystemdCgroup = true          # 与 kubelet 的 cgroupDriver=systemd 保持一致

[plugins."io.containerd.grpc.v1.cri"]
  sandbox_image = "swr.cn-north-4.myhuaweicloud.com/ddn-k8s/registry.k8s.io/pause:3.9"
```

- **cgroup 驱动必须一致**：containerd 用 systemd，kubelet 却用 cgroupfs，会导致 Pod 起不来或资源统计异常。
- **pause 镜像**要走内网可达的地址，否则节点无法创建 Pod 沙箱。
- 私有仓库认证放在 `/etc/containerd/certs.d/<registry>/hosts.toml`，不要把凭据写进主配置。

kubelet 侧（`/var/lib/kubelet/config.yaml` 或 kubeadm 配置）：

```yaml
cgroupDriver: systemd
```

kubeadm 初始化时也可显式指定：

```yaml
kind: KubeletConfiguration
cgroupDriver: systemd
```

## 4. 验证清单

`verify.sh` 会依次检查：

| 检查 | 期望 |
| --- | --- |
| `systemctl is-active containerd` | `active` |
| `/run/containerd/containerd.sock` | 存在 |
| `crictl info` | `RuntimeReady: true`、`NetworkReady: true` |
| `containerd config dump` | `SystemdCgroup = true` |
| pause 镜像拉取（仅 `--pull`） | 成功 |

若节点没有 `crictl`，脚本会提示安装方式（与 Kubernetes 版本对应）：

```bash
VERSION="v1.29.0" # 按集群 Kubernetes minor 版本选择并固定
ARCH="amd64"
BASE="crictl-${VERSION}-linux-${ARCH}.tar.gz"
curl -fLO "https://github.com/kubernetes-sigs/cri-tools/releases/download/${VERSION}/${BASE}"
curl -fLO "https://github.com/kubernetes-sigs/cri-tools/releases/download/${VERSION}/${BASE}.sha256"
sha256sum --check "${BASE}.sha256"
sudo tar zxvf "${BASE}" -C /usr/local/bin
sudo crictl config --set runtime-endpoint=unix:///run/containerd/containerd.sock
```

## 5. 与流水线的关系

- 构建阶段用 kaniko（无特权、不挂载 containerd.sock），只需要节点能拉取构建镜像；
- 部署后的 Pod 由节点上的 containerd 拉起，镜像地址为 `ACR/image@sha256:...`；
- 节点需要能访问 ACR 与 `swr.cn-north-4.myhuaweicloud.com`（镜像同步站）。

## 6. 常见问题

| 现象 | 排查 |
| --- | --- |
| Pod `CreateContainerError` / `RunPodSandbox failed` | pause 镜像拉取失败；检查 `sandbox_image` 与节点网络 |
| `crictl info` 报连接失败 | socket 路径不一致，检查 `--runtime-endpoint` 与 `containerd.sock` |
| kubelet 报 `failed to run Kubelet: misconfiguration: cgroup` | containerd 与 kubelet 的 cgroup driver 不一致 |
| 节点磁盘暴涨 | 检查 `/var/lib/containerd` 的 image/container 回收策略（kubelet `imageGCHighThresholdPercent`） |
| 拉取私有 ACR 镜像 403 | `/etc/containerd/certs.d/<registry>/hosts.toml` 未配置认证，或镜像 tag/digest 不存在 |
