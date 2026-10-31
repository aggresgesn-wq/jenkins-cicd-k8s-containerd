"""登录、会话与登录限流。"""

from conftest import PASSWORD, csrf_headers, login


def test_anonymous_request_gets_401(client):
    response = client.get("/prod-api/system/user/list")

    assert response.status_code == 401
    assert response.get_json()["code"] == 401


def test_login_success_returns_session(client):
    response = login(client, "admin1")

    assert response.status_code == 200
    assert response.get_json()["code"] == 200
    # 登录后 /getInfo 可以正常拿到用户信息
    info = client.get("/prod-api/getInfo")
    assert info.status_code == 200
    assert info.get_json()["user"]["userName"] == "admin1"


def test_login_response_does_not_leak_token(client):
    response = login(client, "admin1")

    assert "token" not in response.get_json()


def test_wrong_password_returns_401(client):
    response = login(client, "admin1", "wrong-password")

    assert response.status_code == 401
    assert response.get_json()["code"] == 401


def test_unknown_user_returns_same_message_as_wrong_password(client):
    unknown = login(client, "nobody", PASSWORD)
    wrong = login(client, "admin1", "wrong-password")

    assert unknown.status_code == wrong.status_code == 401
    assert unknown.get_json()["msg"] == wrong.get_json()["msg"]


def test_account_locked_after_repeated_failures(client):
    for _ in range(3):
        assert login(client, "admin1", "wrong-password").status_code == 401

    locked = login(client, "admin1", PASSWORD)
    assert locked.status_code == 429
    assert locked.get_json()["code"] == 429


def test_logout_clears_session(client):
    headers = csrf_headers(client) if login(client, "admin1").status_code == 200 else {}
    response = client.post("/prod-api/logout", headers=headers)

    assert response.status_code == 200
    assert client.get("/prod-api/getInfo").status_code == 401
