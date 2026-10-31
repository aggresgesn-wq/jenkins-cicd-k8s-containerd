# coding:utf-8
from ..base import base
from ..models import User, Organization, Role, OnLine, Config
from flask import render_template, request
from flask import g, jsonify
import hashlib
import hmac
from flask_login import login_user, logout_user, login_required, \
    current_user
from flask import session
from datetime import datetime
from .. import  db
import uuid
from sqlalchemy import asc, true
from sqlalchemy import desc
from sqlalchemy import text
import flask_excel as excel
from .. import permission
from ..security import AVATAR_ALLOWED_TYPES, AVATAR_MAX_BYTES, login_throttle, rotate_csrf_token
from ..operationlog import log_operation
import os
from .. import captcha
from flask import send_from_directory
from werkzeug.utils import secure_filename
import ipaddress
from concurrent.futures import ThreadPoolExecutor
import threading
from flask import current_app
from app import setup_logger
from ..security import transactional

logger = setup_logger(__name__)

@base.route('/system/user/authRole', methods=['PUT'])
@login_required
@permission('system:role:edit')
@transactional
def grant_user_role():
    id = request.args['userId']
    ids = request.args['roleIds']

    user = User.query.get(id)

    if not ids:
        user.roles = []
    else:
        idList = ids.split(',')
        user.roles = [Role.query.get(rid) for rid in idList]

    db.session.add(user)

    return jsonify({'code': 200, 'msg': '操作成功'})

def update_location_async(app, online_id, ip):
    """异步更新位置信息"""
    with app.app_context():
        try:
            location = get_location_from_ip(ip)
            online = OnLine.query.get(online_id)
            if online:
                online.LOCATION = location
                db.session.commit()
        except Exception as e:
            logger.error(f"更新位置信息失败: {e}")

@login_required
def record_login_history(type):
    online = OnLine()
    online.LOGINNAME = current_user.LOGINNAME
    online.IP = request.remote_addr
    online.TYPE = type
    user_agent = request.headers.get('User-Agent')
    online.OS = get_os_from_user_agent(user_agent)
    online.BROWSER = get_browser_from_user_agent(user_agent)
    
    # 如果是内网IP，直接设置位置
    if is_private_ip(request.remote_addr):
        online.LOCATION = "内网IP"
    else:
        online.LOCATION = "查询中..."
        
    db.session.add(online)
    db.session.commit()
    
    # 只有外网IP才启动异步查询
    if not is_private_ip(request.remote_addr):
        executor = ThreadPoolExecutor(max_workers=1)
        executor.submit(update_location_async, current_app._get_current_object(), online.ID, request.remote_addr)
    
def is_private_ip(ip):
    """判断是否为内网IP"""
    try:
        return ipaddress.ip_address(ip).is_private
    except ValueError:
        return False

def get_location_from_ip(ip):
    """Get location string from IP address"""
    if is_private_ip(ip):
        return "内网IP"
    
    try:
        import requests
        response = requests.get(f'http://whois.pconline.com.cn/ipJson.jsp?ip={ip}&json=true')
        data = response.json()
        return f"{data.get('pro', '')} {data.get('city', '')}" if data.get('pro', '') else data.get('addr', 'XX XX')
    except Exception:
        return "XX XX"    

def get_os_from_user_agent(user_agent):
    """Extract OS info from User-Agent string"""
    if 'Windows' in user_agent:
        return 'Windows'
    elif 'Mac OS' in user_agent:
        return 'Mac OS'
    elif 'Linux' in user_agent:
        return 'Linux'
    elif 'Android' in user_agent:
        return 'Android'
    elif 'iOS' in user_agent:
        return 'iOS'
    else:
        return 'Unknown'

