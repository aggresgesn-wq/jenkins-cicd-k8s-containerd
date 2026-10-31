# jenkins-gitea-k8s-containerd

> 仓库名中的 `gitea` 属于历史命名。当前代码、流水线、Webhook 与提交状态回写**默认使用 GitHub**；如需内网自建代码托管，可按 [deploy/gitea/README.md](deploy/gitea/README.md) 在 Linux 上部署 Gitea 并切换 Webhook。

面向 Kubernetes 的 CI/CD 示例仓库：代码托管在 GitHub，Jenkins 在集群内动态创建构建 Pod，使用 kaniko 构建镜像，发布到 containerd 运行时集群。仓库内置一个可运行的 Flask + Vue 后台权限系统，用来演示从提交、测试、扫描、构建、推送到测试/生产发布与回滚的完整链路。

![系统架构](docs/images/architecture.png)

> 图中构建阶段以 Rootless BuildKit 表示无特权构建；当前实现使用 kaniko，二者都不使用 privileged 容器、不挂载 containerd.sock。

图中发布通道以 Helm Upgrade/GitOps 表示；当前示例使用 `deploy/k8s` 清单与 Jenkins 部署阶段实现等价的发布/回滚，可平滑替换为 Helm。

- 仓库地址：<https://github.com/aggresgesn-wq/jenkins-gitea-k8s-containerd>
- 应用目录：[webapp/](webapp)
- 生产启动方式：gunicorn，入口 `webapp/wsgi.py:app`，容器端口 `5000`

## 项目定位

| 维度 | 说明 |
| --- | --- |
| 目标 | 一套可落地、可照着复现的 Jenkins + GitHub + K8s CI/CD 参考实现 |
| 示例应用 | Flask 2.2 + Vue 2 后台权限系统，RBAC、验证码、操作日志、健康检查 |
| 构建 | Jenkins Pipeline + kaniko，不依赖 Docker daemon、privileged 容器或宿主机 containerd socket |
| 部署 | `deploy/k8s` 清单，namespace 为 `webapp` |
| 运行时 | containerd + gunicorn，健康检查 `/health/live`、`/health/ready` |
| 安全基线 | Session + 双提交 Cookie CSRF、RBAC、非 root/只读根文件系统，详见 [SECURITY.md](SECURITY.md) |

## 架构总览

```text
GitHub ──webhook──> Jenkins ──kaniko──> 镜像仓库（ACR）
                      │                      │
                      └── kubectl/清单 ──> K8s（containerd）──> gunicorn ──> MySQL 8
```

目录结构：

```text
.
├── README.md
├── SECURITY.md
├── CONTRIBUTING.md
├── docs/
│   ├── ARCHITECTURE.md        # 组件、请求链路、认证时序、数据模型、CI/CD
│   ├── DEPLOYMENT.md          # 环境准备、Secret、数据库、构建、部署、回滚、排障
│   └── images/architecture.png # 系统架构图
├── deploy/
│   ├── k8s/                   # 原生清单：Deployment/Service/Ingress/HPA/PDB/PVC/NetworkPolicy/MySQL/备份
│   ├── helm/webapp/           # 同一套资源的 Helm Chart（多环境发布）
│   ├── jenkins/               # Jenkins Helm values 与安装/插件/备份说明
│   └── monitoring/            # Prometheus 抓取配置、告警规则、Grafana 仪表盘
└── webapp/
    ├── app/                   # Flask：models/routes/templates/security/metrics
    ├── ui/                    # Vue 2.7 + Element UI 前端（含 package-lock.json）
    ├── docker/                # mirror.py（国内镜像地址查询工具）
    ├── scripts/               # reset_password.py、check_default_passwords.py
    ├── tests/                 # 后端测试（pytest）
    ├── db.sql                 # 初始化表结构与种子数据
    ├── dockerfile             # 多阶段构建：Node 构建前端 + Python 运行后端
    ├── Jenkinsfile            # 流水线定义
    ├── pyproject.toml         # Python 依赖（uv）
    ├── wsgi.py                # gunicorn 入口
    └── start.py               # 本地开发入口
```

技术栈：

| 层 | 技术 |
| --- | --- |
| 后端 | Flask 2.2、Flask-Login、Flask-SQLAlchemy、Flask-Simple-Captcha、MySQL 8 |
| 前端 | Vue 2.7、Element UI、Vuex、Vue Router、Axios 1.x |
| 运行 | gunicorn（`wsgi.py:app`），容器端口 5000，`/metrics` 暴露 Prometheus 指标 |
| 交付 | Jenkins + kaniko、GitHub（Webhook + Commit Status）、Kubernetes + containerd、Helm/Kustomize |

## 快速开始

以下命令默认在 Windows PowerShell 7 中执行。开始前请准备：Python 3.11 + uv、Node.js 18 + npm、MySQL 8.0、Docker（可选）、kubectl 与可用的 K8s 集群。

### 路径一：本地运行后端与前端

