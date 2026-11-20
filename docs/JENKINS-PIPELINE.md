# 已验证流水线（Jenkins #11）

本文件记录 2026-11-16 在实验集群上真实跑通的 Jenkins 流水线。截图与构建号来自 Jenkins 本身，不是示意图。

## 运行环境

| 项 | 值 |
| --- | --- |
| Jenkins | 2.541.1，Kubernetes 命名空间 `jenkins`，NodePort **30080** |
| 构建号 | **#11**（2026-11-16 23:12） |
| 结果 | SUCCESS，总耗时约 4 分 45 秒 |
| 代码来源 | Gitea `http://192.168.80.137:3000/tanchenrui/webapp.git`，分支 `main`，commit `da5526f` |
| Agent | 动态 Pod，节点 `k8s-master`，容器 python / nerdctl / buildkitd / jnlp |
| 镜像 | `crpi-m67ogm8wgcr0rh38.cn-hangzhou.personal.cr.aliyuncs.com/tanchenrui/webapp:da5526f` |

## 阶段耗时

| 阶段 | 耗时 |
| --- | --- |
| Declarative: Checkout SCM | 14s |
| 1. 拉取 Gitea 源码 | 358ms |
| 2. Python 安装依赖（uv） | 48s |
| 3. 构建镜像 + 推送 ACR（nerdctl + buildkitd） | 3m 48s |
| 4. K8s 一键部署 | 88ms（占位 echo，尚未执行 kubectl） |
| Declarative: Post Actions | 122ms |

![Jenkins #11 阶段视图](../images/jenkins/08-stage-view-verified.png)

## 流水线做了什么

1. Jenkins 通过 Pipeline from SCM 从 Gitea 拉取仓库与 `Jenkinsfile`；
2. 动态创建 Agent Pod（nodeSelector 固定到 `k8s-master`）；
3. `python` 容器安装 uv 并按 `pyproject.toml` 安装依赖；
4. `nerdctl` 容器连接 `buildkitd` sidecar，多阶段构建前端（Node 18）+ 后端（Python 3.11）；
5. 镜像以阿里云 ACR 地址命名构建，完成后 `Loaded image` 到节点 containerd；
6. 镜像构建完成后推送到阿里云 ACR（`nerdctl push`）；第 4 阶段目前只输出占位提示，尚未执行 `kubectl` 发布。

## 镜像推送到阿里云 ACR

镜像在 `nerdctl` 容器中构建完成后，推送到阿里云 ACR：

- Registry：`crpi-m67ogm8wgcr0rh38.cn-hangzhou.personal.cr.aliyuncs.com`
- 命名空间/仓库：`tanchenrui/webapp`
- 标签：`<git short sha>`，例如 `da5526f`
- 完整地址：`crpi-m67ogm8wgcr0rh38.cn-hangzhou.personal.cr.aliyuncs.com/tanchenrui/webapp:da5526f`

推送依赖 Jenkins 中配置的 ACR 凭据（用户名/密码，或 `docker-registry` Secret），由流水线在构建阶段完成登录与 push。

## 已知问题与规避

### Agent 无法连接 Jenkins（DNS 污染）

- 现象：Agent Pod 内解析 `jenkins.jenkins.svc.cluster.local` 得到 `198.18.x.x`，JNLP 一直 offline。
- 正确做法：Jenkins Cloud 的 Jenkins URL 保持 **Service DNS**：

  ```text
  http://jenkins.jenkins.svc.cluster.local:8080
  ```

  它是 Jenkins 配置项（Manage Clouds → Kubernetes → Jenkins URL，或 JCasC 的 `jenkinsUrl`），不要写死 ClusterIP。

- 修复 CoreDNS（推荐）：

  ```bash
  kubectl -n kube-system get configmap coredns -o yaml
  # 把 forward . /etc/resolv.conf 改为可靠上游，例如 223.5.5.5
  kubectl -n kube-system rollout restart deployment/coredns
  ```

- 临时规避：仅在排障时给 Agent Pod 加 `hostAliases` 指向 Service ClusterIP，不要提交到仓库。
- 验证：`kubectl -n jenkins exec <agent-pod> -c jnlp -- getent hosts jenkins.jenkins.svc.cluster.local` 应返回 ClusterIP，而不是 `198.18.x.x`。

### kubectl 容器无法执行 sh

`container('kubectl')` 在该 Pod 里无法启动 `sh`（工作区权限/容器用户问题），因此真实部署阶段暂时回退为占位；后续建议把 kubectl 挂进 `python` 容器并用 SA token 调用。
