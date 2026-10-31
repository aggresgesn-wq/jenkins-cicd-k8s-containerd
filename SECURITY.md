# 安全策略

本仓库包含一个可运行的 Flask + Vue 后台权限系统，以及 Jenkins + GitHub + K8s 的 CI/CD 示例（Gitea 可作为自建替代）。本文说明漏洞上报方式、密钥管理规范、已实施的安全控制与上线检查清单。安全是默认要求，不是可选附加项。

适用范围：`webapp/` 应用代码、`webapp/Jenkinsfile`、`deploy/k8s` 清单及相关文档。

## 安全边界与假设

- 集群、Ingress、MySQL 与镜像仓库由部署方负责加固；本仓库假设这些基础设施已启用最小权限与网络隔离。
- 应用信任 Ingress 传递的客户端信息，但只使用其做限流与审计，不将其作为授权依据。
- 生产必须启用 HTTPS；纯 HTTP 只允许用于本地开发与一次性测试环境。
- 管理员账号被视为高权限主体，其操作会写入审计日志；不假设管理员终端绝对可信。
- 第三方依赖与基础镜像的安全由上游维护者负责，本仓库通过固定版本、镜像同步与流水线扫描降低风险。

设计原则：默认拒绝、最小权限、纵深防御、失败关闭（fail closed）、密钥与代码分离。

## 支持的版本

| 版本 | 是否支持 | 说明 |
| --- | --- | --- |
| 2.x | 是 | 当前 `main` 分支，接收安全修复 |
| < 2.0 | 否 | 不再维护，建议升级 |

只对受支持版本接受安全报告。使用旧版本时请先复现于最新 `main` 或对应 release tag。

## 漏洞上报

**请勿通过公开 Issue 披露未修复漏洞。** 使用 GitHub Security Advisory 私密上报：

<https://github.com/aggresgesn-wq/jenkins-gitea-k8s-containerd/security/advisories/new>

报告请尽量包含：

- 受影响的版本、commit 或镜像 tag；
- 漏洞类型与影响范围（例如越权、CSRF、会话固定、命令执行）；
- 最小复现步骤或 PoC，附脱敏后的请求/响应；
- 是否需要特定角色、网络位置或配置；
- 建议的修复方向（可选）。

维护者目标：3 个工作日内确认收到，7 个工作日内完成初步评估；修复与披露时间根据严重程度和影响面协商。修复发布后，会在 Advisory 中致谢报告者（如报告者同意）。

## 非安全缺陷

普通功能 Bug、文档错误、部署问题请走 GitHub Issues。不要在公开 Issue 中附带未修复漏洞的利用细节、真实凭据或生产环境数据。

## 密钥管理规范

| 密钥/凭据 | 存放位置 | 轮换影响 |
| --- | --- | --- |
| `SECRET_KEY` | K8s Secret `webapp-secrets` | 所有 Session 与 CSRF 签名失效，用户需重新登录 |
| `DATABASE_URI` | K8s Secret `webapp-secrets` | 含数据库密码；更新后滚动重启生效 |
| `CAPTCHA_SECRET_KEY` | K8s Secret `webapp-secrets` | 已签发验证码失效；多副本必须保持一致 |
| ACR 推送凭据 | Jenkins Credentials `acr-credentials` | 仅影响镜像推送，需同步更新 Jenkins 凭据 |
| kubeconfig / ServiceAccount | Jenkins Credentials `kubeconfig` 或集群内 RBAC | 影响部署权限，按最小权限授予 |
| Ingress TLS 证书 | K8s TLS Secret | 影响 HTTPS，需在证书到期前轮换 |

强制规则：

1. **禁止入库**：任何真实密钥、密码、Token、kubeconfig、TLS 私钥都不得写入 Git、镜像层、Dockerfile、Jenkinsfile、文档示例或 Issue。
2. **禁止入日志**：应用与流水线日志不得打印 `Authorization`、`Cookie`、`X-XSRF-TOKEN`、数据库连接串等敏感信息。
3. **Base64 不是加密**：K8s Secret 的 `data` 只是 Base64 编码，不等于加密；不要提交含真实值的 Secret YAML。
4. **最小权限**：数据库账号只授予业务所需的 `SELECT/INSERT/UPDATE/DELETE`；Jenkins 部署账号只授予目标 namespace 的必要权限；ACR 账号只授予推送权限。
5. **环境隔离**：开发、测试、生产使用不同的 Secret、数据库与镜像仓库路径，禁止复用生产凭据。
6. **创建方式**：使用 `kubectl create secret`、Jenkins Credentials 或 External Secrets / Sealed Secrets 等方案；`.env` 仅限本地且已被 `.gitignore` 忽略。
7. **泄露处置**：一旦怀疑泄露，立即轮换密钥、撤销会话与 Token、检查审计日志，并评估是否需要通知受影响用户。

## 已实施的安全控制

