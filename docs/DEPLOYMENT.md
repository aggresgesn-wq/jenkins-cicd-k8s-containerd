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
运行期密钥放在 K8s Secret 中，名称示例为 `webapp-secret`，必须与 Deployment 的 `secretRef` 一致。

```powershell
# 目录：E:\CICD（PowerShell）
$SECRET_KEY = python -c "import secrets; print(secrets.token_hex(32))"
$CAPTCHA_SECRET_KEY = python -c "import secrets; print(secrets.token_hex(32))"

kubectl -n webapp create secret generic webapp-secret `
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
$env:ACR_REGISTRY = "crpi-m67ogm8wgcr0rh38.cn-hangzhou.personal.cr.aliyuncs.com"; $env:ACR_NAMESPACE = "<acr-namespace>"; $env:IMAGE_TAG = "local"
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
- 测试环境使用独立命名空间 `webapp-staging`，Jenkins 在人工批准前只会改动它，不会触碰生产：

```powershell
# 目录：E:\CICD（PowerShell）
kubectl apply -f deploy/k8s/overlays/staging/namespace.yaml
kubectl kustomize deploy/k8s/overlays/staging | kubectl apply -f -
kubectl -n webapp-staging rollout status deployment/webapp --timeout=180s
```

- 在 Ingress 中配置域名与 TLS Secret `webapp-tls`，并把 DNS 指向 Ingress Controller。
- `/metrics` 已在 Ingress 层拒绝公网访问，只允许集群内 Prometheus 抓取；需要临时排查时用 `kubectl port-forward`。
- Jenkins 流水线现在通过 `kubectl kustomize deploy/k8s/overlays/{staging,production}` 渲染整套配置后 `kubectl apply`，并用 `image@sha256:<digest>` 部署（digest 由 kaniko 输出），因此 ConfigMap、Ingress、HPA、PDB、NetworkPolicy 的变更也会随流水线发布。
- 如使用 Helm/GitOps，可用 `helm upgrade` 替代 `kubectl apply`；首次部署若因依赖顺序失败，确认 namespace、Secret、ConfigMap、PVC 已存在后重新 `kubectl apply -f deploy/k8s/`。

### 使用 Helm 部署（可选）

`deploy/helm/webapp` 与 `deploy/k8s` 管理同一批资源，二选一：

```powershell
# 目录：E:\CICD（PowerShell）
helm upgrade --install webapp deploy/helm/webapp -n webapp --create-namespace `
  --set image.tag="$(git rev-parse --short HEAD)" `
  --set ingress.host="app.example.com"
kubectl -n webapp rollout status deployment/webapp --timeout=180s
helm history webapp -n webapp
helm rollback webapp 1 -n webapp
```

`fullnameOverride` 固定为 `webapp`，因此 `kubectl set image deployment/webapp` 与 Helm 发布可以混用。

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

### 7.1 Jenkins 插件与云配置

安装方式（Helm / Docker / 包管理）、插件源加速、K8s Cloud 配置、凭据与备份恢复，见 [deploy/jenkins/README.md](../deploy/jenkins/README.md)。

安装 **Kubernetes**、**Credentials**、**Credentials Binding**、**Pipeline**、**Git**、**GitHub** 插件。

在 *Manage Jenkins → Clouds* 新增 Kubernetes Cloud：

- Kubernetes URL 与 Namespace：集群内 `https://kubernetes.default.svc`，Namespace 为构建 Pod 所在命名空间（示例 `jenkins`）。
- Credentials：有权创建 Pod 的 ServiceAccount 或 kubeconfig 凭据。
- Jenkins URL 与 Pod Template：`https://jenkins.example.com` 供 JNLP 回连；容器包含 Python、Node、kaniko、kubectl，不要 privileged、不要挂载宿主机 containerd socket。

### 7.2 凭据

在 *Manage Jenkins → Credentials* 创建：

| ID | 类型 | 用途 |
| --- | --- | --- |
| `acr-credentials` | Username with password | 推送/拉取 ACR 镜像 |
| `github-token` | Secret text | 回写 GitHub Commit Status（`repo:status` 权限） |
| `github-webhook-secret` | Secret text | 校验 GitHub Webhook 签名（与仓库 Webhook Secret 一致） |
| `kubeconfig` | Secret file | 集群外部署；集群内改用 ServiceAccount（见 `deploy/k8s/jenkins-rbac.yaml`） |

凭据 ID 已被 `webapp/Jenkinsfile` 引用，改名时需同步修改。镜像仓库命名空间通过 Jenkins 全局环境变量 `ACR_NAMESPACE` 提供（未设置时回退为 `your-namespace`），不要把个人账号写进 Jenkinsfile。

