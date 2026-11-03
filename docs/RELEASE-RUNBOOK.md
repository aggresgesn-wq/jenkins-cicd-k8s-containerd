# Kustomize 发布与恢复规程

主发布入口：`ci/Jenkinsfile.release` + `ci/release.sh` + `deploy/k8s/overlays/`。
Helm 为可选安装示例，不允许与 Kustomize 同时管理同一套资源。#53 原始文件继续作为构建证据保存，不能用作完整发布证明。

## 职责与权限

| 身份 | 职责 | 约束 |
| --- | --- | --- |
| 平台管理员 | Namespace、Secret、StorageClass、RBAC、集群组件 | 不交给应用构建脚本 |
| 构建 Job | 测试、构建、扫描、推送镜像、交付 digest | 不挂载发布身份；lab 已禁止自动挂载 API token |
| 发布 Job | 渲染 Kustomize、diff/apply、rollout、恢复旧镜像 | 只使用可信工程仓库、独立 jenkins-release 身份 |
| 审批人 | 核对 staging、镜像来源和变更内容 | Jenkins 管理员设置 RELEASE_APPROVERS；管理员本身仍可能有审批权限 |

注意：lab 保留的宿主机 socket/特权 sidecar 仍有节点级风险，禁止挂 token 并不能消除此风险。迁移受限 Rootless 构建环境前，仅用于可信实验代码；不能把这个配置称作生产隔离。候选 hardened 单 Pod 流程也不作为正式生产发布入口。

## 一次性准备

1. 管理员创建 `webapp`、`webapp-staging` 与 Jenkins Agent 命名空间。确认 Secret、RWX StorageClass、imagePullSecret、Ingress/TLS、数据库和网络策略可用。
2. `deploy/k8s/jenkins-release-rbac.yaml` 默认假设发布 Agent 位于 `jenkins`。若现场使用 `jenkins-agent`，同时调整 ServiceAccount namespace 和两个 RoleBinding subjects，不改变应用 namespace。
3. 仅向专用发布 Job 绑定 jenkins-release，不给构建 Job。这个角色没有 pods/exec、Pod 创建或 Secret 读取权限，但 Deployment 写权限仍可间接获取应用 Secret，因此发布 Job 配置与 SCM 必须受控。
4. 发布 Job 的 SCM 固定本工程仓库受保护的 main，Script Path 为 `ci/Jenkinsfile.release`；不加载来自应用仓库或不可信 PR 的 Jenkinsfile。限制谁能修改 Job、触发生产与更改基础设施仓库。
5. 管理员为该 Job 注入 APP_IMAGE_REPOSITORY（完整仓库名，不含 tag/digest）和 RELEASE_APPROVERS（审批用户/组）。应用参数仅接受 digest，不允许临时替换镜像仓库。
6. 每个环境只能由这一个发布 Job 写入；disableConcurrentBuilds 只约束同一 Job，不阻止其他 Job/管理员并发操作。

部署 Role 不负责创建 Namespace；基础设施部署先于应用发布。Kustomize 基础资源位于 deploy/k8s/base，overlay 引用该目录，避免直接加载目录外 YAML 的安全限制。基础资源文件已移动，旧脚本若直接引用 deploy/k8s/deployment.yaml 等路径，须更新为 deploy/k8s/base/ 下对应路径。

## 发布步骤

1. 构建并推送镜像，保留应用 commit、构建号、扫描报告、远端 registry digest。发布 Job 本身不验证这些报告或签名，审批人必须核对，签名准入仍待建设。
2. 选择 staging，输入合法 sha256 digest；Job 渲染配置、执行 diff，保存旧镜像，apply 并等待 rollout。
3. 验证 Service/Ingress、登录与数据库读写；rollout-ready 只表示 Deployment 就绪，不代表外部流量链路已验证。
4. 选择 production 时，同一个 digest 先部署 staging，再进入限时指定审批人确认，然后发布生产。记录应用访问验证结果。
5. 归档 digest、工程 commit、previous-image、target-image、result、rollout.txt。工作区会清理，Jenkins 归档必须使用持久存储与访问控制。

staging 固定一个副本、无 HPA，PDB 允许维护时中断；允许短暂不可用。现有 staging 如已部署 HPA，仅从文件删除不会自动删除集群资源：管理员先导出配置，再显式删除 staging 的 webapp HPA，确认没有其他控制器重建它。不要使用全命名空间 prune。

生产仍使用 HPA；变更时检查实际副本和数据库连接预算，避免重复 apply 固定 replicas 引起缩容。完整收敛副本字段所有权需结合现场 last-applied/field manager 迁移，暂不在未接入集群时自动执行。

## 失败恢复

- staging 失败：不修改生产，保留记录并排查。
- 审批拒绝或超时：未进入生产时不执行生产回滚。
- 生产 apply/rollout 失败或构建中止：只有存在 started 标记才恢复旧镜像；JSON Patch 会检查当前镜像仍为本次目标，避免覆盖别人随后发布的版本。
- 第一次部署没有旧镜像；Agent 丢失、API 不可达、镜像冲突都会使自动恢复不能保证成功。按失败记录由管理员接管。
- 恢复只涉及镜像，不恢复 ConfigMap、PVC 或数据库。涉及 schema/配置变更时，必须提前验证旧版兼容性。

## 恢复演练与证据

在隔离环境使用同一发布流程，注入不可就绪镜像，记录发现时间、恢复启动和完成时间；核对旧镜像、Pod Ready、Ingress 与关键业务。备份恢复在独立数据库执行，禁止对当前数据直接覆盖。

MySQL 备份现在使用 pipefail、临时文件、gzip 校验和 SHA-256；只认同时具有 .sql.gz 和 .sha256 的完整对。校验成功不等于可恢复，需要导入验证。备份保留清理由异机复制与恢复验证后执行，避免失败周期自动删除最后可用副本；必须设置容量告警与人工保留计划。

```text
变更编号 / 应用 commit / 工程 commit：
构建号 / 镜像 digest / 扫描报告：
环境 / 发布人与审批人：
旧镜像 / 新镜像：
diff 审核 / rollout / Service-Ingress 验证：
故障时间 / 恢复开始 / 恢复完成：
恢复后镜像 / 业务与数据验证：
备份版本 / 校验和 / 隔离恢复结果：
未通过项及负责人：
```

本轮只有本地配置和模拟失败测试。真实 push、发布、审批、回滚、数据恢复仍需现场验收，验收后再更新运行证据。
