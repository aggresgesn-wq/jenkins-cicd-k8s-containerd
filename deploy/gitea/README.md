# 在 Linux 上安装与配置 Gitea

本目录提供 Gitea 在 Linux 上的安装方式（二进制 + systemd 为推荐生产方案，另附 Docker Compose 与 K8s/Helm）、初始化配置、反向代理、Jenkins 对接与备份升级说明。

> 本仓库默认以 **GitHub** 为代码托管平台；Gitea 用于内网/自建场景，功能上可替代 GitHub 的仓库托管与 Webhook 触发。两者可以并存：生产只启用其中一个，避免同一分支被重复触发。

## 1. 环境要求

| 项 | 要求 |
| --- | --- |
| 操作系统 | 主流 Linux（Ubuntu 22.04+/Debian 12+/Rocky 9+/openEuler 等），x86_64 或 arm64 |
| 运行用户 | 独立的 `git` 用户（不要用 root 运行） |
| 数据库 | SQLite（≤10 人小团队）或 MySQL 8 / PostgreSQL 14+（推荐） |
| 内存 | 最低 1 GiB，推荐 2 GiB 以上 |
| 端口 | HTTP `3000`（由 Nginx 反代 443），SSH `2222`（或复用系统 22 端口） |

```bash
# 以 Ubuntu/Debian 为例
sudo apt update
sudo apt install -y git curl nginx mysql-server
sudo systemctl enable --now nginx mysql
```

## 2. 方式 A：二进制 + systemd（推荐生产）

### 2.1 创建用户与目录

```bash
sudo useradd --system --shell /bin/bash --comment 'Git Version Control' \
  --create-home --home-dir /home/git git

sudo mkdir -p /var/lib/gitea/{custom,data,log}
sudo chown -R git:git /var/lib/gitea
sudo chmod -R 750 /var/lib/gitea

sudo mkdir -p /etc/gitea
sudo chown root:git /etc/gitea
sudo chmod 770 /etc/gitea
```

### 2.2 下载并安装二进制

```bash
# 按需替换版本号与架构（amd64 / arm64）
GITEA_VERSION=1.22.6
curl -fL -o /tmp/gitea \
  "https://dl.gitea.com/gitea/${GITEA_VERSION}/gitea-${GITEA_VERSION}-linux-amd64"
sudo install -m 755 /tmp/gitea /usr/local/bin/gitea
gitea --version
```

> 国内网络可用 `https://dl.gitea.com` 的镜像或 GitHub Release 加速地址；下载后建议校验官方 `sha256`。

### 2.3 安装 systemd 服务

```bash
sudo cp deploy/gitea/gitea.service /etc/systemd/system/gitea.service
sudo systemctl daemon-reload
sudo systemctl enable --now gitea
sudo systemctl status gitea --no-pager
```

首次启动前先准备配置（见第 4 节），否则会进入网页安装向导。

## 3. 方式 B：Docker Compose

```bash
cd deploy/gitea
cp app.ini.example app.ini        # 修改数据库口令、SECRET_KEY、域名
sudo docker compose up -d
sudo docker compose logs -f gitea
```

`docker-compose.yml` 默认使用 MySQL 8 + 命名卷；生产建议把数据库换成托管实例，并挂载 `custom/`、`data/` 到宿主机目录。

## 4. 配置 app.ini

把 `app.ini.example` 复制到 `/etc/gitea/app.ini`（Docker 方式放到挂载目录），至少修改：

- `server.DOMAIN` / `server.ROOT_URL`：真实域名与 HTTPS 地址
- `server.SECRET_KEY`：`gitea generate secret SECRET_KEY` 生成
- `database.*`：MySQL/PostgreSQL 连接信息
- `security.INSTALL_LOCK = true`：锁定安装向导，防止被重新初始化
- `service.DISABLE_REGISTRATION = true`：关闭自助注册，由管理员建号
- `webhook.ALLOWED_HOST_LIST`：限制 Webhook 目标，避免 SSRF

配置完成后执行迁移并重启：

```bash
sudo -u git gitea migrate -c /etc/gitea/app.ini
sudo systemctl restart gitea
```

### 4.1 创建管理员

```bash
sudo -u git gitea admin user create \
  --admin --username gitea-admin --email admin@example.com \
  --random-password -c /etc/gitea/app.ini
```

密码只输出一次，请立即保存；首次登录后修改。

