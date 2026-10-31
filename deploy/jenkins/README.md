# Jenkins 安装与配置

本目录提供 Jenkins Controller 的 Helm values 与落地说明，配合 `webapp/Jenkinsfile` 与 `deploy/k8s/jenkins-rbac.yaml` 使用。

> 界面截图与逐项配置对照见 [docs/JENKINS-UI.md](../../docs/JENKINS-UI.md)（登录、新建流水线、SCM 配置、插件管理、历史构建对比）。

## 1. 安装方式

### 方式 A：Helm（推荐，K8s 内）

```bash
# 目录：E:\CICD
helm repo add jenkins https://charts.jenkins.io
helm repo update

kubectl create namespace jenkins
kubectl -n jenkins create secret generic jenkins-admin \
  --from-literal=jenkins-admin-user=admin \
  --from-literal=jenkins-admin-password="$(openssl rand -base64 24)"

helm upgrade --install jenkins jenkins/jenkins \
  --namespace jenkins \
  --values deploy/jenkins/values.yaml \
  --wait

kubectl -n jenkins get pods
kubectl -n jenkins port-forward svc/jenkins 8080:8080
```

初始管理员密码：

```bash
kubectl -n jenkins exec svc/jenkins -c jenkins -- \
  cat /run/secrets/chart-admin-password
```

### 方式 B：Docker（本地验证）

```bash
docker run -d --name jenkins -p 8080:8080 -p 50000:50000 \
  -v jenkins_home:/var/jenkins_home \
  jenkins/jenkins:lts-jdk17
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

### 方式 C：Linux 包管理

```bash
sudo wget -O /etc/yum.repos.d/jenkins.repo https://pkg.jenkins.io/redhat-stable/jenkins.repo
sudo rpm --import https://pkg.jenkins.io/redhat-stable/jenkins.io.key
sudo yum install -y java-17-openjdk jenkins
sudo systemctl enable --now jenkins
sudo cat /var/lib/jenkins/secrets/initialAdminPassword
```

## 2. 插件与插件源

`values.yaml` 的 `controller.installPlugins` 已包含核心插件（Kubernetes、Pipeline、Git、GitHub、JCasC、Credentials Binding、JUnit、DingTalk 等）。

国内网络安装插件失败时，把升级站点换到镜像：

1. *Manage Jenkins → Plugins → Advanced*。
2. 将 Update Site 改为 `https://mirrors.tuna.tsinghua.edu.cn/jenkins/updates/update-center.json`（或 `https://mirror.esuni.jp/jenkins/updates/update-center.json`）。
3. 保存后重启 Jenkins，再次安装。

命令行/容器方式可预先修改 `$JENKINS_HOME/hudson.model.UpdateCenter.xml` 中的 `url` 字段。

## 3. 配置 Kubernetes 动态 Agent

*Manage Jenkins → Clouds → New cloud → Kubernetes*：

| 项 | 值 |
| --- | --- |
| Kubernetes URL | `https://kubernetes.default.svc` |
| Kubernetes Namespace | `jenkins` |
| Credentials | 集群内留空（使用 Pod 的 ServiceAccount）或选择 kubeconfig 凭据 |
| Jenkins URL | `https://jenkins.example.com/` |
| Pod Labels | `jenkins=slave` |
| Service Account | `jenkins-deployer`（见 `deploy/k8s/jenkins-rbac.yaml`） |

构建 Pod 的容器（python / node / kaniko / kubectl）由 `webapp/Jenkinsfile` 内嵌的 Pod 模板定义，**不使用 privileged、不挂载 containerd.sock**。

部署权限：在集群中应用 RBAC 清单，让构建 Pod 只能滚动更新 `webapp` 命名空间的 Deployment：

```bash
kubectl apply -f deploy/k8s/jenkins-rbac.yaml
```

> `jenkins-rbac.yaml` 中的 ServiceAccount 位于 `jenkins` 命名空间，Role/RoleBinding 位于 `webapp` 命名空间；如果 Jenkins 安装在其他命名空间，请同步修改。

## 4. 凭据

*Manage Jenkins → Credentials → System → Global credentials*：

| ID | 类型 | 用途 |
| --- | --- | --- |
| `acr-credentials` | Username with password | 推送/拉取 ACR 镜像 |
| `github-token` | Secret text | 回写 GitHub Commit Status（`repo:status`） |
| `github-webhook-secret` | Secret text | 校验 GitHub Webhook 签名 |
| `dingtalk-webhook` | Secret text | 可选：构建通知（完整 Webhook 地址） |
| `kubeconfig` | Secret file | 集群外部署时使用 |

## 5. GitHub Webhook

仓库 → *Settings → Webhooks → Add webhook*：

- Payload URL：`https://jenkins.example.com/github-webhook/`（末尾斜杠必需）
- Content type：`application/json`
- Secret：与 `github-webhook-secret` 一致
- Events：*Just the push event*

Job 触发勾选 *GitHub hook trigger for GITScm polling*，Job 类型为 *Pipeline script from SCM*，Script Path 为 `webapp/Jenkinsfile`。

更完整的步骤（Token 权限、提交状态、排障）见 [docs/DEPLOYMENT.md](../../docs/DEPLOYMENT.md) 第 7 节。

## 6. 备份与恢复

`JENKINS_HOME` 包含 `jobs/`、`credentials.xml`、`secrets/`、`plugins/`、`nodes/`、`users/` 等，务必整体备份（PDB/JCasC 也无法替代凭据与密钥）：

```bash
# 备份（PVC 快照或拷贝）
kubectl -n jenkins exec jenkins-0 -c jenkins -- tar czf - /var/jenkins_home \
  > jenkins-home-$(date +%Y%m%d).tar.gz

# 恢复
kubectl -n jenkins cp jenkins-home-20260101.tar.gz jenkins-0:/tmp/
kubectl -n jenkins exec jenkins-0 -c jenkins -- \
  tar xzf /tmp/jenkins-home-20260101.tar.gz -C /
kubectl -n jenkins rollout restart statefulset/jenkins
```

云上更推荐对存储卷做定时快照，并定期在测试环境演练恢复。

## 7. 升级与卸载

```bash
helm repo update
helm upgrade jenkins jenkins/jenkins -n jenkins -f deploy/jenkins/values.yaml --wait
helm history jenkins -n jenkins
helm rollback jenkins <revision> -n jenkins

helm uninstall jenkins -n jenkins
kubectl delete pvc -n jenkins -l app.kubernetes.io/instance=jenkins   # 谨慎：删除历史数据
```

## 8. 常见问题

| 现象 | 原因与处理 |
| --- | --- |
| 初始密码找不到 | Helm：`/run/secrets/chart-admin-password`；包安装：`/var/lib/jenkins/secrets/initialAdminPassword` |
| 插件安装卡住/失败 | 切换插件源（见第 2 节），或离线下载 `.hpi` 后 *Advanced → Upload Plugin* |
| `mvn/npm/kubectl: command not found` | Jenkins 进程的 PATH 不含工具路径；在 *Global Properties → Environment variables* 补 PATH，或在 Pod 模板中直接使用带工具的镜像 |
| Pod 一直 Pending | 检查节点资源、`nodeSelector/tolerations`、ServiceAccount 是否存在 |
| Webhook 返回 403/404 | Payload URL 末尾斜杠、Jenkins URL 配置、GitHub 插件是否安装；查看 *Recent Deliveries* |
| 构建无法访问集群 API | 未绑定 `jenkins-deployer` ServiceAccount 或 Role/RoleBinding 命名空间不匹配 |
