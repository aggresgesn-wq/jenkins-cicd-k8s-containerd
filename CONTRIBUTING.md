# 贡献指南

感谢参与改进 Jenkins + GitHub + K8s CI/CD 示例与内置 Flask 后台系统。本文说明开发流程、分支与提交规范、代码风格、测试要求和 PR 检查清单。

安全漏洞请勿公开提交 Issue，按 [SECURITY.md](SECURITY.md) 的私密渠道上报。

## 开发流程

1. **先建 Issue**：描述背景、期望行为与验收标准；较大的改动先讨论方案。
2. **同步主分支**：从最新 `main` 切出短生命周期分支，不要直接在 `main` 上提交。
3. **本地跑通**：按 [webapp/README.md](webapp/README.md) 启动 MySQL、后端与前端。
4. **小步提交**：一个提交只做一件事，提交信息遵循 Conventional Commits。
5. **自测**：后端测试、前端 lint/build 全部通过；涉及接口权限的补充权限矩阵测试。
6. **发起 PR**：填写检查清单，说明变更、验证方式与回滚方案，等待 Review。

本地准备：

```powershell
# 目录：E:\CICD\webapp（PowerShell）
uv sync
uv run --with pytest python -m pytest tests -q
uv run --with ruff ruff check .
uv run --with ruff ruff format --check .

# 目录：E:\CICD\webapp\ui（PowerShell）
npm install --registry=https://registry.npmmirror.com
npm run lint
npm run build:prod
```

## 分支规范

| 分支 | 用途 | 示例 |
| --- | --- | --- |
| `main` | 受保护的主分支，始终可发布 | `main` |
| `feat/<issue>-<slug>` | 新功能 | `feat/42-user-lockout` |
| `fix/<issue>-<slug>` | 缺陷修复 | `fix/57-403-status` |
| `docs/<slug>` | 文档改进 | `docs/deployment-webhook` |
| `ci/<slug>` | 流水线与部署配置 | `ci/kaniko-build` |
| `chore/<slug>` | 依赖、工具、杂项 | `chore/bump-node` |

分支尽量在 3 天内合并；长期分支需定期 rebase `main` 并说明原因。

## 提交规范

采用 [Conventional Commits](https://www.conventionalcommits.org/)，格式：

```text
<type>(<scope>): <subject>

<body>

<footer>
```

常用 type：

| type | 含义 |
| --- | --- |
| `feat` | 新功能 |
| `fix` | 缺陷修复 |
| `docs` | 仅文档 |
| `refactor` | 不改变行为的重构 |
| `perf` | 性能优化 |
| `test` | 测试相关 |
| `build` | 构建系统或依赖 |
| `ci` | CI/CD 配置 |
| `chore` | 杂项 |
| `revert` | 回滚提交 |

示例：

```text
feat(auth): 增加登录失败锁定
fix(api): 未登录统一返回 HTTP 401
docs(deploy): 补充 GitHub Webhook 配置
ci(jenkins): 使用 kaniko 替代 privileged 构建
test(rbac): 覆盖只读角色的权限矩阵
```

不兼容变更在 type 后加 `!`，并在 footer 写 `BREAKING CHANGE:` 说明迁移方式。提交主题使用中文或英文均可，type/scope 使用英文。

## 代码风格

### Python

- 遵循 PEP 8，4 空格缩进，单行不超过 100 字符，以 `pyproject.toml` / ruff 配置为准。
- 提交前运行 `ruff check .` 与 `ruff format --check .`；不要提交被注释掉的调试代码。
- 路由装饰器保持“路由 → 登录校验 → 权限校验”的顺序，权限码使用 `system:user:list` 这类稳定命名。
- 异常要记录上下文并返回合适的 HTTP 状态码；禁止把密码、Cookie、连接串写入日志。
- 新增配置一律走环境变量，不在代码中写默认密钥。

### 前端

- 遵循 `webapp/ui/.eslintrc.js`，2 空格缩进，提交前执行 `npm run lint`。
- 组件文件使用 PascalCase 或项目既有命名；避免新增全局状态，优先复用 `store` 与 `utils`。
- 所有写请求通过统一 axios 实例发出，确保自动携带 `X-XSRF-TOKEN`；不要绕过拦截器。
- 不在前端保存明文密码，不使用 jsencrypt 私钥方案；密码交给浏览器密码管理器。

### YAML / Jenkins / SQL

- YAML 2 空格缩进；镜像使用明确 tag 或 digest，不使用 `latest`。
- Jenkins 构建不得使用 privileged 容器、不得挂载宿主机 containerd socket；构建统一走 kaniko。
- 禁止在 Jenkinsfile、K8s 清单、`db.sql` 中写入真实密码或 Token。
- SQL 变更保持 MySQL 8 兼容与 `utf8mb4`；同步更新 `db.sql` 与相关文档，待 Alembic 落地后改为迁移脚本。

## 测试要求

- **新增或修改接口必须带权限矩阵测试**，至少覆盖：
  - 匿名访问返回 HTTP 401；
  - 已登录但无权限返回 HTTP 403；
  - 具备权限码时返回 2xx；
  - 写接口缺少 `X-XSRF-TOKEN` 时被拒绝。
- 角色相关改动同时覆盖 `superadmin`、`admin`、`readonly` 三类 `ROLEKEY`，以及禁用角色/禁用用户。
- 测试使用 `testing` 配置与独立测试库，禁止连接开发或生产数据库；测试数据在 teardown 中清理。
- 前端改动至少通过 `npm run lint` 与 `npm run build:prod`；涉及交互的 PR 附截图或录屏。
- 流水线或 K8s 清单改动需在测试环境验证：构建、推送、部署、探针、回滚至少各一次。
- 安全扫描失败不得通过跳过检查来合并；确需例外时在 PR 中说明原因与补偿措施。

## PR 检查清单

- [ ] 已关联 Issue，PR 标题符合 Conventional Commits。
- [ ] 变更范围单一，没有无关格式化或重构。
- [ ] 后端测试通过，新增接口包含 401/403/2xx 权限矩阵用例。
- [ ] 前端 `npm run lint`、`npm run build:prod` 通过。
- [ ] 文档已同步（README、DEPLOYMENT、ARCHITECTURE、SECURITY 中受影响的部分）。
- [ ] 无真实密钥、密码、Token、kubeconfig、生产数据。
- [ ] 数据库变更有 `db.sql` 更新与回滚说明。
- [ ] Jenkins/K8s 变更经过测试环境验证，并说明回滚方式。
- [ ] 涉及 UI 的变更附截图；涉及接口的变更附 `curl` 示例。
- [ ] CI 全绿，安全扫描无未处理的高危项。

## Review 与合并

- 至少 1 名维护者 Approve；涉及认证、授权、密钥、部署的改动建议 2 人 Review。
- 合并方式使用 Squash Merge，合并后的提交信息保持 Conventional Commits。
- 合并后删除功能分支；`main` 保持可构建、可部署、可回滚。
- 发现合并后回归时，优先 `revert` 对应提交，再重新提交修复 PR。
