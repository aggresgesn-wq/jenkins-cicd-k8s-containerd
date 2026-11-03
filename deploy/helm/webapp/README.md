> 可选安装方案。主发布使用 Kustomize，见 [发布规程](../../../docs/RELEASE-RUNBOOK.md)。禁止 Helm 与 Kustomize 同时管理同一 release 的资源。

# webapp Helm Chart

把 `deploy/k8s` 的清单参数化为一个可复用的 Chart（Deployment / Service / Ingress / HPA / PDB / PVC / NetworkPolicy / ServiceAccount）。

## 安装

```bash
kubectl create namespace webapp --dry-run=client -o yaml | kubectl apply -f -

kubectl -n webapp create secret generic webapp-secret \
  --from-literal=SECRET_KEY="$(openssl rand -hex 32)" \
  --from-literal=CAPTCHA_SECRET_KEY="$(openssl rand -hex 16)" \
  --from-literal=DATABASE_URI="mysql+mysqlconnector://webapp:REPLACE_ME@mysql:3306/authbase?charset=utf8mb4" \
  --dry-run=client -o yaml | kubectl apply -f -

helm upgrade --install webapp deploy/helm/webapp \
  --namespace webapp \
  --set-string image.repository="registry.example.com/webapp" \
  --set-string image.tag="sha256-REPLACE_ME" \
  --set ingress.host="app.example.com"
```

把 `REPLACE_ME` 替换为真实值。`fullnameOverride` 固定为 `webapp`，仅用于稳定 Deployment/Service 名称；后续镜像更新必须继续通过 Helm，不能使用 `kubectl set image` 制造配置漂移。

## 常用参数

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `image.repository` | ACR 仓库地址 | 镜像仓库 |
| `image.tag` | Chart appVersion | 必须在安装/升级时覆盖为不可变版本 |
| `existingSecret` | `webapp-secret` | 敏感配置来源，不写入 values |
| `config.*` | 见 values.yaml | 非敏感环境变量，写入 ConfigMap |
| `persistence.enabled/size` | `true` / `5Gi` | 头像上传目录 |
| `autoscaling.*` | 2–6 副本，CPU 70% | 需要 metrics-server |
| `ingress.host` | `webapp.example.com` | 访问域名 |
| `networkPolicy.ingressNamespace` | `ingress-nginx` | 允许入站的命名空间 |

## 升级与回滚

```bash
helm upgrade webapp deploy/helm/webapp -n webapp --reuse-values --set-string image.tag=sha256-REPLACE_WITH_DIGEST
helm history webapp -n webapp
helm rollback webapp REVISION_NUMBER -n webapp
```

## 与 kustomize 的关系

- `deploy/k8s`：项目主发布方式，按 staging/production overlay 交付；
- `deploy/helm/webapp`：独立的可选安装示例，不是主发布链路；
- 两者必须二选一；已经由一种工具创建的 release，不得直接切换另一种工具接管。