def get_browser_from_user_agent(user_agent):
    """Extract browser info from User-Agent string"""
    if 'Chrome' in user_agent:
        return 'Chrome'
    elif 'Firefox' in user_agent:
        return 'Firefox'
    elif 'Safari' in user_agent:
        return 'Safari'
    elif 'Edge' in user_agent:
        return 'Edge'
    elif 'MSIE' in user_agent or 'Trident' in user_agent:
        return 'Internet Explorer'
    else:
        return 'Unknown'

@base.route('/logout', methods=['POST'])
@login_required
@transactional
def do_logout():
    record_login_history(0)
    logout_user()
    session.clear()
    return jsonify({'success': True})

@base.route('/login', methods=['POST'])
@transactional
def do_login():
    payload = request.get_json(silent=True) or {}
    username = (payload.get('username') or '').strip()
    password = payload.get('password') or ''

    if not username or not password:
        return jsonify({'code': 400, 'msg': '用户名和密码不能为空'}), 400

    if login_throttle.locked(username):
        return jsonify({'code': 429, 'msg': '登录失败次数过多，请稍后再试'}), 429

    config = Config.query.filter(Config.config_key == 'sys.account.captchaOnOff').first()
    if config and config.config_value == 'true':
        code = payload.get('code', '')
        if captcha.config.get('ONLY_UPPERCASE') is True:
            code = code.upper()

        if not captcha.verify(code, payload.get('uuid', '')):
            return jsonify({'msg': '验证码错误~', 'code': 400}), 400

    user = User.query.filter_by(LOGINNAME=username).first()

    # 账号不存在、未激活、密码错误统一返回同一条消息，避免账号枚举
    if user is None or user.STATUS != '0':
        login_throttle.register_failure(username)
        return jsonify({'msg': '登录失败,账号密码错误~', 'code': 401}), 401

    salt = bytes.fromhex(user.SALT)
    expected = hash_password(password, salt).hex()
    if not hmac.compare_digest(expected, user.PWD or ''):
        login_throttle.register_failure(username)
        return jsonify({'msg': '登录失败,账号密码错误~', 'code': 401}), 401

    login_throttle.reset(username)
    session.clear()  # 防会话固定
    login_user(user)
    rotate_csrf_token()
    record_login_history(1)
    return jsonify({'msg': '登录成功~', 'code': 200, 'url': '/'})

@base.route('/system/user/list', methods=['GET'])
@login_required
@permission('system:user:list')
def user_grid():
    filters = []
    if 'userName' in request.args:
        filters.append(User.LOGINNAME.like('%' + request.args['userName'] + '%'))
    if 'phonenumber' in request.args:
        filters.append(User.PHONENUMBER.like('%' + request.args['phonenumber'] + '%'))
    if 'status' in request.args:
        filters.append(User.STATUS == request.args['status'])
    if 'params[beginTime]' in request.args and 'params[endTime]' in request.args:
        filters.append(User.CREATEDATETIME >  request.args['params[beginTime]'])
        filters.append(User.CREATEDATETIME <  request.args['params[endTime]'])

    order_by = []
    if request.form.get('sort'):
        if request.form.get('order') == 'asc':
            order_by.append(asc(getattr(User,request.form.get('sort').upper())))
        elif request.form.get('order') == 'desc':
            order_by.append(desc(getattr(User,request.form.get('sort').upper())))
        else:
            order_by.append(getattr(User,request.form.get('sort').upper()))

    page = request.args.get('pageNum', 1, type=int)
    rows = request.args.get('pageSize', 10, type=int)
    if 'deptId' in request.args:
        # Define a recursive CTE
        dept_cte = (
            db.session.query(Organization.ID)
            .filter(Organization.ID == request.args['deptId'])
            .cte('dept_tree', recursive=True)
        )
        
        # Recursive part of the CTE
        dept_cte = dept_cte.union_all(
            db.session.query(Organization.ID)
            .join(dept_cte, Organization.SYORGANIZATION_ID == dept_cte.c.ID)
        )
        pagination = User.query.join(Organization, User.organizations).join(
            dept_cte, Organization.ID == dept_cte.c.ID).filter(*filters).params(
            dept_id=request.args['deptId']).order_by(*order_by).paginate(
            page=page, per_page=rows, error_out=False)
    else:
        pagination = User.query.filter(*filters).order_by(*order_by).paginate(
            page=page, per_page=rows, error_out=False)
    users = pagination.items

    return jsonify({'rows': [user.to_json() for user in users], 'total': pagination.total, 'code': 200, 'msg': '查询成功'})

