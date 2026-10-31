# jenkins-gitea-k8s-containerd
Deploy containerized Jenkins on K8s, integrate with gitea for CI/CD pipeline

- 应用代码：[webapp/](webapp)（Flask + Vue 后台权限管理系统）
- 基础镜像加速：镜像地址取自 [渡渡鸟镜像同步站](https://docker.aityp.com)，同步到华为云 SWR，形如 `swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.11`，用法见 [webapp/README.md](webapp/README.md) 的“基础镜像加速（国内）”一节