### 7.3 创建 GitHub Token

1. GitHub → *Settings → Developer settings → Personal access tokens*。
2. **Fine-grained token**：Repository access 选择该仓库，权限给 `Commit statuses: Read and write`、`Contents: Read-only`；若用经典 Token，勾选 `repo:status`（私有仓库还需 `repo`）。
3. 将 Token 保存为 Jenkins 的 `github-token`（Secret text），不要写进仓库或 Jenkinsfile。

Token 只用于两件事：回写提交状态、可选地读取仓库元数据；构建本身通过 Jenkins 的 Git 插件拉取代码（HTTPS + 独立凭据或 Deploy Key）。

### 7.4 配置 GitHub Webhook

1. 仓库 → *Settings → Webhooks → Add webhook*。
2. **Payload URL**：`https://jenkins.example.com/github-webhook/`（GitHub 插件端点，末尾斜杠不能省）。
3. **Content type**：`application/json`。
4. **Secret**：填与 Jenkins `github-webhook-secret` 一致的随机字符串（`openssl rand -hex 32`）。
5. **Events**：勾选 *Just the push event*；需要 PR 校验时再勾 *Pull requests*。
6. 保存后进入 *Recent Deliveries*，确认返回 `200`；再到 Jenkins 查看 Job 是否被触发。

> 若使用 Generic Webhook Trigger，Payload URL 改为 `https://jenkins.example.com/generic-webhook-trigger/invoke?token=<token>`，并在 Job 中配置 token 参数与分支过滤。

### 7.5 提交状态反馈

`webapp/Jenkinsfile` 会在流水线开始、成功、失败时调用 GitHub Status API，把结果写回对应 commit：

```bash
POST https://api.github.com/repos/aggresgesn-wq/jenkins-cicd-k8s-containerd/statuses/$GIT_COMMIT
Authorization: token $GITHUB_TOKEN
{"state":"success|failure|pending","context":"jenkins/ci","target_url":"$BUILD_URL","description":"..."}
```

配置好 `github-token` 后，Pull Request 页面会显示 `jenkins/ci` 检查项；Token 缺失时流水线只打印告警，不阻塞构建。

### 7.6 Jenkins Job

- 类型：*Pipeline script from SCM*，SCM 选 Git，仓库地址 `https://github.com/aggresgesn-wq/jenkins-cicd-k8s-containerd.git`，分支 `main`。
- Script Path：`webapp/Jenkinsfile`。
- 构建触发器：*GitHub hook trigger for GITScm polling*。
- 生产阶段使用 `input` 人工批准并限制审批人；拒绝或超时不得继续部署。

### 7.7 自建 Gitea（可选，Linux）

内网或离线环境可按 [deploy/gitea/README.md](../deploy/gitea/README.md) 在 Linux 上部署 Gitea：二进制 + systemd（推荐生产）、Docker Compose、或 K8s/Helm；其中包含 `app.ini` 示例、Nginx 反代、管理员初始化、备份升级与排障。

切换到 Gitea 时注意：

- Gitea 的 Webhook 事件头与 GitHub 不同，Jenkins 的 GitHub 插件 `/github-webhook/` 不一定能直接消费；优先使用 **Gitea 插件**（`/gitea-webhook/post`）或 **Generic Webhook Trigger**。
- `webapp/Jenkinsfile` 中的 `githubStatus()` 调用 GitHub Status API；切换到 Gitea 后需改为 Gitea 的 Commit Status 接口，或删除该步骤（流水线会打印告警但继续执行）。
- 仓库地址、SSH 端口（默认 2222）与凭据需在 Jenkins Job 中同步修改。

## 8. 备份与恢复

### 8.1 数据库备份

`deploy/k8s/mysql-backup-cronjob.yaml` 提供每日 `mysqldump` 备份（03:30，保留 7 天）：

```powershell
# 目录：E:\CICD（PowerShell）
kubectl apply -f deploy/k8s/mysql.yaml
kubectl apply -f deploy/k8s/mysql-backup-cronjob.yaml
kubectl -n webapp get cronjob,pods -l app=mysql-backup
kubectl -n webapp create job --from=cronjob/mysql-backup backup-manual
kubectl -n webapp logs job/backup-manual
```

托管数据库请使用云厂商的自动备份 + 跨可用区副本，并定期做恢复演练。

### 8.2 恢复演练

```bash
# 在临时命名空间恢复，验证数据完整性后再切流量
kubectl -n webapp exec -it mysql-0 -- sh -c \
  'gunzip -c /backup/authbase-<时间戳>.sql.gz | mysql -uroot -p"$MYSQL_ROOT_PASSWORD" authbase'
```

