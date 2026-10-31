from ..base import base
from ..models import Resource
from ..models import Role
from ..models import User
from ..models import Organization
from flask import g, jsonify, request
from flask_login import current_user, login_required
import json
from .. import db
from flask import render_template
from datetime import datetime
import uuid
from .. import permission
from ..security import transactional
from ..operationlog import log_operation


def _is_descendant(node, candidate):
    """判断 candidate 是否位于 node 的子树中（含自身），用于阻止部门树成环。"""
    current = candidate
    seen = set()
    while current is not None and current.ID not in seen:
        seen.add(current.ID)
        if current.ID == node.ID:
            return True
        current = current.parent
    return False


def _validate_parent(org, parent_id):
    """返回 (parent, error_response)，parent_id 为空表示根节点。"""
    if not parent_id:
        return None, None
    parent = Organization.query.get(parent_id)
    if parent is None:
        return None, (jsonify({'code': 404, 'msg': '上级部门不存在'}), 404)
    if _is_descendant(org, parent):
        return None, (jsonify({'code': 409, 'msg': '上级部门不能是自身或其子部门'}), 409)
    return parent, None

@base.route('/system/dept/list', methods=['GET'])
@login_required
@permission('system:dept:list')
def syorganization_treeGrid():
    filters = []
    if 'deptName' in request.args:
        filters.append(Organization.NAME.like('%' + request.args['deptName'] + '%'))
    if 'status' in request.args:
        filters.append(Organization.STATUS == request.args['status'])        

    orgs = Organization.query.filter(*filters)

    return jsonify({'msg': '操作成功', 'code': 200, "data": [org.to_json() for org in orgs]})

@base.route('/system/dept/treeselect', methods=['GET'])
@login_required
@permission('system:dept:list')
def syorganization_tree_select():
    orgs = Organization.query.filter(Organization.SYORGANIZATION_ID == None)

    return jsonify({'msg': '操作成功', 'code': 200, "data": [org.to_tree_select_json() for org in orgs]}) 

@base.route('/system/dept/list/exclude/<id>', methods=['GET'])
@login_required
@permission('system:dept:list')
def syorganization_dept_list_exclude(id):
    orgs = Organization.query.filter(Organization.ID != id)

    return jsonify({'msg': '操作成功', 'code': 200, "data": [org.to_json() for org in orgs]})

@base.route('/system/dept/<string:id>', methods=['GET'])
@login_required
@permission('system:dept:query')
def syorganization_getById(id):
    org = Organization.query.get(id)

    if org:
        return jsonify({'msg': '操作成功', 'code': 200, 'data': org.to_json()})
    else:
        return jsonify({'success': False, 'msg': 'error'})

@base.route('/system/dept', methods=['PUT'])
@login_required
@permission('system:dept:edit')
@log_operation('修改部门')
@transactional
def syorganization_update():
    org = Organization.query.get(request.json.get('deptId'))
    if org is None:
        return jsonify({'code': 404, 'msg': '部门不存在'}), 404

    if 'parentId' in request.json:
        parent, error = _validate_parent(org, request.json['parentId'])
        if error:
            return error
        org.parent = parent

    org.UPDATEDATETIME = datetime.now()
    if 'deptName' in request.json:  org.NAME = request.json['deptName']
    if 'email' in request.json: org.EMAIL = request.json['email']
    if 'leader' in request.json: org.LEADER = request.json['leader']
    if 'phone' in request.json: org.PHONE = request.json['phone']
    if 'orderNum' in request.json:  org.SEQ = request.json['orderNum']
    if 'status' in request.json: org.STATUS = request.json['status']

    db.session.add(org)

    return jsonify({'code': 200, 'msg': '操作成功'})

@base.route('/system/dept', methods=['POST'])
@login_required
@permission('system:dept:add')
@log_operation('新增部门')
@transactional
def syorganization_save():
    org = Organization()
    org.ID = str(uuid.uuid4())

    if 'parentId' in request.json:
        parent, error = _validate_parent(org, request.json['parentId'])
        if error:
            return error
        org.parent = parent

    if 'deptName' in request.json:  org.NAME = request.json['deptName']
    if 'email' in request.json: org.EMAIL = request.json['email']
    if 'leader' in request.json: org.LEADER = request.json['leader']
    if 'phone' in request.json: org.PHONE = request.json['phone']
    if 'orderNum' in request.json: org.SEQ = request.json['orderNum']
    if 'status' in request.json: org.STATUS = request.json['status']

    # add organization to current user
    current_user.organizations.append(org)

    db.session.add(org)

    return jsonify({'code': 200, 'msg': '操作成功'})

@base.route('/system/dept/<string:id>', methods=['DELETE'])
@login_required
@permission('system:dept:remove')
@log_operation('删除部门')
@transactional
def sydept_delete(id):
    org = Organization.query.get(id)
    if org is None:
        return jsonify({'code': 404, 'msg': '部门不存在'}), 404
    if org.children.count() > 0:
        return jsonify({'code': 409, 'msg': '存在子部门，不能删除'}), 409
    if org.users.count() > 0:
        return jsonify({'code': 409, 'msg': '部门下仍有用户，不能删除'}), 409

    db.session.delete(org)

    return jsonify({'code': 200, 'msg': '操作成功'})