```powershell
# 目录：E:\CICD\webapp（PowerShell；source 为 mysql 客户端命令）
mysql -h 127.0.0.1 -u root -p -e "CREATE DATABASE IF NOT EXISTS authbase CHARACTER SET utf8mb4;"
mysql -h 127.0.0.1 -u root -p authbase -e "source db.sql"
```

```powershell
# 目录：E:\CICD\webapp（PowerShell）
uv sync
$env:FLASK_CONFIG = "development"
$env:SECRET_KEY = "dev-only-replace-me"
$env:DATABASE_URI = "mysql+mysqlconnector://root:REPLACE_ME@127.0.0.1:3306/authbase?charset=utf8mb4"
$env:CAPTCHA_SECRET_KEY = "dev-only-replace-me"
uv run python start.py
```

```powershell
# 目录：E:\CICD\webapp\ui（PowerShell）
npm install --registry=https://registry.npmmirror.com
npm run dev
```

浏览器访问 <http://localhost>。**种子数据不包含可用密码**（`db.sql` 中 `admin` 的密码哈希已置为无效值），首次启动前必须生成管理员密码：

```powershell
# 目录：E:\CICD\webapp（PowerShell）
python scripts/reset_password.py --username admin
# 输出示例：已重置用户 admin 的密码：Xk9#mP2vQ7...
```

开发服务器默认监听 80 端口，并将 API 请求代理到 `127.0.0.1:5000`；用上一步生成的密码登录，并立即在“个人中心”改密。存量环境可用 `python scripts/check_default_passwords.py` 自检是否仍存在弱口令。

### 路径二：Docker 构建并运行

```powershell
# 目录：E:\CICD\webapp（PowerShell）
docker build -f dockerfile -t webapp:local .
docker run --rm -p 5000:5000 `
  -e FLASK_CONFIG=production `
  -e SECRET_KEY="replace-with-random-32-bytes" `
  -e DATABASE_URI="mysql+mysqlconnector://webapp:REPLACE_ME@host.docker.internal:3306/authbase?charset=utf8mb4" `
  -e CAPTCHA_SECRET_KEY="replace-with-random-32-bytes" `
  webapp:local

# 首次部署：在容器内生成管理员密码（或对已有数据库执行）
docker run --rm -e DATABASE_URI="mysql+mysqlconnector://webapp:REPLACE_ME@host.docker.internal:3306/authbase?charset=utf8mb4" `
  webapp:local python scripts/reset_password.py --username admin

curl.exe -fsS http://127.0.0.1:5000/health/live
```

### 路径三：部署到 Kubernetes

先按 [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) 创建 Secret 并初始化数据库，再执行：

```powershell
# 目录：E:\CICD（PowerShell）
kubectl apply -f deploy/k8s/
kubectl -n webapp rollout status deployment/webapp --timeout=180s
kubectl -n webapp port-forward svc/webapp 8080:80

# 首次初始化管理员密码（种子数据不含可用密码）
kubectl -n webapp exec deploy/webapp -- python scripts/reset_password.py --username admin
```

浏览器访问 <http://localhost:8080>；生产环境通过 Ingress 域名访问。

同一套资源也提供了 Helm Chart，多环境发布时更合适：

```powershell
# 目录：E:\CICD（PowerShell）
helm upgrade --install webapp deploy/helm/webapp -n webapp --create-namespace `
  --set image.tag="$(git rev-parse --short HEAD)" --set ingress.host="app.example.com"
