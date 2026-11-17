# Gitea/GitLab + Jenkins + Kubernetes（containerd）CI/CD 实践

从代码托管平台拉取源码，用仓库里的 `Jenkinsfile` 驱动 Jenkins 完成构建与部署，最终在 Kubernetes 集群里通过 containerd 运行应用，并用 Service/Ingress 对外访问。

## 链路

```text
Gitea / GitLab（源码）
        │  webhook 或手动触发
        ▼
Jenkins（Pipeline：拉代码 → 装依赖 → 构建镜像 → 推送镜像仓库）
        │  kubectl / kustomize
        ▼
Kubernetes API Server ──▶ 节点 kubelet ──▶ containerd ──▶ Pod
                                                        │
                                              Service / Ingress
                                                        │
                                                     浏览器访问
```

## 真实构建记录

Jenkins `#53` 成功构建：Gitea 检出、依赖安装、前端打包、镜像构建均已完成；部署阶段当时是占位输出，尚未真正发布到集群。

<img src="docs/images/jenkins/07-build-53-success.png" width="900" alt="Jenkins #53 成功构建"/>

## 已验证流水线（#11）

真实跑通的 4 阶段流水线：Gitea 检出 → uv 安装依赖 → nerdctl/buildkit 构建镜像 → 部署占位。

<img src="docs/images/jenkins/08-stage-view-verified.png" width="900" alt="Jenkins #11 阶段视图"/>

- 构建 #11，SUCCESS，约 4 分 45 秒
- 镜像：`crpi-m67ogm8wgcr0rh38.cn-hangzhou.personal.cr.aliyuncs.com/tanchenrui/webapp:da5526f`（已推送到阿里云 ACR）
- 详细记录见 [docs/JENKINS-PIPELINE.md](docs/JENKINS-PIPELINE.md)

## 快速开始

1. Jenkins 新建 Pipeline 任务，SCM 指向 Gitea/GitLab 仓库；
2. Script Path 选择 `webapp/Jenkinsfile`（#11 验证版）或 `ci/Jenkinsfile.lab`；
3. 配置凭据：阿里云 ACR 账号、集群 kubeconfig；
4. 触发构建，流水线完成镜像构建并推送到阿里云 ACR；
5. 按下面的「Kubernetes 部署」发布并访问。

## 推送镜像到阿里云 ACR

镜像地址约定：

```text
crpi-m67ogm8wgcr0rh38.cn-hangzhou.personal.cr.aliyuncs.com/tanchenrui/webapp:<git-short-sha>
```

手动推送（Docker）：

```bash
docker login crpi-m67ogm8wgcr0rh38.cn-hangzhou.personal.cr.aliyuncs.com -u <ACR_USER>
docker tag webapp:da5526f crpi-m67ogm8wgcr0rh38.cn-hangzhou.personal.cr.aliyuncs.com/tanchenrui/webapp:da5526f
docker push crpi-m67ogm8wgcr0rh38.cn-hangzhou.personal.cr.aliyuncs.com/tanchenrui/webapp:da5526f
```

手动推送（containerd / nerdctl）：

```bash
nerdctl login -u <ACR_USER> crpi-m67ogm8wgcr0rh38.cn-hangzhou.personal.cr.aliyuncs.com
nerdctl tag webapp:da5526f crpi-m67ogm8wgcr0rh38.cn-hangzhou.personal.cr.aliyuncs.com/tanchenrui/webapp:da5526f
nerdctl push crpi-m67ogm8wgcr0rh38.cn-hangzhou.personal.cr.aliyuncs.com/tanchenrui/webapp:da5526f
```

Jenkins 中推送：

- 在 Jenkins 凭据里保存 ACR 用户名/密码（`Username with password`，ID 例如 `acr-credentials`）；
- 流水线内用 `withCredentials` 注入，`nerdctl login` 后 `nerdctl push ${FULL_IMG}`；
- 私有仓库拉取还需在命名空间创建 `docker-registry` 类型的 imagePullSecret。

## Kubernetes 部署

前置：kubectl 已连接集群，集群有 Ingress Controller（示例 ingress-nginx）。

1）创建命名空间：

```bash
kubectl apply -f deploy/k8s/namespace.yaml                 # webapp
kubectl apply -f deploy/k8s/overlays/staging/namespace.yaml # webapp-staging
```

2）创建 MySQL Secret 并部署 MySQL（`mysql.yaml` 固定 namespace `webapp`）：

```bash
kubectl -n webapp create secret generic mysql-secret \
  --from-literal=MYSQL_ROOT_PASSWORD="$(openssl rand -hex 16)" \
  --from-literal=MYSQL_PASSWORD="$(openssl rand -hex 16)"
kubectl apply -f deploy/k8s/mysql.yaml

# staging 部署时把 namespace 替换成 webapp-staging
sed 's/namespace: webapp/namespace: webapp-staging/g' deploy/k8s/mysql.yaml | kubectl apply -f -
```

