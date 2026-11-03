.PHONY: help install test lint render verify clean

PY ?= python3

help: ## 显示可用目标
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-10s %s\n", $$1, $$2}'

install: ## 安装后端开发依赖
	$(PY) -m pip install -e './webapp[dev]'

test: ## 运行后端测试
	$(PY) -m pytest webapp/tests -q

lint: ## ruff 静态检查
	$(PY) -m ruff check webapp

render: ## 渲染 staging / production 清单
	kubectl kustomize deploy/k8s/overlays/staging > /dev/null
	kubectl kustomize deploy/k8s/overlays/production > /dev/null

verify: ## 脚本语法 + 发布/巡检回归
	sh -n ci/release.sh
	sh -n ops/e2e_drill.sh
	$(PY) -m unittest discover -s ci/tests
	$(PY) -m unittest discover -s ops/tests

clean: ## 清理本地缓存
	rm -rf reports .pytest_cache .ruff_cache .coverage
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