@base.route('/system/user/', methods=['GET'])
@login_required
@permission('system:user:list')
def syuser_get():
    json = {'code': 200, 'msg': ''}
    json['roles'] = [role.to_json() for role in Role.query.all()]
    json['posts'] = []
    return jsonify(json)

@base.route('/system/user/<id>', methods=['GET'])
@login_required
@permission('system:user:query')
def syuser_getById(id):
    user = User.query.get(id)

    if user:
        json = {'code': 200, 'msg': '', 'data': user.to_json()}
        if len(user.roles.all()) > 0:
            json['roles'] = [role.to_json() for role in user.roles]
            json['roleIds'] = [role.ID for role in user.roles]

        return jsonify(json)
    else:
        return jsonify({'success': False, 'msg': 'error'})

@base.route('/system/user', methods=['PUT'])
@login_required
@permission('system:user:edit')
@transactional
def syuser_update():
    id = request.json['userId']
    userName = request.json['userName']
    
    # if User.query.filter(User.LOGINNAME == loginname).filter(User.ID != id).first():
    #     return jsonify({'code': 201, 'msg': '更新用户失败，用户名已存在！'})

    user = User.query.get(id)

    user.UPDATEDATETIME = datetime.now()
    if 'status' in request.json: user.STATUS = request.json['status']
    if 'nickName' in request.json: user.NAME = request.json['nickName'] 
    if 'sex' in request.json: user.SEX = request.json['sex']
    if 'email' in request.json: user.EMAIL = request.json['email']
    if 'phonenumber' in request.json: user.PHONENUMBER = request.json['phonenumber']
    if 'deptId' in request.json: user.organizations = Organization.query.filter(Organization.ID == request.json['deptId']).all()
    if 'roleIds' in request.json:
        user.roles = [Role.query.get(roleId) for roleId in request.json['roleIds']]

    db.session.add(user)

    return jsonify({'code': 200, 'msg': '更新成功！'})

def generate_salt(length=16):
    """生成随机盐"""
    return os.urandom(length)

def hash_password(password, salt):
    """使用PBKDF2算法加密密码"""
    return hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'), salt, 100000)

@base.route('/system/user', methods=['POST'])
@login_required
@permission('system:user:add')
@transactional
def syuser_save():
    if User.query.filter_by(LOGINNAME = request.json['userName']).first():
        return jsonify({'success': False, 'msg': '新建用户失败，用户名已存在！'})

    user = User()

    user.ID = str(uuid.uuid4())
    salt = generate_salt()
    user.SALT = salt.hex()
    user.PWD = hash_password(request.json['password'], salt).hex()

    with db.session.no_autoflush:
        if 'nickName' in request.json: user.NAME = request.json['nickName'] 
        if 'sex' in request.json: user.SEX = request.json['sex']
        if 'email' in request.json: user.EMAIL = request.json['email']
        if 'phonenumber' in request.json: user.PHONENUMBER = request.json['phonenumber']
        if 'deptId' in request.json: user.organizations = Organization.query.filter(Organization.ID == request.json['deptId']).all()
        if 'roleIds' in request.json:
            user.roles = [Role.query.get(roleId) for roleId in request.json['roleIds']]

        user.LOGINNAME = request.json['userName']

        # add current use to new user
        #current_user.roles.append(user)

        db.session.add(user)

    return jsonify({'code': 200, 'msg': '新建用户成功！'})

