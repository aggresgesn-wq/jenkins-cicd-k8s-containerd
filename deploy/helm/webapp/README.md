> 可选安装方案。主发布使用 Kustomize，见 [发布规程](../../../docs/RELEASE-RUNBOOK.md)。禁止 Helm 与 Kustomize 同时管理同一 release 的资源。

# webapp Helm Chart

把 `deploy/k8s` 的清单参数化为一个可复用的 Chart（Deployment / Service / Ingress / HPA / PDB / PVC / NetworkPolicy / ServiceAccount）。

## 安装

```bash
kubectl create namespace webapp

kubectl -n webapp create secret generic webapp-secret \
  --from-literal=SECRET_KEY="$(openssl rand -hex 32)" \
  --from-literal=CAPTCHA_SECRET_KEY="$(openssl rand -hex 16)" \
  --from-literal=DATABASE_URI="mysql+mysqlconnector://webapp:REPLACE_ME@mysql:3306/authbase?charset=utf8mb4"

helm upgrade --install webapp deploy/helm/webapp \
  --namespace webapp \
  --set image.tag="$(git rev-parse --short HEAD)" \
  --set ingress.host="app.example.com"
```

`fullnameOverride` 固定为 `webapp`，因此 Deployment/Service 名称与 `webapp/Jenkinsfile` 中的 `kubectl set image deployment/webapp` 保持一致。

## 常用参数

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `image.repository` | ACR 仓库地址 | 镜像仓库 |
| `image.tag` | Chart appVersion | 建议在 CI 中覆盖为 git short sha |
| `existingSecret` | `webapp-secret` | 敏感配置来源，不写入 values |
| `config.*` | 见 values.yaml | 非敏感环境变量，写入 ConfigMap |
| `persistence.enabled/size` | `true` / `5Gi` | 头像上传目录 |
| `autoscaling.*` | 2–6 副本，CPU 70% | 需要 metrics-server |
| `ingress.host` | `webapp.example.com` | 访问域名 |
| `networkPolicy.ingressNamespace` | `ingress-nginx` | 允许入站的命名空间 |

## 升级与回滚

```bash
helm upgrade webapp deploy/helm/webapp -n webapp --reuse-values --set image.tag=<sha>
helm history webapp -n webapp
helm rollback webapp <revision> -n webapp
```

## 与 kustomize 的关系

- `deploy/k8s`：完整清单，适合 `kubectl apply -k` 直接部署与教学对照；
- `deploy/helm/webapp`：同一套资源的参数化版本，适合多环境发布；
- 两者二选一，避免同时管理同一批对象。