恢复后重点核对：`SYUSER`、`SYROLE`、`SYRESOURCE` 行数，管理员可登录，`db.sql` 版本与代码一致。

### 8.3 Jenkins 与镜像

- Jenkins `JENKINS_HOME` 包含凭据与密钥，需整体备份（见 [deploy/jenkins/README.md](../deploy/jenkins/README.md)）。
- 镜像保留策略：ACR 保留最近 30 个 tag，生产使用不可变 tag（git short sha）。

## 9. 监控与告警

应用在 `/metrics` 暴露 Prometheus 指标，配套告警与 Grafana 面板见 [deploy/monitoring/README.md](../deploy/monitoring/README.md)：

```powershell
# 目录：E:\CICD（PowerShell）
kubectl apply -f deploy/monitoring/servicemonitor.yaml     # Prometheus Operator
kubectl apply -f deploy/monitoring/prometheusrule.yaml
```

关键告警：5xx 比例、P95 延迟、登录失败突增、Pod 重启、HPA 达到上限。日志统一输出到 stdout，设置 `LOG_FORMAT=json` 便于采集；审计日志已对密码/Token 脱敏。

## 10. 故障排查

| 现象 | 常见原因 | 处理 |
| --- | --- | --- |
| 接口 401 | 未登录、Session 过期、`SECRET_KEY` 变更、`SESSION_COOKIE_SECURE=true` 但用 HTTP 访问、反向代理丢失 Cookie | 检查浏览器 Cookie 与 `Set-Cookie`；确认 HTTPS 与 `SECRET_KEY` 稳定；必要时重新登录 |
| 接口 403 | 角色未启用、角色未绑定资源、资源 `PERMS` 与 `@permission` 不一致、前端缓存了旧菜单 | 核对 `SYROLE.ROLEKEY`、`SYROLE_SYRESOURCE`、`SYRESOURCE.PERMS`；清除前端缓存 |
| 验证码错误 | 多副本 `CAPTCHA_SECRET_KEY` 不一致、服务器时间偏差、Cookie 被拦截 | 统一 Secret 并滚动重启；校准 NTP；确认浏览器允许 Cookie |
| 数据库连接失败 | 主机名/端口错误、MySQL 低于 8.0、账号无权限、密码未 URL 编码、NetworkPolicy 未放行 | 从 Pod 内用 `mysql` 客户端测试；检查 `DATABASE_URI` 与 Secret；核对 NetworkPolicy 出站规则 |
| 探针失败 | `/health/ready` 依赖数据库不可用、端口不是 5000、启动过慢、只读根文件系统导致写失败 | `kubectl describe pod` 看事件；`kubectl logs` 看启动日志；确认 `/tmp` 与上传 PVC 可写 |
| 镜像拉取失败 | 缺少 `acr-pull` Secret、tag 不存在、SWR/ACR 网络不通 | 检查 `imagePullSecrets`、镜像地址与仓库权限；基础镜像用 `mirror.py` 换国内地址 |
| 上传返回 413 | `MAX_CONTENT_LENGTH` 或 Ingress `proxy-body-size` 太小 | 同时调整应用环境变量与 Ingress 注解，重启后验证 |
| Jenkins 插件安装失败 | 默认更新站点在国内不可达 | 换用清华/日本镜像站点（见 deploy/jenkins/README.md 第 2 节）后重试 |
| 构建报 `command not found` | Jenkins/构建 Pod 的 PATH 不含工具路径 | 在 Pod 模板中直接使用带工具的镜像，或补 `PATH` 环境变量 |
| GitHub Webhook 不触发 | URL 末尾缺斜杠、Secret 不一致、插件未装 | 在 GitHub *Recent Deliveries* 查看响应码，对照 `github-webhook-secret` |
| 本地 `npm run dev` 接口 404 | 前端 `VUE_APP_BASE_API` 与后端蓝图前缀不一致 | 统一为 `/prod-api`，devServer 代理只转发、不做 pathRewrite |
| 刷新前端路由返回 404 | SPA history 模式缺少回退 | Flask 已提供 catch-all；若用 Nginx 直出静态文件，配置 `try_files $uri $uri/ /index.html` |
| 删除部门/角色报 409 | 存在子部门、关联用户或为内置角色 | 先解除引用；这是有意的业务约束，不是异常 |

排障时优先看三处：`kubectl -n webapp describe pod`、`kubectl -n webapp logs deploy/webapp`、Ingress Controller 访问日志。不要在日志中输出 Cookie、密码或完整连接串。