@base.route('/register', methods=['POST'])
@transactional
def syuser_register():
    if User.query.filter_by(LOGINNAME = request.json['username']).first():
        return jsonify({'success': False, 'msg': '注册用户失败，用户名已存在！'})

    user = User()

    user.ID = str(uuid.uuid4())
    salt = generate_salt()
    user.SALT = salt.hex()
    user.PWD = hash_password(request.json['password'], salt).hex()

    with db.session.no_autoflush:
        user.NAME = request.json['username']
        user.roles = Role.query.filter(Role.NAME == '只读用户').all()

        user.LOGINNAME = request.json['username']
        user.NAME = user.LOGINNAME
        user.STATUS = '0'

        db.session.add(user)
        db.session.commit()

    return jsonify({'code': 200, 'msg': '注册用户成功！'})

@base.route('/system/user/<id>', methods=['DELETE'])
@login_required
@permission('system:user:remove')
@transactional
def syuser_delete(id):
    user = User.query.get(id)
    if user:
        db.session.delete(user)

    return jsonify({'code': 200, 'msg': '删除成功'})

@base.route('/system/user/profile/updatePwd', methods=['PUT'])
@login_required
@log_operation('修改密码')
@transactional
def syuser_update_pwd():
    # 密码走请求体（JSON/form），不再从 URL 查询参数读取，避免被访问日志记录
    payload = request.get_json(silent=True) or request.form or request.args
    old_password = payload.get('oldPassword') or ''
    new_password = payload.get('newPassword') or ''

    if len(new_password) < 8:
        return jsonify({'code': 400, 'msg': '新密码长度不能少于 8 位'}), 400

    user = User.query.get(current_user.ID)

    if user:
        salt = bytes.fromhex(user.SALT)
        hash = hash_password(old_password, salt).hex()
        if not hmac.compare_digest(hash, user.PWD or ''):
            return jsonify({'code': 400, 'msg': '旧密码错误'}), 400

        user.PWD = hash_password(new_password, salt).hex()
        db.session.add(user)
    return jsonify({'code': 200, 'msg': '修改成功'})

@base.route('/getInfo', methods=['GET'])
@login_required
def syuser_info():
    resources = []
    resourceTree = []

    resources += [res for org in current_user.organizations for res in org.resources if org.resources]
    resources += [res for role in current_user.roles for res in role.resources if role.resources]
    
    # remove repeat
    new_dict = dict()
    for obj in resources:
        if obj.ID not in new_dict:
            new_dict[obj.ID] = obj

    for resource in new_dict.values():
        resourceTree.append(resource.PERMS)

    return jsonify({'msg': '登录成功~', 'code': 200, \
        'user': {'userName': current_user.LOGINNAME, 'avatar': '', 'nickName': current_user.NAME, 'userId': current_user.ID}, \
        'roles': [role.NAME for role in current_user.roles], 'permissions': resourceTree})

@base.route('/system/user/profile', methods=['GET'])
@login_required
def syuser_profile():
     return jsonify({'msg': '操作成功', 'code': 200, \
        'data': current_user.to_json(), \
        'postGroup': current_user.organizations[0].NAME if len(current_user.organizations) > 0 else '', \
        'roleGroup': [role.NAME for role in current_user.roles]})

@base.route('/system/user/profile', methods=['PUT'])
@login_required
@transactional
def syuser_update_profile():
    # 只能修改当前登录用户自己的资料：忽略客户端传入的 userId/userName，
    # 否则任何登录用户都能改别人的邮箱、手机号。
    payload = request.get_json(silent=True) or {}
    user = User.query.get(current_user.ID)

    user.UPDATEDATETIME = datetime.now()
    if 'nickName' in payload: user.NAME = payload['nickName']
    if 'sex' in payload: user.SEX = payload['sex']
    if 'email' in payload: user.EMAIL = payload['email']
    if 'phonenumber' in payload: user.PHONENUMBER = payload['phonenumber']

    db.session.add(user)

    return jsonify({'code': 200, 'msg': '更新成功！'})

