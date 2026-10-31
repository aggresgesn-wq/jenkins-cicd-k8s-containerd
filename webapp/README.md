# 基于Flask实现后台权限管理系统

## Authbase铂金版本

**金钱有价，知识无价，本系统基础版本开源免费，另外有偿提供铂金版，功能更全，支持Vue3和自动代码生成等，并提供视频讲解，具体详情请移步[Authbase铂金版本](https://gitee.com/zhujf21st/authbase_premium_preview "Authbase铂金版本")。**

## Authbase FastAPI版本

**Authbase FastAPI版本，具体详情请移步[Authbase FastAPI版本](https://gitee.com/zhujf21st/authbase_fastapi "Authbase FastAPI版本")。**

## Authbase Flask版本

基于Python的Flask WEB框架实现后台权限管理系统，内容包含：用户管理、角色管理、资源管理和机构管理。基础版本开源免费，前端基于ElementUI + Vue2，后端基于Flask，前后端分离。

>套用Python社区的一句话，人生苦短，我用Python，本开源项目前端界面优美，后端代码精炼，希望能够帮助到有需要的朋友。

## 完整设计文档

文档请移步[设计文档](http://docs.authbase.top)

## 系统定制

**支持有偿系统定制，根据具体情况，几百几千不等。** 
1. 学生编程作业
2. 毕业设计都可以
3. 本系统无关也行，十几年的资深开发经验
4. <span style="color:red">可开科技公司发票</span>
5. ...

**微信扫码加我好友支付，备注authbase。**

![微信号](doc/wx.png)

## Docker运行

我已经将系统打包到docker镜像中，镜像中包含：
1. ubuntu 20.04
2. authbase代码
3. mysql server 8.0。数据库账户密码authbase/123456


具体方法参考源码中的docker目录。

镜像基于阿里云容器镜像服务进行自动构建

如何使用

1. docker pull registry.cn-hangzhou.aliyuncs.com/zisokal/authbase:1.1
2. docker run -d -p 5000:5000 -p 80:80 \
	-e DEV_DATABASE_URI="mysql+mysqlconnector://authbase:123456@127.0.0.1/authbase?charset=utf8" \
	--name authbase registry.cn-hangzhou.aliyuncs.com/zisokal/authbase:1.1
3. 打开浏览器访问页面 http://localhost   
   系统默认的登录名密码为admin/123456



**前端依赖插件**

 1. Vue
 2. Vuex
 3. ElementUI
 4. Axios
 

**后端依赖插件**

 1. Flask
 2. Flask-SQLAlchemy
 3. Flask-Login
 4. Flask-moment
 5. MySQL-connector-python
 6. Flask-Excel

## 启动方法

前端启动：

1. 安装Node.js
2. 进入源代码的ui目录。cd ui
3. npm install
4. npm run dev

后端启动：

更新使用uv包管理，uv是一个用Rust编写的、速度极快的Python包和项目管理工具，旨在成为Python生态中的一站式解决方案。具体安装可以参考[官网](https://docs.astral.sh/uv/getting-started/installation/)，根据自己的操作系统自行选择安装，本机可以没有python，uv自己管理。安装完成后，通过以下步骤启动后端服务。

1. mysql创建名为authbase的数据库(因为机构查询用到了CTE，所以MYSQL需要8.0以上版本)；
2. 导入根目录下db.sql数据库脚本到authbase数据库中；
3. 更改config.py DevelopmentConfig类下的数据库连接，提供用户名密码；
4. 执行命令安装虚拟环境和依赖包。

   ```shell
   uv sync
   ```

5. 启动后端

   ```shell
   uv run start.py
   ```

## 讨论群

欢迎加入python技术爱好者，群号码：297690915

## 效果图

![登陆](doc/登陆.png)

![首页](doc/首页.png)

![个人中心](doc/个人中心.png)

![机构管理](doc/机构管理.png)

![角色管理](doc/角色管理.png)

![用户管理](doc/用户管理.png)

![资源管理](doc/资源管理.png)

![登录历史](doc/登录历史.png)

![操作日志](doc/操作日志.png)

![服务监控](doc/server.png)
