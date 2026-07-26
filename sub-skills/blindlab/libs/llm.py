# -*- coding: utf-8 -*-
"""LLM 适配器：OpenAI 兼容 chat 接口。只负责调用与重试，不含提示词业务。"""
import time

import requests

from config import settings

# 直连：不读系统代理环境变量
_session = requests.Session()
_session.trust_env = False


class LLMError(Exception):
    pass


class LLMClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None,
                 model: str | None = None):
        self.api_key = api_key or settings.LLM_API_KEY
        self.base = (base_url or settings.LLM_BASE_URL).rstrip("/")
        self.model = model or settings.LLM_MODEL

    def chat(self, system: str, user: str, temperature: float | None = None,
             max_tokens: int | None = None) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": settings.LLM_TEMPERATURE if temperature is None else temperature,
            "max_tokens": settings.LLM_MAX_TOKENS if max_tokens is None else max_tokens,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        last_err: Exception | None = None
        for attempt in range(3):
            try:
                r = _session.post(self.base + "/chat/completions", json=payload,
                                  headers=headers, timeout=90)
                if r.status_code != 200:
                    raise LLMError(f"HTTP {r.status_code}: {r.text[:200]}")
                data = r.json()
                return data["choices"][0]["message"]["content"].strip()
            except (requests.RequestException, LLMError, KeyError, ValueError) as e:
                last_err = e
                time.sleep(2 + attempt * 2)
        raise LLMError(f"LLM 调用失败: {last_err}")
