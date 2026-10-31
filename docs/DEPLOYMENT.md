# 部署指南

本文覆盖从零部署到 Kubernetes 的完整流程：环境准备、Secret、数据库、镜像构建、部署、健康检查、回滚，以及 Jenkins 与 GitHub 的接入。命令默认在 Windows PowerShell 7 中执行，标注 Git Bash 的除外。

## 1. 环境准备
- Kubernetes 1.24+，容器运行时为 containerd，`kubectl` 已配置集群上下文。
- Ingress Controller（示例使用 ingress-nginx），并准备可解析的域名。
- MySQL 8.0+（托管实例或容器），字符集 `utf8mb4`。
- 可推送的镜像仓库（示例为阿里云 ACR），以及拉取镜像用的凭据。
- Jenkins（集群内或集群外均可），用于运行 `webapp/Jenkinsfile`。

```powershell
# 目录：E:\CICD（PowerShell）
kubectl get nodes
kubectl create namespace webapp --dry-run=client -o yaml | kubectl apply -f -
```

命名空间以 `deploy/k8s` 清单为准；上面的命令是幂等的，便于首次部署和重复执行。

## 2. 创建 Secret
运行期密钥放在 K8s Secret 中，名称示例为 `webapp-secrets`，必须与 Deployment 的 `secretRef` 一致。

```powershell
# 目录：E:\CICD（PowerShell）
$SECRET_KEY = python -c "import secrets; print(secrets.token_hex(32))"
$CAPTCHA_SECRET_KEY = python -c "import secrets; print(secrets.token_hex(32))"

kubectl -n webapp create secret generic webapp-secrets `
  --from-literal=SECRET_KEY="$SECRET_KEY" `
  --from-literal=CAPTCHA_SECRET_KEY="$CAPTCHA_SECRET_KEY" `
  --from-literal=DATABASE_URI="mysql+mysqlconnector://webapp:REPLACE_ME@mysql.example.internal:3306/authbase?charset=utf8mb4" `
  --dry-run=client -o yaml | kubectl apply -f -
```

- 没有系统 Python 时，在 `webapp` 目录用 `uv run python -c "..."` 生成随机值。
- `DATABASE_URI` 中的密码要替换为真实值并做 URL 编码；不要把真实值写进本文或 Git。
- 修改 Secret 后执行 `kubectl -n webapp rollout restart deployment/webapp` 让环境变量生效。

拉取 ACR 私有镜像还需要 docker-registry 类型的 Secret：

```powershell
# 目录：E:\CICD（PowerShell）
kubectl -n webapp create secret docker-registry acr-pull `
  --docker-server="crpi-m67ogm8wgcr0rh38.cn-hangzhou.personal.cr.aliyuncs.com" `
  --docker-username="your-username" `
  --docker-password="your-password" `
  --dry-run=client -o yaml | kubectl apply -f -
```

## 3. 初始化数据库
`db.sql` 只包含表结构与种子数据，不包含 `CREATE DATABASE`，必须先建库。机构查询使用递归 CTE，MySQL 必须为 8.0 及以上。

### 方式 A：本地/测试用 MySQL 容器

```powershell
# 目录：E:\CICD（PowerShell）
$env:MYSQL_ROOT_PASSWORD = "replace-with-strong-password"
docker run -d --name webapp-mysql -p 3306:3306 `
  -e MYSQL_ROOT_PASSWORD="$env:MYSQL_ROOT_PASSWORD" `
  -e MYSQL_DATABASE=authbase `
  -v webapp-mysql:/var/lib/mysql `
  mysql:8.0

docker exec webapp-mysql mysqladmin ping -uroot -p"$env:MYSQL_ROOT_PASSWORD" --silent
docker cp .\webapp\db.sql webapp-mysql:/tmp/db.sql
docker exec -i webapp-mysql mysql -uroot -p"$env:MYSQL_ROOT_PASSWORD" authbase -e "source /tmp/db.sql"
```

```powershell
# 目录：E:\CICD（PowerShell；创建应用账号，密码与 DATABASE_URI 一致）
docker exec -i webapp-mysql mysql -uroot -p"$env:MYSQL_ROOT_PASSWORD" -e "CREATE USER IF NOT EXISTS 'webapp'@'%' IDENTIFIED BY 'REPLACE_ME'; GRANT SELECT,INSERT,UPDATE,DELETE ON authbase.* TO 'webapp'@'%'; FLUSH PRIVILEGES;"
```

该容器只适合本地验证。K8s 内的应用不能通过 `127.0.0.1` 访问它，应使用集群内可达的地址或托管实例。

### 方式 B：托管 MySQL

