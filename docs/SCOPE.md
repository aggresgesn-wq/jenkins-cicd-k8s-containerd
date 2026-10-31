# 功能范围与遗留问题清单

本文件明确“哪些功能是真实可用的、哪些仍是若依模板遗留”，避免出现“页面在、接口没有”的假功能，并记录后续清理计划。

## 1. 已具备后端能力的功能（可正常使用）

| 模块 | 接口 | 说明 |
| --- | --- | --- |
| 登录 / 退出 | `POST /prod-api/login`、`POST /prod-api/logout` | Session + 验证码 + 登录限流 |
| 个人中心 | `GET/PUT /system/user/profile`、`PUT /system/user/profile/updatePwd`、`POST /system/user/profile/avatar` | 改密轮换盐值，头像校验类型与大小 |
| 用户管理 | `/system/user/**`（list/get/add/edit/delete/changeStatus/resetPwd/authRole/export） | 含删除保护（不能删自己、不能删内置 admin） |
| 角色管理 | `/system/role/**`（list/get/add/edit/delete/changeStatus/dataScope/authUser/*） | 内置角色与仍被引用的角色禁止删除 |
| 菜单/资源 | `/system/menu/**` | 树形资源维护 |
| 部门管理 | `/system/dept/**` | 上级部门成环校验、子部门/用户存在时禁止删除 |
| 字典与参数 | `/system/dict/**`、`/system/config/**` | 字典类型被引用时禁止删除；`refreshCache` 为显式空操作 |
| 登录日志 | `/monitor/logininfor/**`（list/export/delete/clean） | 登录/退出记录 |
| 在线用户 | `/monitor/online/list`、`DELETE /monitor/online/{id}` | 基于登录历史聚合；**不会立即吊销浏览器 Session**（无状态 Cookie 的固有限制） |
| 操作日志 | `/monitor/operlog/**` | 关键写操作已接入 `@log_operation`，密码/Token 脱敏 |
| 服务监控 | `/monitor/server` | 单次 CPU 采样 |
| 健康检查 / 指标 | `/health/live`、`/health/ready`、`/metrics` | 探针与 Prometheus |

## 2. 仍未实现、需要决定去留的若依模板模块

以下页面与 API 目前**没有后端实现**，属于“看起来存在但点进去不可用”，必须在下一轮二选一：

| 模块 | 前端位置 | 建议 |
| --- | --- | --- |
| 定时任务 | `views/monitor/job`、`views/monitor/job/log` | 删除（K8s CronJob 已覆盖调度需求） |
| 缓存监控 | `views/monitor/cache` | 删除 |
| Druid 监控 | `views/monitor/druid` | 删除（与 Flask 无关） |
| 岗位管理 | `views/system/post` | 删除 |
| 通知公告 | `views/system/notice` | 删除 |
| 代码生成 | `views/tool/gen`、`views/tool/build` | 删除 |
| 用户导入 | `/system/user/importData` | 删除入口 |

清理方式（一次性提交）：

1. 删除对应 `views/` 目录与 `api/` 文件；
2. 删除 `router/index.js` 中的路由与 `src/assets/icons/svg` 中不再使用的图标；
3. 清理 `db.sql` 中 `SYRESOURCE` 的相关菜单/按钮权限行与 `sys_dict_*` 数据；
4. 在前端菜单不再请求这些路径后，删除对应后端未实现的空壳路由（当前后端本来就没有，无需改代码）。

## 3. 已知技术债（按优先级）

1. **输入校验**：多数接口仍直接读取 `request.json[...]`，缺少统一的 400/404/409 语义。计划引入轻量 Schema（如 `app/validation.py`）覆盖用户、角色、部门、配置的写接口。
2. **排序字段白名单**：`user/role/online/operlog` 列表仍用 `getattr(Model, 用户输入)`，非法字段会 500。计划在 `app/security.py` 增加 `safe_order_by()` 并逐接口替换。
3. **初始化数据拆分**：`db.sql` 同时包含结构、种子与历史演示数据（用户、登录记录、操作日志）。计划拆为：
   - `migrations/`（结构，Alembic）；
   - `seed.sql`（内置角色、菜单、字典等最小数据）；
   - `demo-data.sql`（仅本地演示）；
   - 首次启动用 `scripts/reset_password.py` 生成管理员。
4. **数据库迁移**：当前角色/部门等类型已与 `db.sql` 对齐（`SYROLE.ID varchar(36)`、`DATASCOPE char(1)`），但缺少版本化迁移工具，计划引入 Flask-Migrate。
5. **前端依赖**：Vue 2.7 已 EOL，计划迁移 Vue 3 + Vite。
6. **在线用户强制下线**：无状态 Session 下无法真正吊销，需引入服务端会话表或 Redis 才能真正生效。

## 4. 与本次修复对应的变更

- 开发环境 API 前缀统一为 `/prod-api`，代理不再重写路径；
- Flask 增加 SPA catch-all，刷新 `/system/user` 等前端路由不再 404；
- 角色主键/数据范围类型与数据库对齐；
- 补齐 `resetPwd`、在线用户、登录日志删除/清空、配置与字典缓存刷新接口；
- 改密与重置密码均轮换盐值；
- 审计日志改为独立会话写入，不再参与业务事务提交；
- 部门树增加成环与删除校验，字典类型增加引用校验；
- 移除向第三方 IP 定位服务发送用户 IP 的逻辑；
- 移除默认管理员口令，新增重置脚本。