## 5. 反向代理与 HTTPS

```bash
sudo cp deploy/gitea/nginx-gitea.conf /etc/nginx/conf.d/gitea.conf
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d git.example.com   # 或使用已有证书
```

Nginx 需要正确传递 `Host`、`X-Forwarded-Proto`、`X-Real-IP`，并把 `client_max_body_size` 调大（LFS/附件）。

## 6. 与 Jenkins 对接

1. **克隆方式**：推荐 SSH。把 Jenkins 构建 Pod 的公钥加入 Gitea 对应用户的 *SSH Keys*，仓库地址使用 `ssh://git@git.example.com:2222/<org>/<repo>.git`。
2. **HTTP 凭据**：在 Jenkins 创建 Username with password（Gitea 用户名 + Access Token），ID 例如 `gitea-http`。
3. **Webhook**：
   - 若 Jenkins 安装了 **Gitea 插件**：Gitea 仓库 → *Settings → Webhooks → Add Webhook → Gitea*，URL 填 `https://jenkins.example.com/gitea-webhook/post`，Secret 与 Jenkins 侧一致。
   - 若只用 **GitHub 插件**：Gitea 版本需支持 GitHub 兼容 Webhook，URL 填 `https://jenkins.example.com/github-webhook/`；不支持时改用 **Generic Webhook Trigger**。
   - Jenkins Job 勾选对应触发器，Pipeline 仍使用仓库中的 `webapp/Jenkinsfile`。
4. **提交状态回写**：Gitea 的 Commit Status API 与 GitHub 不同，`webapp/Jenkinsfile` 里的 `githubStatus()` 仅适用于 GitHub；使用 Gitea 时应改为调用
   `POST /api/v1/repos/{owner}/{repo}/statuses/{sha}`（Token 需 `write:repository` 权限），或直接停用该步骤。

## 7. 把仓库从 GitHub 迁移到 Gitea

1. Gitea 右上角 *+ → New Migration* → 选择 GitHub。
2. 填仓库 URL 与 GitHub Token（只读 `repo` 即可），勾选 *Migrate Issues / Pull Requests / Releases*（按需）。
3. 迁移完成后在 Jenkins Job 中把仓库地址改为 Gitea 地址，并重新配置 Webhook。
4. 保留 GitHub 仓库作为镜像时，可用 *Settings → Mirror* 定时同步，避免双写。

## 8. 备份、升级与排障

```bash
# 备份（数据 + 配置 + 仓库 + 数据库）
sudo -u git gitea dump -c /etc/gitea/app.ini -f /var/backups/gitea-$(date +%F).zip

# 升级：替换二进制后执行迁移
sudo systemctl stop gitea
sudo install -m 755 /tmp/gitea-new /usr/local/bin/gitea
sudo -u git gitea migrate -c /etc/gitea/app.ini
sudo systemctl start gitea
```

| 现象 | 排查 |
| --- | --- |
| 502 Bad Gateway | `systemctl status gitea`、`journalctl -u gitea -n 100`；确认 `HTTP_ADDR/HTTP_PORT` 与 Nginx 一致 |
| 克隆 403/401 | SSH 端口与 `ROOT_URL` 不一致；检查 `SSH_PORT`、`START_SSH_SERVER`、防火墙 |
| Webhook 不触发 | Gitea *Webhooks → Recent Deliveries* 看响应码；URL 末尾斜杠、Secret、Jenkins 插件类型 |
| 附件/LFS 上传失败 | Nginx `client_max_body_size`、Gitea `server.LFS_START_SERVER` 与存储路径 |
| 升级后页面异常 | 未执行 `gitea migrate`，或 `custom/` 中模板/主题不兼容 |

## 9. 安全基线

- 关闭自助注册（`DISABLE_REGISTRATION = true`），管理员手工建号。
- 强制 HTTPS，`ROOT_URL` 使用 `https://`，并开启 `service.REQUIRE_SIGNIN_VIEW`（按需）。
- `webhook.ALLOWED_HOST_LIST` 限制外发目标，防止 SSRF 对内网探测。
- 数据库账号最小权限；`app.ini` 权限 `770`、属组 `git`，不要提交到仓库。
- 定期 `gitea dump` 并异地保存；每季度做一次恢复演练。
- 对外只暴露 Nginx 的 443；`3000` 与 `2222` 仅监听内网或本机。
