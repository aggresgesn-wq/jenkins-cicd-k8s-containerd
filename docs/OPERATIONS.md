# 三节点集群与 NFS/Gitea 运维手册

适用范围：一个三节点 Kubernetes 实验集群 + 一台 NFS/Gitea VM。命令中的 context、地址、服务名、路径必须按实际环境填写。下面是操作方案，不是已执行记录。

## 资产与日常巡检

复制 `ops/inventory.example.yaml` 到本地填写，记录每台机器的 CPU、内存、磁盘、IP、角色、系统/K8s/containerd 版本，列出 NFS 导出路径、客户端、挂载选项、Gitea 数据库与仓库目录。含内网信息的实例清单不提交公共仓库。

```bash
python ops/inspect_cluster.py --context LAB_CONTEXT --output reports/cluster-health.json
kubectl --context LAB_CONTEXT get nodes -o wide
kubectl --context LAB_CONTEXT -n jenkins-agent get pods -o wide
kubectl --context LAB_CONTEXT get pvc -A
```

脚本只 GET 节点、Pod、PVC；需要对应 list 权限，不读取 Secrets、日志或 kubeconfig 内容。不执行跨 context 切换。报告中的 healthy 仅表示本次节点/Pod/PVC 检查无 error，不证明业务可用或 NFS 可读写。

| 频率建议 | 检查 | 保留证据 |
| --- | --- | --- |
| 每次发布前后 | 节点 Ready、Pod readiness、重启计数、PVC Bound、应用访问 | commit、构建号、巡检 JSON、HTTP 结果 |
| 每天 | VM 磁盘/ inode、NFS 服务、Gitea 服务、最近备份 | df/findmnt/systemctl 结果、备份时间与校验和 |
| 每周 | 依赖告警、失败构建分类、容量趋势 | 风险清单与处置记录 |
| 每月/重大变更后 | 隔离环境恢复、错误镜像恢复演练 | 恢复时间、验证步骤、未通过项 |

## DNS 与构建失败排查

1. 在节点与 Agent Pod 分别查询镜像、PyPI 域名；对比 `/etc/resolv.conf`、CoreDNS 转发与代理设置。日志中出现 198.18.* 只能作为排查线索，不直接等同于污染结论。
2. 区分镜像拉取网络（节点）、Agent 下载依赖网络和 BuildKit RUN 网络。Pod 的 hostAliases 不保证影响 BuildKit 内部步骤。
3. 分别验证 DNS、路由、TLS、HTTP 状态；不要通过关闭证书验证掩盖问题。
4. #53 使用固定 hostAliases/--add-host 临时规避；生产化应改为可靠解析、受控代理或内部镜像/依赖仓库，并移除过期 IP。
5. 对 ImagePullBackOff 查节点到 registry、imagePullSecrets 及 tag；对 Pending 查资源、nodeSelector、taint 和 PVC；对构建失败查看第一个错误，不能只看最后一行。

## NFS 检查

服务 VM 查看 `systemctl status nfs-server`（具体服务名随发行版变化）、`exportfs -v`、`df -h`、`df -i`；客户端使用 `findmnt -t nfs,nfs4` 核对真实挂载与选项。PVC Bound 不证明服务端 I/O 正常，另需在专用测试目录用应用 UID 执行受控读写验证。

仅向实验节点网段开放导出；避免无理由使用 no_root_squash。不可对正在提供服务的挂载盲目强制卸载、删除 PVC 或改变 UID/GID。NFS 数据盘、Gitea 数据与 Jenkins PVC 是否共用需要现场确认。

## Gitea/NFS 备份与恢复

一致性备份需协调 Gitea 数据库、仓库和附件的写入窗口；按照实际安装版本的 [Gitea 官方备份恢复文档](https://docs.gitea.com/administration/backup-and-restore/) 停止写入/服务后执行 dump 或数据库原生备份。不要只复制正在写入的数据库文件。

1. 确认 Gitea 二进制/容器版本、运行用户、app.ini、数据库类型与所有存储路径；先在演练环境验证命令。
2. 维护窗口暂停写入，以 Gitea 运行用户执行 `gitea dump -c /actual/path/app.ini`；外部数据库按其一致性机制备份。记录实际版本和时间。
3. NFS 上的应用文件和数据库分别制定一致性备份；普通文件复制不能替代数据库备份。Jenkins 如使用 NFS，也要协调停止写入并保护 JENKINS_HOME 中的密钥。
4. 备份包计算 SHA-256，发送到另一故障域，限制读取权限并加密。不要上传到本 GitHub 仓库；不能只保存在同一台 VM/NFS 盘。
5. 在隔离 VM 恢复同版本 Gitea、数据库、仓库及附件，核对权限、hooks、登录、clone、push 和文件完整性。确认不会向真实 Jenkins 发送 Webhook。
6. 记录恢复起止时间、数据恢复点和失败原因；结束后按演练方案处置隔离环境，不覆盖现有服务。

建议目标可先设 RPO 24h、RTO 2h，但二者仅为计划，**尚无实测达成记录**。保留周期按数据量与磁盘容量确定。

## 发布故障处理

#53 尚无自动发布，不能直接用它演示回滚。候选发布脚本 `ci/release.sh` 只恢复应用镜像，不恢复 ConfigMap、数据库或 PVC。配置/schema 变更须设计向后兼容与单独恢复方案。

故障时先冻结新发布，保存 commit/镜像/rollout 状态，检查事件和 readiness；确认恢复目标后再操作，最后验证 Service/Ingress 和关键业务。不要将“删除 Pod 重建”作为数据恢复手段。

## 演练记录模板

```text
日期 / 操作人 / 环境 context：
变更或故障假设：
影响范围及停止条件：
演练前 commit / 镜像 / 备份版本：
检测时间 / 开始恢复时间 / 恢复完成时间：
执行命令与退出码（脱敏）：
业务、数据一致性、巡检验证结果：
实测恢复时间 / 实际数据恢复点：
未通过项 / 后续改进：
```

优先在隔离环境演练错误镜像、PVC Pending、NFS 不可达与 Gitea 恢复；禁止为演示直接破坏现有 VM 或生产数据。