```bash
# 目录：E:\CICD（Git Bash）
mysql -h "$DB_HOST" -u "$DB_ADMIN" -p -e "CREATE DATABASE IF NOT EXISTS authbase CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;"
mysql -h "$DB_HOST" -u "$DB_ADMIN" -p authbase < webapp/db.sql
```

再由 DBA 创建最小权限账号，SQL 与方式 A 相同；账号只授予业务所需的 `SELECT/INSERT/UPDATE/DELETE`。

导入前先备份；导入后检查 `SYUSER`、`SYROLE`、`SYRESOURCE` 行数与预期一致。

## 4. 构建镜像
```powershell
# 目录：E:\CICD（PowerShell；构建上下文为 webapp，COPY 路径相对该目录）
$env:ACR_REGISTRY = "crpi-m67ogm8wgcr0rh38.cn-hangzhou.personal.cr.aliyuncs.com"; $env:ACR_NAMESPACE = "tanchenrui"; $env:IMAGE_TAG = "local"
docker build -f webapp/dockerfile `
  --build-arg UI_IMAGE="swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/node:18" `
  --build-arg BASE_IMAGE="swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.11" `
  -t "$env:ACR_REGISTRY/$env:ACR_NAMESPACE/webapp:$env:IMAGE_TAG" `
  webapp
docker push "$env:ACR_REGISTRY/$env:ACR_NAMESPACE/webapp:$env:IMAGE_TAG"
```

| build ARG | 默认值 | 说明 |
| --- | --- | --- |
| `UI_IMAGE` | `swr.cn-north-4.../docker.io/node:18` | 前端构建阶段镜像；需要官方镜像时覆盖为 `node:18` |
| `BASE_IMAGE` | `swr.cn-north-4.../docker.io/python:3.11` | 运行阶段镜像；需要官方镜像时覆盖为 `python:3.11` |

`ARG` 只在构建期生效，不要用它传递密钥；密钥会进入镜像历史。运行期配置一律通过环境变量或 Secret 注入。

CI 中使用 kaniko，不依赖 Docker daemon：

```bash
# 目录：Jenkins 构建 Pod 内
/kaniko/executor --context=/workspace/webapp --dockerfile=/workspace/webapp/dockerfile \
  --destination="$FULL_IMG" \
  --build-arg=UI_IMAGE="$UI_IMAGE" --build-arg=BASE_IMAGE="$BASE_IMAGE"
```

kaniko 使用 Jenkins 挂载的仓库凭据，不需要 privileged 容器，也不挂载宿主机 containerd socket；Rootless BuildKit 是等价替代方案，二者可互换。

## 5. 部署到 Kubernetes
```powershell
# 目录：E:\CICD（PowerShell）
kubectl apply -f deploy/k8s/
kubectl -n webapp set image deployment/webapp webapp="$env:ACR_REGISTRY/$env:ACR_NAMESPACE/webapp:$env:IMAGE_TAG"
kubectl -n webapp rollout status deployment/webapp --timeout=180s
kubectl -n webapp get pods,svc,ingress
```

- `set image` 中的 `webapp` 是容器名，示例与清单保持一致；如不同，先 `kubectl -n webapp get deployment webapp -o yaml` 确认。
- 在 Ingress 中配置域名与 TLS Secret `webapp-tls`，并把 DNS 指向 Ingress Controller。
- 如使用 Helm/GitOps，可用 `helm upgrade` 替代 `kubectl apply`；首次部署若因依赖顺序失败，确认 namespace、Secret、ConfigMap、PVC 已存在后重新 `kubectl apply -f deploy/k8s/`。

## 6. 健康检查与回滚
```powershell
# 目录：E:\CICD（PowerShell，单独终端保持运行）
kubectl -n webapp port-forward svc/webapp 8080:80
```
```powershell
# 目录：E:\CICD（PowerShell，另一个终端）
curl.exe -i http://127.0.0.1:8080/health/live
curl.exe -i http://127.0.0.1:8080/health/ready
kubectl -n webapp get endpoints webapp
```

两个探针都应返回 200，且 `endpoints` 中至少有一个 Ready 地址。`/health/ready` 失败通常意味着数据库不可用；此时 Pod 会被摘除流量，但不会被重启。

```powershell
# 目录：E:\CICD（PowerShell）
kubectl -n webapp rollout history deployment/webapp
kubectl -n webapp rollout undo deployment/webapp
kubectl -n webapp rollout undo deployment/webapp --to-revision=2
```

先在测试环境验证回滚，再执行生产回滚。PDB 与滚动更新策略保证回滚期间至少保留一个可用副本。

