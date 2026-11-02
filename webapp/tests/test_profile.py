"""个人资料与头像上传：防越权修改、文件类型与大小校验。"""

import io

import app.routes.user as user_module
from tests.conftest import auth_client


def test_profile_update_cannot_modify_other_user(client, app):
    headers = auth_client(client, "viewer")

    response = client.put(
        "/prod-api/system/user/profile",
        json={"userId": "admin1", "userName": "admin1", "nickName": "hacked"},
        headers=headers,
    )

    assert response.status_code == 200
    from app.models import User

    with app.app_context():
        assert User.query.get("admin1").NAME == "admin1"
        assert User.query.get("viewer").NAME == "hacked"


def test_avatar_rejects_non_image(client):
    headers = auth_client(client, "viewer")

    response = client.post(
        "/prod-api/system/user/profile/avatar",
        data={"avatarfile": (io.BytesIO(b"plain text, not an image"), "shell.php")},
        headers=headers,
        content_type="multipart/form-data",
    )

    assert response.status_code == 415


def test_avatar_rejects_oversized_file(client):
    headers = auth_client(client, "viewer")
    payload = b"\x89PNG\r\n\x1a\n" + b"0" * (2 * 1024 * 1024 + 16)

    response = client.post(
        "/prod-api/system/user/profile/avatar",
        data={"avatarfile": (io.BytesIO(payload), "big.png")},
        headers=headers,
        content_type="multipart/form-data",
    )

    assert response.status_code == 413


def test_avatar_accepts_valid_png(client, tmp_path, monkeypatch):
    monkeypatch.setattr(user_module, "get_upload_path", lambda: str(tmp_path))
    headers = auth_client(client, "viewer")
    payload = b"\x89PNG\r\n\x1a\n" + b"0" * 64

    response = client.post(
        "/prod-api/system/user/profile/avatar",
        data={"avatarfile": (io.BytesIO(payload), "avatar.png")},
        headers=headers,
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    image_url = response.get_json()["imgUrl"]
    assert image_url.endswith(".png")
    assert (tmp_path / image_url.rsplit("/", 1)[-1]).exists()


def test_avatar_requires_login(client):
    response = client.post(
        "/prod-api/system/user/profile/avatar",
        data={"avatarfile": (io.BytesIO(b"\x89PNG\r\n\x1a\n"), "a.png")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 401