```

监控与告警见 [deploy/monitoring/README.md](deploy/monitoring/README.md)，Jenkins 安装与配置见 [deploy/jenkins/README.md](deploy/jenkins/README.md)。

## 镜像加速说明

基础镜像统一取自[渡渡鸟镜像同步站](https://docker.aityp.com)，同步到华为云 SWR，国内网络可直接拉取，无需额外配置 Docker 加速器。地址规则：

```text
swr.cn-north-4.myhuaweicloud.com/ddn-k8s/<原始仓库>/<镜像>:<tag>
```

| 原始镜像 | 国内可用地址 |
| --- | --- |
| `python:3.11` | `swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.11` |
| `node:18` | `swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/node:18` |
| `ubuntu:20.04` | `swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/ubuntu:20.04` |
| `moby/buildkit:v0.31.1` | `swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/moby/buildkit:v0.31.1` |

查询镜像地址：

```powershell
# 目录：E:\CICD\webapp（PowerShell）
python docker/mirror.py python:3.11 node:18 ubuntu:20.04
python docker/mirror.py ghcr.io/containerd/nerdctl:latest --platform linux/arm64 --json
```

未同步的镜像可到 <https://docker.aityp.com/manage/add> 提交同步请求。`webapp/dockerfile` 的 `UI_IMAGE`、`BASE_IMAGE` 已默认使用上述国内地址，需要官方镜像时用 `--build-arg` 覆盖。

## 安全基线摘要

- **认证**：基于 Flask Session 的 Cookie 会话，`HttpOnly` + `SameSite=Lax`，生产环境启用 `Secure`。
- **CSRF**：登录成功后下发 `XSRF-TOKEN` Cookie，前端所有写请求携带 `X-XSRF-TOKEN` 头，服务端做双提交 Cookie 校验。
- **授权**：RBAC（用户-角色-资源），角色 `ROLEKEY` 为 `superadmin` / `admin` / `readonly`，接口通过 `@permission('system:user:list')` 等权限码校验；未登录返回 HTTP 401，无权限返回 HTTP 403。
- **密钥**：`SECRET_KEY`、`DATABASE_URI`、`CAPTCHA_SECRET_KEY` 等只通过环境变量注入，生产使用 K8s Secret 与 Jenkins Credentials，禁止入库。
- **默认口令**：`db.sql` 种子账号不含可用密码，首次启动前必须运行 `scripts/reset_password.py`；`scripts/check_default_passwords.py` 可巡检存量环境。
- **容器**：非 root 运行、只读根文件系统、无 privileged、不挂载宿主机 containerd socket。
- **其他**：登录限流与锁定、验证码、上传类型/大小校验、依赖与镜像安全扫描、审计日志脱敏（密码/Token 不落库）。

完整控制清单与上线检查表见 [SECURITY.md](SECURITY.md)。

## 文档索引

| 文档 | 内容 |
| --- | --- |
| [README.md](README.md) | 项目定位、快速开始、镜像加速、安全摘要 |
| [webapp/README.md](webapp/README.md) | 应用功能、本地开发、环境变量、Docker 构建、常见问题 |
| [SECURITY.md](SECURITY.md) | 漏洞上报、密钥管理、安全控制清单、部署检查清单 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 分支与提交规范、代码风格、测试要求、PR 检查清单 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 组件图、请求链路、认证时序、数据模型、CI/CD 流程 |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | 环境准备、Secret、数据库、构建、K8s/Helm 部署、Jenkins/GitHub 接入、备份恢复、排障 |
| [deploy/jenkins/README.md](deploy/jenkins/README.md) | Jenkins 安装（Helm/Docker/包管理）、插件源、K8s Cloud、凭据、备份升级 |
| [deploy/gitea/README.md](deploy/gitea/README.md) | Gitea 在 Linux 上的安装（二进制+systemd / Docker / Helm）、初始化、反代、Jenkins 对接、备份升级 |
| [docs/IMAGES.md](docs/IMAGES.md) | 镜像清单：流水线、构建、部署与运维组件统一走渡渡鸟镜像站的地址与校验方式 |
| [docs/BRANCH-PROTECTION.md](docs/BRANCH-PROTECTION.md) | main 分支保护、`jenkins/ci` 必需检查与生产发布限制 |
| [deploy/containerd/README.md](deploy/containerd/README.md) | containerd 安装脚本、`config.toml`（SystemdCgroup/CRI）、kubelet cgroup 配置与节点校验 |
| [deploy/jenkins/jcasc/jenkins.yaml](deploy/jenkins/jcasc/jenkins.yaml) | Jenkins JCasC 示例（Kubernetes Cloud、PATH、location）与 Job DSL |
| [deploy/monitoring/README.md](deploy/monitoring/README.md) | Prometheus 抓取、告警规则、Grafana 仪表盘、日志与审计脱敏 |
| [deploy/helm/webapp/README.md](deploy/helm/webapp/README.md) | Helm Chart 参数、安装升级与回滚 |
| [docs/SCOPE.md](docs/SCOPE.md) | 功能范围、若依模板遗留模块、技术债与清理计划 |

## 许可证与来源声明

- `webapp/` 基于上游 **AuthBase** 项目（<https://gitee.com/zhujf21st/authbase>）二次开发，沿用其 **Apache License 2.0**，许可证全文见 [webapp/LICENSE](webapp/LICENSE)。
- Jenkins、GitHub、Kubernetes、kaniko、渡渡鸟镜像同步站等第三方组件与镜像分别遵循其各自许可证，使用前请自行确认。
- 本仓库的 CI/CD 配置与文档为示例性质，不附带任何形式的担保；用于生产前请结合组织安全规范进行评估。

## Roadmap

以下事项尚未完成，欢迎通过 Issue / PR 参与：

- [ ] **前端框架升级**：Vue 2 已进入 EOL，当前停留在 2.7.16（2.x 最后一个维护版本），计划迁移到 Vue 3 + Vite + Element Plus。
- [ ] **数据库迁移**：引入 Flask-Migrate / Alembic，取代手工导入 `db.sql` 的初始化方式，并纳入 CI 校验。
- [ ] **可观测性增强**：已提供 `/metrics`、告警规则与 Grafana 面板；后续补充 OpenTelemetry 链路追踪与日志集中化（Loki/ELK）。
- [ ] **供应链安全**：镜像 SBOM、签名（cosign）与部署准入校验。
