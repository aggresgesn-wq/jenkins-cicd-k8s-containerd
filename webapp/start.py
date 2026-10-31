import os
from app import create_app, db
from flask import request, render_template, jsonify, session
import importlib
from app import setup_logger

logger = setup_logger(__name__)

def load_routes():
    for filename in os.listdir(f"./app/routes"):
        if filename.endswith('.py') and filename != '__init__.py':
            module_name = filename[:-3]  # 去掉.py后缀
            # 使用 importlib 动态导入模块
            module = importlib.import_module(f"app.routes.{module_name}")
            logger.info(f"Loaded route module: {module.__name__}")
            
load_routes()

app = create_app(os.getenv('FLASK_CONFIG') or 'default')

@app.route('/')
def index():
    # 返回 Vue 前端页面
    return app.send_static_file('index.html')


logger.info('Server started')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(401)
def unauthorized(error):
    if '/logout' in request.path:
        return jsonify({"code": 200, "msg": "success"}), 200
    
    return jsonify({"code": 401, "msg": "Unauthorized access, please login again."}), 200

@app.before_request
def before():
    # print("请求地址：" + str(request.path))
    # print("请求方法：" + str(request.method))
    # print("---请求headers--start--")
    # print(str(request.headers).rstrip())
    # print("---请求headers--end----")
    # print("GET参数：" + str(request.args))
    # print("POST参数：" + str(request.form))

    session.modified = True

    url = request.path  # 当前请求的URL
    passUrl = ["/login"]
    if url in passUrl:
        pass
    # else:
    #     return jsonify({'msg': '当前操作没有权限', 'code': 403})
    #     _id = session.get("_id", None)
    #     if not _id:
    #         return jsonify(401, {"msg": "认证失败，无法访问系统资源"})
    #     else:
    #         pass
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)