## 7. Jenkins 与 GitHub 接入

### Jenkins 插件与云配置

安装 **Kubernetes**、**Credentials**、**Credentials Binding**、**Pipeline**、**Git** 插件；GitHub 触发可使用 **GitHub** 插件或 Generic Webhook Trigger。

在 *Manage Jenkins → Clouds* 新增 Kubernetes Cloud：

- Kubernetes URL 与 Namespace：集群内 `https://kubernetes.default.svc`，Namespace 为构建 Pod 所在命名空间（示例 `jenkins`）。
- Credentials：有权创建 Pod 的 ServiceAccount 或 kubeconfig 凭据。
- Jenkins URL 与 Pod Template：`https://jenkins.example.com` 供 JNLP 回连；容器包含 Python 与 kaniko，不要 privileged、不要挂载宿主机 containerd socket。

### 凭据

在 *Manage Jenkins → Credentials* 创建：

| ID | 类型 | 用途 |
| --- | --- | --- |
| `acr-credentials` | Username with password | 推送/拉取 ACR 镜像 |
| `github-token` | Secret text | GitHub API / Webhook 校验 |
| `kubeconfig` | Secret file | 集群外部署；集群内可改用 ServiceAccount |

`ACR_REGISTRY`、`ACR_NAMESPACE` 与 Jenkinsfile 中的环境变量保持一致；凭据 ID 如有调整，同步修改 Jenkinsfile。

### Gitea Webhook

1. 进入 Gitea 仓库 → *Settings → Webhooks → Add Webhook → Gitea*。
2. Target URL 填 Jenkins 的 Gitea 端点，例如 `https://jenkins.example.com/gitea-webhook/post`；使用 Generic Webhook Trigger 时填 `https://jenkins.example.com/generic-webhook-trigger/invoke?token=<token>`。
3. Secret 填与 Jenkins 凭据一致的随机值，不要复用应用 `SECRET_KEY`。
4. 勾选 **Push** 与 **Pull Request** 事件，Content Type 选 `application/json`；保存后点击 *Test Delivery*，确认最近一次返回 2xx，再到 Jenkins 查看构建是否被触发。
5. Jenkins Job 使用 *Pipeline script from SCM*，Script Path 指向 `webapp/Jenkinsfile`，分支限制为 `main`。

生产阶段建议配置 `input` 人工批准，并限制审批人；拒绝或超时不得继续部署。

## 8. 故障排查

| 现象 | 常见原因 | 处理 |
| --- | --- | --- |
| 接口 401 | 未登录、Session 过期、`SECRET_KEY` 变更、`SESSION_COOKIE_SECURE=true` 但用 HTTP 访问、反向代理丢失 Cookie | 检查浏览器 Cookie 与 `Set-Cookie`；确认 HTTPS 与 `SECRET_KEY` 稳定；必要时重新登录 |
| 接口 403 | 角色未启用、角色未绑定资源、资源 `PERMS` 与 `@permission` 不一致、前端缓存了旧菜单 | 核对 `SYROLE.ROLEKEY`、`SYROLE_SYRESOURCE`、`SYRESOURCE.PERMS`；清除前端缓存 |
| 验证码错误 | 多副本 `CAPTCHA_SECRET_KEY` 不一致、服务器时间偏差、Cookie 被拦截 | 统一 Secret 并滚动重启；校准 NTP；确认浏览器允许 Cookie |
| 数据库连接失败 | 主机名/端口错误、MySQL 低于 8.0、账号无权限、密码未 URL 编码、NetworkPolicy 未放行 | 从 Pod 内用 `mysql` 客户端测试；检查 `DATABASE_URI` 与 Secret；核对 NetworkPolicy 出站规则 |
| 探针失败 | `/health/ready` 依赖数据库不可用、端口不是 5000、启动过慢、只读根文件系统导致写失败 | `kubectl describe pod` 看事件；`kubectl logs` 看启动日志；确认 `/tmp` 与上传 PVC 可写 |
| 镜像拉取失败 | 缺少 `acr-pull` Secret、tag 不存在、SWR/ACR 网络不通 | 检查 `imagePullSecrets`、镜像地址与仓库权限；基础镜像用 `mirror.py` 换国内地址 |
| 上传返回 413 | `MAX_CONTENT_LENGTH` 或 Ingress `proxy-body-size` 太小 | 同时调整应用环境变量与 Ingress 注解，重启后验证 |

排障时优先看三处：`kubectl -n webapp describe pod`、`kubectl -n webapp logs deploy/webapp`、Ingress Controller 访问日志。不要在日志中输出 Cookie、密码或完整连接串。
