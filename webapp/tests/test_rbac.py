"""权限矩阵：普通用户调用管理接口必须 403，管理员只能做被授权的事。"""

from tests.conftest import auth_client


def test_readonly_cannot_list_users(client):
    auth_client(client, "viewer")

    response = client.get("/prod-api/system/user/list")

    assert response.status_code == 403
    assert response.get_json()["code"] == 403


def test_readonly_cannot_list_roles(client):
    auth_client(client, "viewer")

    assert client.get("/prod-api/system/role/list").status_code == 403


def test_readonly_cannot_assign_roles(client):
    headers = auth_client(client, "viewer")

    response = client.put(
        "/prod-api/system/role/authUser/selectAll?roleId=1&userIds=viewer", headers=headers
    )

    assert response.status_code == 403


def test_readonly_cannot_change_data_scope(client):
    headers = auth_client(client, "viewer")

    response = client.put(
        "/prod-api/system/role/dataScope", json={"roleId": 3, "dataScope": 1}, headers=headers
    )

    assert response.status_code == 403


def test_readonly_cannot_export_users(client):
    headers = auth_client(client, "viewer")

    response = client.post("/prod-api/base/syuser/export", headers=headers)

    assert response.status_code == 403


def test_admin_can_list_roles(client):
    auth_client(client, "admin1")

    assert client.get("/prod-api/system/role/list").status_code == 200


def test_admin_cannot_use_permissions_it_does_not_have(client):
    headers = auth_client(client, "admin1")

    response = client.post(
        "/prod-api/system/config",
        json={"configKey": "app.x", "configName": "x", "configValue": "1", "configType": 0},
        headers=headers,
    )

    assert response.status_code == 403


def test_superadmin_bypasses_permission_matrix(client):
    auth_client(client, "super")

    assert client.get("/prod-api/system/role/list").status_code == 200
    assert client.get("/prod-api/system/user/list").status_code == 200
