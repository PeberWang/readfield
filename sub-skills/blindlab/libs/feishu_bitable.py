# -*- coding: utf-8 -*-
"""飞书多维表格适配器：tenant token + bitable 建库/建字段/拉记录 + 授权。

只做 HTTP 封装与错误统一，不含业务逻辑。同步 requests 实现，避免异步复杂度。
"""
import json
import time
from pathlib import Path

import requests

from config import settings

# 国内服务直连：不读系统代理环境变量，避免现场网络环境代理抖动影响流程
_session = requests.Session()
_session.trust_env = False

# 触发频率限制的错误码（飞书会对超限请求进行慢响应/拒绝）
_RATE_LIMIT_CODES = {99991400, 99991401}


def _token_cache_path() -> Path:
    return settings.RESULTS_DIR / ".feishu_token_cache.json"


class FeishuError(Exception):
    """飞书 API 错误：code + msg。"""


class BitableClient:
    def __init__(self, app_id: str | None = None, app_secret: str | None = None):
        self.app_id = app_id or settings.FEISHU_APP_ID
        self.app_secret = app_secret or settings.FEISHU_APP_SECRET
        self.base = settings.FEISHU_BASE_URL.rstrip("/")
        self._token: str | None = None
        self._token_expire = 0.0

    # ---- 基础 ----
    def token(self) -> str:
        if self._token and time.time() < self._token_expire - 60:
            return self._token
        # 磁盘缓存：避免每次运行都请求 token（计入频率限制）
        cache_file = _token_cache_path()
        try:
            cache = json.loads(cache_file.read_text(encoding="utf-8"))
            if (cache.get("app_id") == self.app_id
                    and time.time() < cache.get("expire_at", 0) - 300):
                self._token = cache["token"]
                self._token_expire = cache["expire_at"]
                return self._token
        except (OSError, ValueError, KeyError):
            pass
        resp = self._raw_post("/auth/v3/tenant_access_token/internal", {
            "app_id": self.app_id, "app_secret": self.app_secret,
        }, auth=False)
        self._token = resp["tenant_access_token"]
        self._token_expire = time.time() + resp.get("expire", 7200)
        try:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(json.dumps({
                "app_id": self.app_id, "token": self._token,
                "expire_at": self._token_expire,
            }), encoding="utf-8")
        except OSError:
            pass
        return self._token

    def _request(self, method: str, path: str, auth: bool = True, **kwargs) -> dict:
        """统一传输层：网络错误重试 + 频率限制退避。返回完整响应体。"""
        headers = kwargs.pop("headers", {})
        headers.setdefault("Content-Type", "application/json; charset=utf-8")
        # 禁 keep-alive：本机 urllib3 在 Python 3.14 下读超时疑似失效，
        # 连接复用会踩「服务端静默断连后读挂死」的坑，每次新连接最稳
        headers["Connection"] = "close"
        if auth:
            headers["Authorization"] = f"Bearer {self.token()}"
        last_err: Exception | None = None
        for attempt in range(6):
            try:
                r = _session.request(method, self.base + path, headers=headers,
                                     timeout=10, **kwargs)
                data = r.json()
            except (requests.RequestException, ValueError) as e:
                last_err = e
                time.sleep(1 + attempt)
                continue
            if data.get("code") in _RATE_LIMIT_CODES:
                wait = min(5 * (attempt + 1), 30)
                time.sleep(wait)
                continue
            return data
        raise FeishuError(f"{method} {path} 重试后仍失败: {last_err or '频率限制'}")

    def _raw_post(self, path: str, payload: dict, auth: bool = True) -> dict:
        """Return full raw JSON response including code and msg."""
        return self._request("POST", path, auth=auth, json=payload)

    def _post(self, path: str, payload: dict, auth: bool = True) -> dict:
        data = self._raw_post(path, payload, auth=auth)
        if data.get("code") != 0:
            raise FeishuError(f"{path} 失败 code={data.get('code')} msg={data.get('msg')}")
        return data.get("data", {})

    def _get(self, path: str, params: dict | None = None) -> dict:
        data = self._request("GET", path, params=params)
        if data.get("code") != 0:
            raise FeishuError(f"{path} 失败 code={data.get('code')} msg={data.get('msg')}")
        return data.get("data", {})

    def _put(self, path: str, payload: dict) -> dict:
        data = self._request("PUT", path, json=payload)
        if data.get("code") != 0:
            raise FeishuError(f"{path} 失败 code={data.get('code')} msg={data.get('msg')}")
        return data.get("data", {})

    # ---- 多维表格 ----
    def create_app(self, name: str, folder_token: str | None = None) -> dict:
        payload = {"name": name}
        if folder_token:
            payload["folder_token"] = folder_token
        return self._post("/bitable/v1/apps", payload)["app"]

    def list_fields(self, app_token: str, table_id: str) -> list:
        items, page_token = [], None
        while True:
            params = {"page_size": 100}
            if page_token:
                params["page_token"] = page_token
            data = self._get(f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields", params)
            items.extend(data.get("items") or [])
            # 注意：飞书总会返回 page_token，终止条件必须看 has_more
            if not data.get("has_more"):
                return items
            page_token = data.get("page_token")

    def create_field(self, app_token: str, table_id: str, name: str, ftype: int,
                     prop: dict | None = None) -> dict:
        body = {"field_name": name, "type": ftype}
        if prop:
            body["property"] = prop
        return self._post(
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields",
            body,
        )["field"]

    def rename_field(self, app_token: str, table_id: str, field_id: str, name: str, ftype: int) -> dict:
        return self._put(
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields/{field_id}",
            {"field_name": name, "type": ftype},
        )["field"]

    def delete_field(self, app_token: str, table_id: str, field_id: str) -> None:
        data = self._request("DELETE",
                             f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields/{field_id}")
        if data.get("code") != 0:
            raise FeishuError(f"delete_field 失败 code={data.get('code')} msg={data.get('msg')}")

    def list_records(self, app_token: str, table_id: str) -> list:
        items, page_token = [], None
        while True:
            params = {"page_size": 500}
            if page_token:
                params["page_token"] = page_token
            data = self._get(f"/bitable/v1/apps/{app_token}/tables/{table_id}/records", params)
            items.extend(data.get("items") or [])
            # 注意：飞书总会返回 page_token，终止条件必须看 has_more
            if not data.get("has_more"):
                return items
            page_token = data.get("page_token")

    # ---- 权限（可选能力，无权限时静默降级，由上层提示）----
    def delete_app(self, app_token: str) -> bool:
        """删除整个多维表格（drive 接口）。失败返回 False。"""
        try:
            data = self._request("DELETE", f"/drive/v1/files/{app_token}?type=bitable")
            return data.get("code") == 0
        except FeishuError:
            return False

    def grant_full_access(self, app_token: str, open_id: str) -> bool:
        """把 bitable 的 full_access 授给用户。失败返回 False。"""
        try:
            self._post(
                "/drive/v1/permissions/" + app_token + "/members?type=bitable&need_notification=false",
                {"member_type": "openid", "member_id": open_id, "perm": "full_access"},
            )
            return True
        except FeishuError:
            return False
