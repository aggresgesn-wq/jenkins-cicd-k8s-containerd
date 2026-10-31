from ..base import base
from ..models import OnLine
from flask import render_template, request, jsonify
from sqlalchemy import asc
from sqlalchemy import desc
import flask_excel as excel
from flask_login import login_required
from .. import permission
from ..security import transactional
from ..operationlog import log_operation
from .. import db

@base.route('/monitor/logininfor/list', methods=['GET'])
@login_required
@permission('monitor:logininfor:list')
def grid_online():
    filters = []
    if request.args.get('loginName'):
        filters.append(OnLine.LOGINNAME.like('%' + request.args.get('loginName') + '%'))
    if request.args.get('ipaddr'):
        filters.append(OnLine.IP.like('%' + request.args.get('ipaddr') + '%'))
    if request.args.get('type'):
        filters.append(OnLine.TYPE == request.args.get('type'))
    if 'params[beginTime]' in request.args and 'params[endTime]' in request.args:
        filters.append(OnLine.CREATEDATETIME >  request.args['params[beginTime]'])
        filters.append(OnLine.CREATEDATETIME <  request.args['params[endTime]'])

    order_by = []
    if request.args.get('orderByColumn'):
        if request.args.get('isAsc') == 'ascending':
            order_by.append(asc(getattr(OnLine,request.args.get('orderByColumn').upper())))
        elif request.args.get('isAsc') == 'descending':
            order_by.append(desc(getattr(OnLine,request.args.get('orderByColumn').upper())))
        else:
            order_by.append(getattr(OnLine,request.args.get('orderByColumn').upper()))

    page = request.args.get('pageNum', 1, type=int)
    rows = request.args.get('pageSize', 10, type=int)
    pagination = OnLine.query.filter(*filters).order_by(*order_by).paginate(
        page=page, per_page=rows, error_out=False)
    onlines = pagination.items

    return jsonify({'total': pagination.total, 'rows': [online.to_json() for online in onlines], 'code': 200})

@base.route('/base/syonline/export', methods=['POST'])
@login_required
@permission('monitor:logininfor:export')
@transactional
def online_export():
    rows = []
    rows.append(['登录名', 'IP地址', '创建时间', '类别'])

    onlines = OnLine.query.all()
    for online in onlines:
        row = []
        row.append(online.LOGINNAME)
        row.append(online.IP)
        row.append(online.CREATEDATETIME)
        if online.TYPE == '0':
            row.append('注销系统')
        elif online.TYPE == '1':
            row.append('登录系统')
        rows.append(row)

    return excel.make_response_from_array(rows, "csv",
                                          file_name="online")


@base.route('/monitor/logininfor/<string:ids>', methods=['DELETE'])
@login_required
@permission('monitor:logininfor:remove')
@log_operation('删除登录日志')
@transactional
def logininfor_delete(ids):
    for log_id in ids.split(','):
        row = OnLine.query.get(log_id)
        if row:
            db.session.delete(row)

    return jsonify({'code': 200, 'msg': '操作成功'})


@base.route('/monitor/logininfor/clean', methods=['DELETE'])
@login_required
@permission('monitor:logininfor:remove')
@log_operation('清空登录日志')
@transactional
def logininfor_clean():
    OnLine.query.delete()

    return jsonify({'code': 200, 'msg': '操作成功'})


@base.route('/monitor/online/list', methods=['GET'])
@login_required
@permission('monitor:online:list')
def online_list():
    """在线用户：按登录名聚合最近一次登录记录。

    应用使用无状态 Session Cookie，服务端不维护会话表，因此这里展示的是
    “最近登录历史”，强制下线只会清理记录，不会立即吊销浏览器中的 Session。
    """
    rows = []
    login_names = [row[0] for row in db.session.query(OnLine.LOGINNAME).distinct().all()]
    for login_name in login_names:
        last = (
            OnLine.query.filter_by(LOGINNAME=login_name)
            .order_by(OnLine.CREATEDATETIME.desc())
            .first()
        )
        if last is None:
            continue
        rows.append({
            'tokenId': last.ID,
            'userName': last.LOGINNAME,
            'deptName': '',
            'ipaddr': last.IP,
            'loginLocation': last.LOCATION,
            'browser': last.BROWSER,
            'os': last.OS,
            'loginTime': last.CREATEDATETIME.strftime('%Y-%m-%d %H:%M:%S') if last.CREATEDATETIME else '',
        })

    return jsonify({'code': 200, 'msg': '操作成功', 'rows': rows, 'total': len(rows)})


@base.route('/monitor/online/<string:token_id>', methods=['DELETE'])
@login_required
@permission('monitor:online:forceLogout')
@log_operation('强制下线')
@transactional
def online_force_logout(token_id):
    row = OnLine.query.get(token_id)
    if row is not None:
        db.session.delete(row)

    return jsonify({'code': 200, 'msg': '操作成功'})
