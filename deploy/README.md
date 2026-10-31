# webapp 云原生部署说明

本目录是 Flask + Vue 应用（`webapp`）的 Kubernetes 部署产物，包含 Deployment、Service、
Ingress、PVC、NetworkPolicy、PDB 等清单，可用 `kubectl apply -k` 一键部署。

## 目录结构

```text
deploy/
├── README.md
└── k8s/
    ├── kustomization.yaml   # 资源列表，apply -k 入口
    ├── namespace.yaml       # namespace: webapp
    ├── configmap.yaml       # 非敏感配置
    ├── secret.example.yaml  # Secret 占位示例（不在 kustomization 中）
    ├── serviceaccount.yaml  # 无 RBAC、关闭 Token 挂载
    ├── pvc.yaml             # /app/uploads 持久卷
    ├── deployment.yaml      # 2 副本、探针、安全上下文
    ├── service.yaml         # ClusterIP 80 -> 5000
    ├── ingress.yaml         # webapp.example.com，nginx class
    ├── networkpolicy.yaml   # 默认拒绝入站 + 最小出站
    └── pdb.yaml             # minAvailable: 1
```

## 前置条件

- Kubernetes 1.21+（使用 `policy/v1` PDB 与 `networking.k8s.io/v1` Ingress）；
- 已安装 ingress-nginx，且 `IngressClass` 名称为 `nginx`（按需修改 `ingress.yaml`）；
- 集群有默认 StorageClass，且支持 `ReadWriteMany`（NFS / CephFS / NAS 等）；
  只有 `ReadWriteOnce` 存储时请看 [存储说明](#存储说明)；
- 已构建并推送镜像，地址形如
  `crpi-m67ogm8wgcr0rh38.cn-hangzhou.personal.cr.aliyuncs.com/<acr-namespace>/webapp:<git-short-sha>`；
- 本地具备 `kubectl`，可选安装 `kustomize`。

## 1. 创建命名空间

```bash
kubectl apply -f deploy/k8s/namespace.yaml
```

## 2. 创建 Secret（不要提交真实值）

`secret.example.yaml` 只是字段示例，**请勿把它直接应用到生产环境**。用下面的命令创建真实 Secret：

```bash
kubectl -n webapp create secret generic webapp-secret \
  --from-literal=SECRET_KEY="$(openssl rand -hex 32)" \
  --from-literal=CAPTCHA_SECRET_KEY="$(openssl rand -hex 16)" \
  --from-literal=DATABASE_URI='mysql+mysqlconnector://webapp:数据库密码@mysql:3306/authbase?charset=utf8'
```

说明：

- `SECRET_KEY` 用于 Flask 会话 / CSRF 签名，至少 32 字符，推荐 `openssl rand -hex 32`；
- `CAPTCHA_SECRET_KEY` 用于验证码签名，推荐 `openssl rand -hex 16`；
- `DATABASE_URI` 中的密码如果包含 `@ : / ? # %` 等字符，需要先做 URL 编码，例如：

  ```bash
  python -c 'import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1], safe=""))' 'p@ss:w/ord'
  ```

- 需要覆盖已有 Secret 时，使用 `--dry-run=client -o yaml | kubectl apply -f -`，避免先删后建：

  ```bash
  kubectl -n webapp create secret generic webapp-secret \
    --from-literal=SECRET_KEY="$(openssl rand -hex 32)" \
    --from-literal=CAPTCHA_SECRET_KEY="$(openssl rand -hex 16)" \
    --from-literal=DATABASE_URI='mysql+mysqlconnector://webapp:密码@mysql:3306/authbase?charset=utf8' \
    --dry-run=client -o yaml | kubectl apply -f -
  ```

- 校验键是否存在（不会打印值）：

  ```bash
  kubectl -n webapp describe secret webapp-secret
  ```

> `secret.example.yaml` 故意没有列入 `kustomization.yaml`，因此 `kubectl apply -k` 不会用占位符覆盖上面创建的真实 Secret。

## 3. 部署

先准备本次发布的镜像地址，然后执行：

```bash
export IMAGE=crpi-m67ogm8wgcr0rh38.cn-hangzhou.personal.cr.aliyuncs.com/<acr-namespace>/webapp:<git-short-sha>

kubectl apply -k deploy/k8s
kubectl -n webapp set image deployment/webapp webapp="$IMAGE"
kubectl -n webapp rollout status deployment/webapp --timeout=180s
```

`deployment.yaml` 中的镜像占位符是 `IMAGE_PLACEHOLDER`，首次 `apply` 后立即 `set image` 即可；
如果 CI 环境安装了 `kustomize`，也可以先替换镜像再 apply，避免出现短暂的 `ImagePullBackOff`：

```bash
cd deploy/k8s
kustomize edit set image IMAGE_PLACEHOLDER="$IMAGE"
kubectl apply -k .
```

## 4. 验证

```bash
kubectl -n webapp get deploy,rs,pods,svc,ingress,pvc

# 端口转发做本地健康检查（port-forward 会占用当前终端，另开一个终端执行 curl）
kubectl -n webapp port-forward svc/webapp 8080:80
curl -i http://127.0.0.1:8080/health/live    # 存活：不查数据库，返回 200
curl -i http://127.0.0.1:8080/health/ready   # 就绪：执行 SELECT 1，数据库异常返回 503

# 通过 Ingress 验证（替换为实际入口 IP/域名）
curl -i -H 'Host: webapp.example.com' http://<ingress-ip>/health/live
```

部署完成后可访问 `http://webapp.example.com/`。登录页由 Flask 提供静态资源，接口前缀为 `/prod-api`。

## 5. 滚动发布

```bash
# 记录变更原因，便于回滚时识别版本
kubectl -n webapp annotate deployment/webapp kubernetes.io/change-cause="release ${IMAGE##*:}" --overwrite

# 更新镜像会触发 RollingUpdate：maxUnavailable=0、maxSurge=1，先起新 Pod 再停旧 Pod
kubectl -n webapp set image deployment/webapp webapp="$IMAGE"
kubectl -n webapp rollout status deployment/webapp --timeout=180s
kubectl -n webapp rollout history deployment/webapp
```

发布过程中可以观察副本与事件：

```bash
kubectl -n webapp get pods -l app=webapp -w
kubectl -n webapp describe deployment webapp
```

## 6. 回滚

```bash
# 查看历史版本（Revision 与 change-cause）
kubectl -n webapp rollout history deployment/webapp

# 回滚到上一个版本
kubectl -n webapp rollout undo deployment/webapp

# 回滚到指定版本
kubectl -n webapp rollout undo deployment/webapp --to-revision=2

kubectl -n webapp rollout status deployment/webapp --timeout=180s
```

Deployment 保留最近 5 个 ReplicaSet（`revisionHistoryLimit: 5`），更早的版本无法直接回滚。

## 7. 启用 TLS 与 SESSION_COOKIE_SECURE

### 7.1 准备域名与证书

1. 把 `ingress.yaml` 中的 `webapp.example.com` 全部替换为真实域名；
2. 将域名 DNS 解析到 ingress-nginx 的入口地址（LoadBalancer IP 或节点 IP）；
3. 准备证书，二选一：

**已有证书**：

```bash
kubectl -n webapp create secret tls webapp-tls \
  --cert=fullchain.pem \
  --key=privkey.pem
```

**使用 cert-manager 自动签发**：在 `ingress.yaml` 的 annotations 中取消
`cert-manager.io/cluster-issuer` 注释并填入实际的 ClusterIssuer（如 `letsencrypt-prod`），
同时保留 `tls.secretName: webapp-tls`，cert-manager 会自动创建/续期该 Secret。

### 7.2 打开 Ingress TLS

取消 `ingress.yaml` 中 `tls:` 段与 `nginx.ingress.kubernetes.io/ssl-redirect: "true"` 的注释，
然后重新 apply：

```bash
kubectl apply -k deploy/k8s
kubectl -n webapp get ingress webapp
```

### 7.3 打开 Secure Cookie

确认 HTTPS 已经可以正常访问后，把 `deploy/k8s/configmap.yaml` 中的 `SESSION_COOKIE_SECURE`
改为 `"true"`，再 apply 并重建 Pod（`envFrom` 注入的环境变量不会热更新）：

```bash
# 修改 deploy/k8s/configmap.yaml 后
kubectl apply -k deploy/k8s
kubectl -n webapp rollout restart deployment/webapp
kubectl -n webapp rollout status deployment/webapp --timeout=180s
```

临时验证也可以直接 patch；但下次 `kubectl apply -k` 会用清单里的值覆盖它，
因此记得把 `configmap.yaml` 同步改掉：

```bash
kubectl -n webapp patch configmap webapp-config \
  --type merge -p '{"data":{"SESSION_COOKIE_SECURE":"true"}}'
kubectl -n webapp rollout restart deployment/webapp
```

> **顺序很重要**：必须先启用 TLS，再把 `SESSION_COOKIE_SECURE` 设为 `true`。
> 否则浏览器不会在纯 HTTP 请求中回传会话 Cookie，表现为无法登录或登录后立刻掉线。

## 8. 私有镜像仓库凭证（可选）

如果 ACR 仓库是私有的，先创建 docker-registry Secret：

```bash
kubectl -n webapp create secret docker-registry acr-pull-secret \
  --docker-server=crpi-m67ogm8wgcr0rh38.cn-hangzhou.personal.cr.aliyuncs.com \
  --docker-username='<阿里云账号>' \
  --docker-password='<镜像仓库密码>' \
  --docker-email='<邮箱>'
```

然后取消 `deployment.yaml` 中 `imagePullSecrets` 段的注释并重新 apply。
如果通过 CI 的 ServiceAccount 拉取镜像，也可以给 ServiceAccount 打补丁：

```bash
kubectl -n webapp patch serviceaccount webapp \
  -p '{"imagePullSecrets":[{"name":"acr-pull-secret"}]}'
```

## 9. 环境变量契约

| 变量 | 来源 | 说明 |
| --- | --- | --- |
| `FLASK_CONFIG` | ConfigMap | 配置档，默认 `production` |
| `SECRET_KEY` | Secret | Flask 会话 / CSRF 签名，必填 |
| `DATABASE_URI` | Secret | SQLAlchemy 连接串，必填 |
| `CAPTCHA_SECRET_KEY` | Secret | 验证码签名密钥，必填 |
| `SESSION_COOKIE_SECURE` | ConfigMap | 仅 HTTPS 发送 Cookie，TLS 就绪后置为 `true` |
| `SESSION_LIFETIME_SECONDS` | ConfigMap | 会话有效期（秒） |
| `LOG_LEVEL` | ConfigMap | 应用与 gunicorn 日志级别 |
| `GUNICORN_WORKERS` | ConfigMap | gunicorn worker 数，默认 4 |
| `MAX_CONTENT_LENGTH` | ConfigMap | Flask 请求体上限（字节） |

`production` 配置启动时会强制校验 `SECRET_KEY`、`DATABASE_URI`、`CAPTCHA_SECRET_KEY`，
缺失或仍为占位符会直接启动失败，避免带着默认密钥上线。

## 存储说明

- `pvc.yaml` 默认 `ReadWriteMany`，2 个副本共享 `/app/uploads`。
- 如果 StorageClass 只支持 `ReadWriteOnce`：
  1. 将 `pvc.yaml` 的 `accessModes` 改为 `ReadWriteOnce`；
  2. 将 `deployment.yaml` 的 `replicas` 改为 `1`；
  3. 重新 apply。RWO 卷无法同时挂载到不同节点上的多个 Pod。
- 使用 NFS / NAS 时，导出目录需要允许 uid/gid 10001 写入；部分 CSI 不支持用
  `fsGroup` 递归修改属主，需要在存储侧放行该用户。
- 上传文件是有状态数据，备份/迁移时不要只备份数据库而遗漏 `/app/uploads`：

  ```bash
  kubectl -n webapp exec deploy/webapp -- ls -al /app/uploads
  ```

- 删除命名空间或执行 `kubectl delete -k deploy/k8s` 会删除 PVC，生产环境请先做好备份。

## 网络与安全说明

- `networkpolicy.yaml` 默认拒绝命名空间内所有入站，仅允许 `ingress-nginx` 命名空间访问 5000；
  出站只放行 DNS、MySQL(3306)、HTTPS(443)。需要访问其他外部服务时按同样格式增加规则。
- NetworkPolicy 依赖支持它的 CNI（Calico / Cilium / Antrea 等），flannel 默认不生效。
- 如果 ingress-nginx 不在 `ingress-nginx` 命名空间，请修改 `namespaceSelector`；
  MySQL 的 `0.0.0.0/0` 建议收窄为数据库实际网段。若 MySQL 也部署在 `webapp` 命名空间，
  默认拒绝入站会挡住它，需要为数据库 Pod 增加允许 webapp 访问 3306 的入站策略。
- 部分 CNI 会把 kubelet 探针请求也纳入 NetworkPolicy；如果 Pod 一直探针失败，
  需要在策略中额外放行节点网段。
- 应用使用 `request.remote_addr` 记录登录 IP / 在线用户；ingress-nginx 只透传
  `X-Forwarded-For`，若应用侧未启用 ProxyFix，后端通常看到的是 ingress Pod 的 IP。
- 容器以非 root（uid 10001）运行，根文件系统只读，`/tmp` 与 `/app/uploads` 是仅有的可写目录；
  ServiceAccount 不挂载 Token，也没有任何 RBAC 权限。
- Health 接口：`/health/live` 只检查进程存活；`/health/ready` 会执行 `SELECT 1`，数据库不可用时返回 503。
