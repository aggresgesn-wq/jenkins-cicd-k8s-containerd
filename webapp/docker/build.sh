#!/bin/bash
set -e

# 基础镜像默认走渡渡鸟镜像同步站(https://docker.aityp.com)的国内地址，
# 需要官方镜像时用 BASE_IMAGE=ubuntu:20.04 ./build.sh 覆盖
BASE_IMAGE="${BASE_IMAGE:-swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/ubuntu:20.04}"

docker build --build-arg BASE_IMAGE="$BASE_IMAGE" -t zisokal/authbase:1.1 .
