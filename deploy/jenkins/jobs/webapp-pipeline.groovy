// Jenkins Job DSL：自动创建 webapp 流水线 Job
//
// 前置：Jenkins 安装 job-dsl 插件，并在 JCasC/系统设置中配置 Job DSL 种子任务，
// 或使用 `jenkins-cli` 执行 `dsl`。替换 owner/repo 与凭据 ID 后再使用。
pipelineJob('webapp-pipeline') {
    description('webapp：GitHub → Jenkins → kaniko → ACR → K8s（staging/production）')
    keepDependencies(false)

    definition {
        cpsScm {
            scm {
                git {
                    remote {
                        url('https://github.com/aggresgesn-wq/jenkins-github-k8s-containerd.git')
                        credentials('github-scm')
                    }
                    branch('*/main')
                }
            }
            scriptPath('webapp/Jenkinsfile')
            lightweight(true)
        }
    }

    triggers {
        githubPush()
    }

    properties {
        disableConcurrentBuilds()
    }
}
