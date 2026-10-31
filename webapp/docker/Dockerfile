# 基础镜像取自渡渡鸟镜像同步站(https://docker.aityp.com)，国内可直接拉取；
# 需要官方镜像时用 --build-arg BASE_IMAGE=ubuntu:20.04 覆盖。
ARG BASE_IMAGE=swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/ubuntu:20.04
FROM ${BASE_IMAGE}

# solve please select the geographic area in which you live problems
ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Shanghai

ADD sources.list /etc/apt/sources.list
ADD pip.conf /root/.pip/pip.conf
ADD docker-entrypoint.sh /tmp/docker-entrypoint.sh

RUN apt update && apt install -y git python3.8 python3-pip && \
    apt install -y nodejs && apt install -y npm && \
    cd /opt && git clone https://gitee.com/zhujf21st/authbase.git && cd authbase && \
    cd ui && npm install && cd .. && \
    pip3 install -r requirements.txt && \
    mv /tmp/docker-entrypoint.sh /opt/authbase/docker-entrypoint.sh && chmod +x /opt/authbase/docker-entrypoint.sh &&  \
    apt install -yq mysql-server && \
    service mysql start && cd /opt/authbase &&  mysql < db.sql || true && mysql < init-user.sql && \
    apt remove -y git && apt clean



WORKDIR /opt/authbase
ENTRYPOINT ["sh", "docker-entrypoint.sh"]    