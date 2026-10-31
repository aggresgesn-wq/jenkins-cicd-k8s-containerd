# Webapp：Flask + Vue 后台权限管理系统

`webapp/` 是 [jenkins-gitea-k8s-containerd](https://github.com/aggresgesn-wq/jenkins-gitea-k8s-containerd) 的内置示例应用，用于演示一个真实前后端项目如何被 Jenkins 测试、扫描、构建并部署到 Kubernetes。后端基于 Flask 2.2，前端基于 Vue 2 + Element UI，生产使用 gunicorn 运行。

> 本项目基于上游 AuthBase（<https://gitee.com/zhujf21st/authbase>）二次开发，沿用 Apache License 2.0，详见 [LICENSE](LICENSE)。

## 功能列表

- 登录 / 退出：账号密码 + 图形验证码，基于 Flask Session 的服务端会话。
- 用户管理：查询、新增、修改、删除、启停、重置密码、分配角色与机构。
- 角色管理：角色 CRUD、资源授权、用户授权、数据范围（机构）配置。
- 资源管理：目录 / 菜单 / 按钮三级资源树，按权限码控制接口与前端按钮。
- 机构与配置：树形机构维护、按机构过滤，以及参数、字典类型与字典数据管理。
- 监控与个人中心：在线用户、登录历史、操作日志、服务监控，以及资料、头像与改密。
- 交付能力：`/health/live`、`/health/ready` 健康检查，多阶段 Docker 构建，Jenkins + K8s 发布。

## 技术栈

| 层次 | 技术 |
| --- | --- |
| 后端框架 | Flask 2.2、Flask-Login、Flask-SQLAlchemy、Flask-Simple-Captcha |
| 数据库 | MySQL 8.0+（机构查询使用递归 CTE，必须 8.0 及以上） |
| 前端 | Vue 2.7（2.x 最终维护版本）、Element UI 2.15、Vuex、Vue Router、Axios 1.x |
| 运行 | gunicorn（`wsgi.py:app`），容器端口 5000 |
| 构建 | uv、npm、多阶段 Dockerfile、kaniko（CI） |

## 目录结构

```text
webapp/
├── app/                # Flask：models / routes / templates
├── ui/                 # Vue 2 + Element UI
├── docker/             # mirror.py（镜像地址查询工具）
├── tests/              # 后端测试
├── db.sql              # 表结构 + 种子数据
├── dockerfile          # 多阶段构建入口
├── Jenkinsfile         # Jenkins 流水线
├── config.py           # 环境变量配置
├── pyproject.toml      # Python 依赖
├── wsgi.py             # gunicorn 入口
└── start.py            # 本地开发入口
```

## 环境要求

- Python 3.11 + [uv](https://docs.astral.sh/uv/)；Node.js 18 + npm；MySQL 8.0+（`utf8mb4`）；Docker 24+（可选）。
- 本地端口：后端 `5000`，前端开发服务器默认 `80`。

## 本地开发

### 1. 初始化数据库

```powershell
# 目录：E:\CICD\webapp（PowerShell；source 为 mysql 客户端命令）
mysql -h 127.0.0.1 -u root -p -e "CREATE DATABASE IF NOT EXISTS authbase CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;"
mysql -h 127.0.0.1 -u root -p authbase -e "source db.sql"
```

`db.sql` 只包含表结构与种子数据，不包含 `CREATE DATABASE`，因此必须先建库。数据库名可按需调整，但要保持与 `DATABASE_URI` 一致。

### 2. 启动后端（uv）

```powershell
# 目录：E:\CICD\webapp（PowerShell）
uv sync
$env:FLASK_CONFIG = "development"
$env:SECRET_KEY = "dev-only-replace-me"
$env:DATABASE_URI = "mysql+mysqlconnector://root:REPLACE_ME@127.0.0.1:3306/authbase?charset=utf8mb4"
$env:CAPTCHA_SECRET_KEY = "dev-only-replace-me"
uv run python start.py
```

访问 <http://127.0.0.1:5000/health/live> 应返回成功。默认管理员为 `admin`，初始密码由 `db.sql` 种子数据决定；首次登录后请立即在“个人中心”修改密码。

### 3. 启动前端

```powershell
# 目录：E:\CICD\webapp\ui（PowerShell）
npm install --registry=https://registry.npmmirror.com
npm run dev
```

浏览器访问 <http://localhost>。开发服务器会把 API 请求代理到 `127.0.0.1:5000`；80 端口被占用时可改用 `$env:port=8080; npm run dev`。

## 环境变量

所有运行配置均通过环境变量注入，不要修改代码中的默认值，也不要提交 `.env` 文件。

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `FLASK_CONFIG` | `production` | 配置档：`production` / `development` / `testing`；本地开发用 `development` |
| `SECRET_KEY` | 无（必须设置） | Flask Session 与 CSRF 签名密钥；生产使用至少 32 字节随机值，变更后所有会话失效 |
| `DATABASE_URI` | 无（必须设置） | SQLAlchemy 连接串，如 `mysql+mysqlconnector://user:pass@host:3306/authbase?charset=utf8mb4` |
| `CAPTCHA_SECRET_KEY` | 无（必须设置） | 验证码签名密钥；多副本必须一致，否则验证码会随机校验失败 |
| `SESSION_COOKIE_SECURE` | `false` | 为 `true` 时 Cookie 仅通过 HTTPS 发送；生产环境必须为 `true` |
| `SESSION_LIFETIME_SECONDS` | `28800` | 会话有效期（秒），默认 8 小时 |
| `LOG_LEVEL` | `INFO` | 日志级别：`DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `GUNICORN_WORKERS` | `4` | gunicorn worker 数，建议 `2 × CPU 核数 + 1` |
| `MAX_CONTENT_LENGTH` | `5242880` | 请求体上限（字节），默认 5 MiB，同时约束上传大小 |

`DATABASE_URI` 中的密码如含 `@`、`:`、`/` 等字符，必须做 URL 编码，否则连接串会被错误解析。

## 运行与测试

```powershell
# 目录：E:\CICD\webapp（PowerShell）
$env:GUNICORN_WORKERS = "4"
uv run --with gunicorn gunicorn -w "$env:GUNICORN_WORKERS" -b 0.0.0.0:5000 --graceful-timeout 30 wsgi:app
```

```powershell
# 目录：E:\CICD\webapp（PowerShell）
curl.exe -fsS http://127.0.0.1:5000/health/live
curl.exe -fsS http://127.0.0.1:5000/health/ready
uv run --with pytest python -m pytest tests -q
uv run --with ruff ruff check .
npm --prefix ui run lint
npm --prefix ui run build:prod
```

测试使用 `testing` 配置，不应连接生产数据库。新增接口必须补充权限矩阵测试，要求见 [CONTRIBUTING.md](../CONTRIBUTING.md)。

## Docker 构建

```powershell
# 目录：E:\CICD\webapp（PowerShell）
docker build -f dockerfile -t webapp:local .
```

构建完成后用环境变量注入配置并运行，容器端口为 `5000`；完整运行示例见根目录 [README.md](../README.md) 的“快速开始”。

`dockerfile` 为多阶段构建：第一阶段用 Node 安装依赖并执行 `npm run build:prod`，第二阶段把前端产物复制到 `app/static/`，再由 gunicorn 在 `5000` 端口提供服务。基础镜像通过 `UI_IMAGE`、`BASE_IMAGE` 两个 build ARG 控制，默认值见下一节。

## 基础镜像加速（国内）

项目构建用的基础镜像统一取自[渡渡鸟镜像同步站](https://docker.aityp.com)：该站把 `docker.io`、`ghcr.io`、`gcr.io`、`quay.io`、`registry.k8s.io` 等仓库的镜像同步到华为云 SWR，国内网络可以直接拉取，不必再单独配置 Docker 加速器。

地址规则：

```text
swr.cn-north-4.myhuaweicloud.com/ddn-k8s/<原始仓库>/<镜像>:<tag>
```

| 原始镜像 | 国内可用地址 |
| --- | --- |
| `python:3.11` | `swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.11` |
| `node:18` | `swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/node:18` |
| `ubuntu:20.04` | `swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/ubuntu:20.04` |
| `moby/buildkit:v0.31.1` | `swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/moby/buildkit:v0.31.1` |
| `ghcr.io/containerd/nerdctl:latest` | `swr.cn-north-4.myhuaweicloud.com/ddn-k8s/ghcr.io/containerd/nerdctl:latest` |

没有同步过的镜像，可以先到站点搜索，或提交同步请求：<https://docker.aityp.com/manage/add>，同步完成后再按上面的规则拼地址。

### 查询镜像地址

`docker/mirror.py` 封装了站点的公开 API（<https://docker.aityp.com/api/v1/image>），输入原始镜像名即可得到国内地址，只依赖 Python 标准库：

```bash
# 目录：E:\CICD\webapp
python docker/mirror.py python:3.11 node:18 ubuntu:20.04
# docker.io/python:3.11 -> swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.11

python docker/mirror.py ghcr.io/containerd/nerdctl:latest --platform linux/arm64 --json
```

查询不到时脚本会按规则拼出兜底地址，并提示到站点提交同步。

### 构建时更换基础镜像

`dockerfile` 的基础镜像做成了 build ARG，默认就是上面的国内地址，需要官方镜像时覆盖即可：

```powershell
# 目录：E:\CICD\webapp（PowerShell）
docker build -f dockerfile `
  --build-arg UI_IMAGE=node:18 `
  --build-arg BASE_IMAGE=python:3.11 `
  -t webapp:dev .
```

## 常见问题

- **接口返回 401**：未登录或会话已过期。检查浏览器是否保存了 `session` Cookie、是否跨域、`SECRET_KEY` 是否在重启后发生变化。
- **接口返回 403**：已登录但缺少权限码。检查角色是否启用、角色是否绑定对应资源，以及资源 `PERMS` 是否与 `@permission(...)` 一致。
- **登录提示验证码错误**：确认 `CAPTCHA_SECRET_KEY` 在重启/多副本间保持一致；服务器时间偏差过大也会导致验证码过期。
- **数据库连接失败**：确认 MySQL 8.0+、账号密码与 `DATABASE_URI` 一致、密码已做 URL 编码，且容器/Pod 能解析数据库主机名。
- **页面提示请求体过大（413）**：调整 `MAX_CONTENT_LENGTH`，并检查 Nginx Ingress 的 `proxy-body-size`。
- **拉取基础镜像失败**：用 `docker/mirror.py` 查询国内地址，或到渡渡鸟镜像同步站提交同步请求。

## 安全注意事项

1. **默认账号必须改密**：首次使用 `admin` 登录后立即修改密码；生产部署前应替换 `db.sql` 中的种子密码，或增加首次登录强制改密。
2. **密钥不入库**：`SECRET_KEY`、`DATABASE_URI`、`CAPTCHA_SECRET_KEY` 只通过环境变量或 K8s Secret 注入，禁止写入代码、镜像、日志或 Git。
3. **启用 HTTPS**：生产环境设置 `SESSION_COOKIE_SECURE=true`，并在 Ingress 配置 TLS，避免会话 Cookie 明文传输。
4. **保持安全开关与上传限制**：生产环境保持验证码、CSRF 双提交校验、登录限流与锁定开启；上传目录禁止执行脚本，并用 `MAX_CONTENT_LENGTH` 与 Ingress 限制请求体大小。
5. **跟进依赖更新**：Vue 2 已 EOL，升级计划见根目录 [README.md](../README.md) 的 Roadmap。
