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
| 3. 构建镜像（nerdctl + buildkitd） | 3m 48s |
| 4. K8s 一键部署 | 88ms（占位 echo，尚未执行 kubectl） |
| Declarative: Post Actions | 122ms |

![Jenkins #11 阶段视图](../images/jenkins/08-stage-view-verified.png)

## 流水线做了什么

1. Jenkins 通过 Pipeline from SCM 从 Gitea 拉取仓库与 `Jenkinsfile`；
2. 动态创建 Agent Pod（nodeSelector 固定到 `k8s-master`）；
3. `python` 容器安装 uv 并按 `pyproject.toml` 安装依赖；
4. `nerdctl` 容器连接 `buildkitd` sidecar，多阶段构建前端（Node 18）+ 后端（Python 3.11）；
5. 镜像以阿里云 ACR 地址命名构建，完成后 `Loaded image` 到节点 containerd；
6. 第 4 阶段目前只输出占位提示，尚未执行 `kubectl` 发布。

## 关于“推送到阿里云 ACR”

当前 Jenkinsfile 只做了 **构建 + 打 ACR 标签 + 加载到节点 containerd**，日志里是 `Loaded image`，**没有 `nerdctl push`**。要真正推到 ACR，需要：

```bash
nerdctl login -u <ACR_USER> -p <ACR_PASS> crpi-m67ogm8wgcr0rh38.cn-hangzhou.personal.cr.aliyuncs.com
nerdctl push ${FULL_IMG}
```

并在 Jenkins 里配置 ACR 凭据（用户名/密码或 `docker-registry` Secret）。README 里不会把“已构建”写成“已推送”。

## 已知问题与规避

- Pod 内 DNS 会污染 `jenkins.jenkins.svc.cluster.local`（解析到 198.18.x.x），导致 Agent 离线；已把 Jenkins Cloud 的 URL 改为 Service ClusterIP `http://10.96.68.92:8080`。
- `container('kubectl')` 在该 Pod 里无法启动 `sh`（工作区权限/容器用户问题），因此真实部署阶段暂时回退为占位；后续建议把 kubectl 挂进 `python` 容器并用 SA token 调用。
