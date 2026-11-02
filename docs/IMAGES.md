> 状态更新（2026-11-02）：本文描述加固候选方案，未由 #53 执行。当前实跑基线为 webapp/Jenkinsfile（Gitea + nerdctl/BuildKit）；参见根目录 README 和 docs/evidence/build-53/。

# 镜像清单

## #53 实跑基线

原始 webapp/Jenkinsfile 使用 python:3.11、nerdctl:latest、moby/buildkit:v0.31.1、固定版本 inbound-agent 的 SWR 镜像；webapp/dockerfile 使用 Node 18 和 Python 3.11。具体完整地址以这两个保留原文件为准。nerdctl 的 latest 尚未固定 digest，不应声称构建完全可复现。

下表仅描述 ci/Jenkinsfile.hardened 的加固候选，不能套用到 #53。

基础镜像优先使用 [docker.aityp.com](https://docker.aityp.com) 同步到华为云 SWR 的地址，避免 Docker Hub / gcr.io 在国内不可达：

```text
swr.cn-north-4.myhuaweicloud.com/ddn-k8s/<原始仓库>/<镜像>:<tag>
```

## 流水线构建 Pod（ci/Jenkinsfile.hardened）

| 容器 | 原始镜像 | 使用的镜像地址 |
| --- | --- | --- |
| python | `docker.io/python:3.11` | `swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.11` |
| node | `docker.io/node:18` | `swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/node:18` |
| buildkit | `moby/buildkit:v0.31.1-rootless` | 同原始镜像；使用前确认网络或同步企业仓库 |
| kubectl | `docker.io/bitnami/kubectl:1.29.3-debian-12-r3` | `swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/bitnami/kubectl:1.29.3-debian-12-r3` |
| helm（清单 lint） | `docker.io/alpine/helm:3.20.2` | `swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/alpine/helm:3.20.2` |
| kubeconform（Schema 校验） | `ghcr.io/yannh/kubeconform:v0.6.7-alpine` | 同原始镜像（包含 shell） |
| trivy（镜像扫描） | `docker.io/aquasec/trivy:0.68.2` | `swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/aquasec/trivy:0.68.2` |
| syft（SBOM） | `anchore/syft:v1.46.0-debug` | 同原始镜像（/busybox/sh） |

> `bitnami/kubectl:1.29` 这种短 tag 在同步站不存在，必须用完整 tag（如 `1.29.3-debian-12-r3`）。

## 应用构建（webapp/dockerfile.production）

| 阶段 | 原始镜像 | 默认地址（可用 build-arg 覆盖） |
| --- | --- | --- |
| 前端构建 | `node:18` | `swr.cn-north-4.../docker.io/node:18`（`UI_IMAGE`） |
| 运行阶段 | `python:3.11` | `swr.cn-north-4.../docker.io/python:3.11`（`BASE_IMAGE`） |

## 部署清单与运维组件

| 用途 | 原始镜像 | 使用的镜像地址 |
| --- | --- | --- |
| 应用运行（Deployment 业务镜像） | 本项目构建产物 | `<ACR>/<namespace>/webapp@sha256:...`（CI 用 digest 部署） |
| MySQL（示例） | `docker.io/mysql:8.0` | `swr.cn-north-4.../docker.io/mysql:8.0` |
| MySQL 备份 CronJob | `docker.io/mysql:8.0` | 同上 |
| Jenkins Controller | `docker.io/jenkins/jenkins:lts-jdk17` | `swr.cn-north-4.../docker.io/jenkins/jenkins:lts-jdk17` |
| Jenkins Agent | `docker.io/jenkins/inbound-agent:3283.v92c105e0f819-9-jdk17` | `swr.cn-north-4.../docker.io/jenkins/inbound-agent:3283.v92c105e0f819-9-jdk17` |
| Gitea（可选，宿主机 Docker） | `docker.io/gitea/gitea:1.22.6` | `swr.cn-north-4.../docker.io/gitea/gitea:1.22.6` |

## 校验方式

新增或升级镜像前，先确认同步站已收录（`webapp/docker/mirror.py` 封装了公开 API）：

```bash
cd webapp
python docker/mirror.py python:3.11 node:18 mysql:8.0
python docker/mirror.py moby/buildkit:v0.31.1-rootless
python docker/mirror.py bitnami/kubectl:1.29.3-debian-12-r3
```

- 查询到结果时脚本直接输出可用的 SWR 地址；
- 查不到会按规则拼兜底地址并提示，**不要直接用兜底地址上生产**，应先到
  <https://docker.aityp.com/manage/add> 提交同步，等同步完成后再更新清单。
- 拉取失败时优先检查 tag 是否存在（短 tag 如 `1.29` 往往没有），以及节点是否允许访问 `swr.cn-north-4.myhuaweicloud.com`。