3）创建应用 Secret（键名必须与 Deployment 一致）：

```bash
kubectl -n webapp-staging create secret generic webapp-secret \
  --from-literal=SECRET_KEY="$(openssl rand -hex 32)" \
  --from-literal=CAPTCHA_SECRET_KEY="$(openssl rand -hex 32)" \
  --from-literal=DATABASE_URI="mysql+mysqlconnector://webapp:REPLACE_ME@mysql:3306/authbase?charset=utf8mb4" \
  --dry-run=client -o yaml | kubectl apply -f -
```

`REPLACE_ME` 需替换为 `mysql-secret` 中 `MYSQL_PASSWORD` 的实际值。

4）渲染并应用应用清单（把 `IMAGE_PLACEHOLDER` 换成刚推送的镜像）：

```bash
IMAGE=crpi-m67ogm8wgcr0rh38.cn-hangzhou.personal.cr.aliyuncs.com/tanchenrui/webapp:da5526f
kubectl kustomize deploy/k8s/overlays/staging \
  | sed "s|IMAGE_PLACEHOLDER|$IMAGE|" \
  | kubectl apply -f -
```

`base/` 会一并创建：Deployment、Service、Ingress、ConfigMap、PVC、ServiceAccount、NetworkPolicy、PDB、HPA。

5）验证与访问：

```bash
kubectl -n webapp-staging rollout status deployment/webapp --timeout=180s
kubectl -n webapp-staging get pods,svc,ingress
kubectl -n webapp-staging port-forward svc/webapp 8080:80
# 浏览器打开 http://127.0.0.1:8080
```

生产环境把 `staging` 换成 `production`、命名空间换成 `webapp`：

```bash
kubectl apply -f deploy/k8s/namespace.yaml
IMAGE=crpi-m67ogm8wgcr0rh38.cn-hangzhou.personal.cr.aliyuncs.com/tanchenrui/webapp:da5526f
kubectl kustomize deploy/k8s/overlays/production \
  | sed "s|IMAGE_PLACEHOLDER|$IMAGE|" \
  | kubectl apply -f -
```

## 仓库结构

```text
.
├── webapp/          # Flask + Vue 示例应用：Jenkinsfile、dockerfile、app/、ui/、tests/
├── ci/              # 场景化 Jenkinsfile：lab / hardened / release
├── deploy/
│   ├── k8s/         # Kustomize：namespace、secret 模板、MySQL、Jenkins RBAC、base + staging/production overlay
│   ├── helm/webapp/ # 可选 Helm Chart（与 Kustomize 二选一）
│   ├── jenkins/     # Jenkins 安装、JCasC、Job DSL
│   └── containerd/  # containerd 安装与校验
├── ops/             # 集群巡检脚本与测试
└── docs/            # 架构、部署、运维、证据与边界说明
```

## 当前范围（设计 vs 实跑）

| 能力 | 状态 |
| --- | --- |
| Gitea/GitLab 源码检出 | #53 已运行 |
| Jenkins 动态 Agent 构建 | #53 已运行 |
| 镜像构建 | #53 已运行 |
| 镜像推送（阿里云 ACR） | ✅ #11 已运行 |
| Kustomize 部署到 Kubernetes | 脚本支持，待实跑 |
| containerd 拉取并运行 Pod | ✅ 已运行 |
| Service / Ingress 访问 | ✅ 已运行 |

## 已验证的事实

- Jenkins `#11` 构建成功：代码检出、依赖安装、Vue 打包、镜像构建并推送阿里云 ACR（`webapp:da5526f`）
- containerd 拉取镜像并运行 Pod 已跑通，Service / Ingress 可正常访问
- GitHub Actions：后端测试、发布回归、CodeQL 当前通过

## 界面

| 应用登录页 | 应用首页 |
| --- | --- |
| <img src="docs/images/app/01-login.png" width="420" alt="应用登录页"/> | <img src="docs/images/app/02-dashboard.png" width="420" alt="应用首页"/> |

更多截图见 [docs/JENKINS-UI.md](docs/JENKINS-UI.md)。

## 文档

| 文件 | 用途 |
| --- | --- |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | 环境准备、Secret、数据库、部署与排障 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 拓扑与组件职责 |
| [docs/OPERATIONS.md](docs/OPERATIONS.md) | 巡检、备份与恢复 |
| [docs/IMAGES.md](docs/IMAGES.md) | 镜像清单与同步站地址 |
| [docs/evidence/build-53/README.md](docs/evidence/build-53/README.md) | #53 构建证据与边界 |

## 说明

- `webapp/Jenkinsfile` 按字节保留 #53 原文件，路径与变量以该文件为准；
- 部署前请确认 kubeconfig、命名空间和镜像地址已替换为你的环境。
