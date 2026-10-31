# 镜像清单（统一走渡渡鸟镜像同步站）

仓库内所有容器镜像都使用 [docker.aityp.com](https://docker.aityp.com) 同步到华为云 SWR 的地址，避免 Docker Hub / gcr.io 在国内不可达：

```text
swr.cn-north-4.myhuaweicloud.com/ddn-k8s/<原始仓库>/<镜像>:<tag>
```

## 流水线构建 Pod（webapp/Jenkinsfile）

| 容器 | 原始镜像 | 使用的镜像地址 |
| --- | --- | --- |
| python | `docker.io/python:3.11` | `swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.11` |
| node | `docker.io/node:18` | `swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/node:18` |
| kaniko | `gcr.io/kaniko-project/executor:v1.23.2-debug` | `swr.cn-north-4.myhuaweicloud.com/ddn-k8s/gcr.io/kaniko-project/executor:v1.23.2-debug` |
| kubectl | `docker.io/bitnami/kubectl:1.29.3-debian-12-r3` | `swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/bitnami/kubectl:1.29.3-debian-12-r3` |
| helm（清单 lint） | `docker.io/alpine/helm:3.20.2` | `swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/alpine/helm:3.20.2` |
| kubeconform（Schema 校验） | `ghcr.io/yannh/kubeconform:latest` | `swr.cn-north-4.myhuaweicloud.com/ddn-k8s/ghcr.io/yannh/kubeconform:latest` |
| trivy（镜像扫描） | `docker.io/aquasec/trivy:0.68.2` | `swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/aquasec/trivy:0.68.2` |
| syft（SBOM） | `docker.io/anchore/syft:v1.46.0` | `swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/anchore/syft:v1.46.0` |

> `bitnami/kubectl:1.29` 这种短 tag 在同步站不存在，必须用完整 tag（如 `1.29.3-debian-12-r3`）。

## 应用构建（webapp/dockerfile）

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
python docker/mirror.py gcr.io/kaniko-project/executor:v1.23.2-debug
python docker/mirror.py bitnami/kubectl:1.29.3-debian-12-r3
```

- 查询到结果时脚本直接输出可用的 SWR 地址；
- 查不到会按规则拼兜底地址并提示，**不要直接用兜底地址上生产**，应先到
  <https://docker.aityp.com/manage/add> 提交同步，等同步完成后再更新清单。
- 拉取失败时优先检查 tag 是否存在（短 tag 如 `1.29` 往往没有），以及节点是否允许访问 `swr.cn-north-4.myhuaweicloud.com`。