| 控制项 | 实现方式 | 验证方式 |
| --- | --- | --- |
| RBAC 授权 | 用户-角色-资源模型；角色 `ROLEKEY` 为 `superadmin` / `admin` / `readonly`；接口用 `@permission('system:user:list')` 等权限码校验 | 权限矩阵测试：匿名 401、无权限 403、有权限 2xx |
| 401/403 语义 | 未登录返回 HTTP 401；已登录但无权限返回 HTTP 403；前端据此跳转登录或提示无权限 | `curl -i` 检查状态码，不依赖响应体 `code` |
| Session Cookie | Flask Session Cookie 设置 `HttpOnly`、`SameSite=Lax`；生产设置 `Secure` | 浏览器 DevTools 查看 Set-Cookie；生产仅 HTTPS |
| CSRF 防护 | 登录后下发 `XSRF-TOKEN` Cookie；前端所有 POST/PUT/DELETE 请求带 `X-XSRF-TOKEN` 头；服务端做双提交 Cookie 校验 | 删除/篡改请求头后写请求应被拒绝 |
| 登录限流与锁定 | 同一账号/来源连续失败达到阈值后临时锁定，返回统一错误，避免账号枚举 | 连续错误密码触发锁定；等待窗口后恢复 |
| 图形验证码 | Flask-Simple-Captcha，密钥来自 `CAPTCHA_SECRET_KEY`，验证码有有效期 | 错误验证码无法登录；多副本校验一致 |
| 密码存储 | 密码以加盐哈希存储，不保存明文；修改密码需验证原密码 | 数据库 `SYUSER.PWD` 不出现明文 |
| 上传校验 | 校验扩展名、MIME 与大小；随机文件名；上传目录不执行脚本；`MAX_CONTENT_LENGTH` 兜底 | 上传可执行文件/超限文件应失败 |
| 容器加固 | 非 root 用户运行；`readOnlyRootFilesystem: true`；`allowPrivilegeEscalation: false`；drop ALL capabilities；不使用 privileged、不挂载宿主机 containerd socket | `kubectl exec` 查看 UID；检查 PodSecurityContext |
| 网络隔离 | NetworkPolicy 默认拒绝，仅放行 Ingress、DNS 与 MySQL 必要流量 | `kubectl describe networkpolicy` 与连通性测试 |
| 密钥注入 | 运行期通过 K8s Secret 环境变量注入；CI 使用 Jenkins Credentials | 仓库与镜像历史中检索不到真实密钥 |
| 供应链检查 | Jenkins 流水线包含后端测试、前端构建与安全扫描（含 SBOM）阶段；镜像以不可变 tag/digest 推送 | 流水线失败即阻断发布 |

运行期抽查：

```powershell
# 目录：E:\CICD（PowerShell）
kubectl -n webapp get secret webapp-secrets
kubectl -n webapp get pods -l app=webapp
kubectl -n webapp exec deploy/webapp -- id
kubectl -n webapp exec deploy/webapp -- sh -c "touch /tmp/healthz && echo tmp-writable"
kubectl -n webapp get networkpolicy,pdb,pvc
# 先另开终端：kubectl -n webapp port-forward svc/webapp 8080:80
curl.exe -i http://127.0.0.1:8080/prod-api/system/user/list
```

最后一条应返回 401（未登录）。如返回 200，说明鉴权链路存在缺陷，应立即停止发布并排查。

## 部署检查清单

部署前：

- [ ] `SECRET_KEY`、`CAPTCHA_SECRET_KEY` 为随机值且未出现在 Git/镜像中。
- [ ] `DATABASE_URI` 使用最小权限账号，密码已 URL 编码，数据库为 MySQL 8.0+。
- [ ] K8s Secret `webapp-secrets` 已创建，名称与 Deployment 的 `secretRef` 一致。
- [ ] 镜像已通过安全扫描，使用明确的 tag 或 digest，不使用 `latest`。
- [ ] Ingress 已配置 TLS，`SESSION_COOKIE_SECURE=true`。
- [ ] `deploy/k8s` 中的 NetworkPolicy、PDB、PVC、ConfigMap 已按环境调整。

部署后：

- [ ] `/health/live` 与 `/health/ready` 均返回成功，Pod 处于 Ready。
- [ ] 未登录访问受保护接口返回 401，普通账号访问越权接口返回 403。
- [ ] 写请求缺少 `X-XSRF-TOKEN` 时被拒绝。
- [ ] 默认管理员 `admin` 已修改初始密码，或已被禁用。
- [ ] 验证码、登录限流与锁定生效。
- [ ] 容器以非 root 运行，根文件系统只读，上传目录可写且不可执行。
- [ ] 日志中无密钥、Cookie、密码；审计日志可查询。
- [ ] 已完成一次回滚演练（`kubectl rollout undo`）。

## 已知限制与后续工作

- Vue 2 已 EOL，前端依赖不再接收安全更新，升级到 Vue 3 已列入 Roadmap。
- 数据库仍通过手工导入 `db.sql` 初始化，尚未引入 Flask-Migrate / Alembic，结构变更需人工评审。
- 可观测性仍在完善，Prometheus 指标与结构化日志尚未落地。

发现上述范围外的安全问题，仍欢迎按本文方式私密上报。

## 事件响应

1. **止损**：下线受影响实例、撤销泄露凭据、阻断异常来源；保留 Pod、日志与审计记录，不要直接删除证据。
2. **轮换**：更新 `SECRET_KEY`（使全部会话失效）、数据库密码、验证码密钥、ACR/Jenkins 凭据与 TLS 证书。
3. **排查**：结合 `SYOPERATIONLOG`、`SYONLINE`、Ingress 与 Jenkins 日志确认影响范围与时间线。
4. **修复与验证**：在测试环境复现并修复，补充回归测试与权限矩阵用例，再按发布流程上线。
5. **通知**：如涉及个人信息或业务数据，按组织合规要求通知受影响方与安全团队。
6. **复盘**：记录根因、检测缺口与改进项，转化为代码、配置或文档变更。