@base.route('/system/user/authRole/<id>', methods=['GET'])
@login_required
@permission('system:user:query')
def syuser_auth_role(id):
    user = User.query.get(id)
    userRoles = [role for role in user.roles]
    allRoles = Role.query.all()
    for allRole in allRoles:
        for userRole in userRoles:
            if userRole.ID == allRole.ID:
                allRole.flag = True

    return jsonify({'code': 200, 'msg': '操作成功', 'roles': [role.to_json() for role in allRoles], 'user': user.to_json()})

@base.route('/base/syuser/export', methods=['POST'])
@login_required
@permission('system:user:export')
@transactional
def user_export():
    rows = []
    rows.append(['登录名', '姓名', '创建时间', '修改时间', '性别'])

    users = User.query.all()
    for user in users:
        row = []
        row.append(user.LOGINNAME)
        row.append(user.NAME)
        row.append(user.CREATEDATETIME)
        row.append(user.UPDATEDATETIME)
        if user.SEX == '0':
            row.append('女')
        elif user.SEX == '1':
            row.append('男')
        rows.append(row)

    return excel.make_response_from_array(rows, "csv",
                                          file_name="user")


@base.route('/system/user/changeStatus', methods=['PUT'])
@login_required
@permission('system:user:edit')
@transactional
def syuser_status_update():
    user = User.query.get(request.json['userId'])

    if 'status' in request.json: user.STATUS = request.json['status']

    db.session.add(user)

    return jsonify({'code': 200, 'msg': '操作成功'})

def _detect_image_type(raw: bytes):
    """按文件头判断真实图片类型，不信任客户端文件名与 Content-Type。"""
    if raw.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if raw.startswith(b"GIF87a") or raw.startswith(b"GIF89a"):
        return "gif"
    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "webp"
    return None


@base.route('/system/user/profile/avatar', methods=['POST'])
@login_required
@transactional
def syuser_avatar_update():
    if 'avatarfile' not in request.files:
        return jsonify({'code': 400, 'msg': '未选择头像文件'}), 400

    file = request.files['avatarfile']
    raw = file.read(AVATAR_MAX_BYTES + 1)
    if not raw:
        return jsonify({'code': 400, 'msg': '上传文件为空'}), 400
    if len(raw) > AVATAR_MAX_BYTES:
        return jsonify({'code': 413, 'msg': '头像大小不能超过 2MB'}), 413

    image_type = _detect_image_type(raw)
    if image_type is None:
        return jsonify({'code': 415, 'msg': '仅支持 JPG/PNG/GIF/WebP 格式的图片'}), 415

    filename = f"{uuid.uuid4().hex}.{AVATAR_ALLOWED_TYPES[image_type]}"
    with open(os.path.join(get_upload_path(), filename), 'wb') as fh:
        fh.write(raw)

    current_user.PHOTO = '/system/user/profile/avatar/' + filename
    db.session.add(current_user)
    db.session.commit()

    return jsonify({'msg': '操作成功', 'code': 200, 'imgUrl': current_user.PHOTO})

@base.route('/system/user/profile/avatar/<filename>', methods=['GET'])
@login_required
def sysuser_avatar_preview(filename):
    try:
        filename = secure_filename(filename)
        response = send_from_directory(get_upload_path(), filename, as_attachment=False)
            # 根据文件扩展名设置 MIME 类型
        if filename.endswith('.jpg') or filename.endswith('.jpeg'):
            response.headers['Content-Type'] = 'image/jpeg'
        elif filename.endswith('.png'):
            response.headers['Content-Type'] = 'image/png'
        return response
    except FileNotFoundError: 
        return jsonify({'msg': '文件不存在', 'code': 404})   

def get_upload_path():
    parent = os.path.dirname(os.path.abspath(__file__))
    parent = os.path.dirname(parent)
    parent = os.path.dirname(parent)

    path = os.path.join(parent, "uploads")
    if not os.path.exists(path):
        os.makedirs(path)
    return path
