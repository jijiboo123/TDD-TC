"""鉴权：拿 token、错误凭据、缺失/错误 token 的拒绝路径。"""

import allure
import requests

pytestmark = allure.feature("接口 · 鉴权")


def test_auth_returns_token(base_url):
    response = requests.post(f"{base_url}/auth", json={"username": "admin", "password": "password123"})
    assert response.status_code == 200
    assert response.json().get("token")


def test_auth_wrong_password_returns_401(base_url):
    response = requests.post(f"{base_url}/auth", json={"username": "admin", "password": "wrong"})
    assert response.status_code == 401


def test_auth_reason_is_reported(base_url):
    response = requests.post(f"{base_url}/auth", json={"username": "admin", "password": "wrong"})
    assert response.json().get("reason") == "Bad credentials"


def test_create_without_token_is_forbidden(base_url, booking_payload):
    response = requests.post(f"{base_url}/booking", json=booking_payload)
    assert response.status_code == 403


def test_create_with_wrong_token_is_forbidden(base_url, booking_payload):
    response = requests.post(
        f"{base_url}/booking", json=booking_payload, headers={"Authorization": "Bearer nope"})
    assert response.status_code == 403


def test_delete_without_token_is_forbidden(base_url, created_booking):
    response = requests.delete(f"{base_url}/booking/{created_booking['id']}")
    assert response.status_code == 403