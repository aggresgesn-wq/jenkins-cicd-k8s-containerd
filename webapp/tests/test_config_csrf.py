"""配置项匿名访问、CSRF 双提交校验。"""

from conftest import auth_client


def test_public_config_key_is_readable_anonymously(client):
    response = client.get("/prod-api/system/config/configKey/sys.account.captchaOnOff")

    assert response.status_code == 200
    assert response.get_json()["msg"] == "false"


def test_sensitive_config_key_requires_login(client):
    response = client.get("/prod-api/system/config/configKey/sys.secret.token")

    assert response.status_code == 401


def test_sensitive_config_key_forbidden_for_readonly_user(client):
    auth_client(client, "viewer")

    response = client.get("/prod-api/system/config/configKey/sys.secret.token")

    assert response.status_code == 403


def test_sensitive_config_key_readable_by_superadmin(client):
    auth_client(client, "super")

    response = client.get("/prod-api/system/config/configKey/sys.secret.token")

    assert response.status_code == 200
    assert response.get_json()["msg"] == "s3cr3t"


def test_write_without_csrf_header_is_rejected(client):
    auth_client(client, "super")

    response = client.post(
        "/prod-api/system/config",
        json={"configKey": "app.csrf", "configName": "csrf", "configValue": "1", "configType": 0},
    )

    assert response.status_code == 403
    assert "CSRF" in response.get_json()["msg"]


def test_write_with_csrf_header_succeeds(client):
    headers = auth_client(client, "super")

    response = client.post(
        "/prod-api/system/config",
        json={"configKey": "app.csrf", "configName": "csrf", "configValue": "1", "configType": 0},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.get_json()["code"] == 200


def test_unauthenticated_write_returns_401_not_csrf_error(client):
    response = client.post("/prod-api/system/config", json={"configKey": "app.x"})

    assert response.status_code == 401
