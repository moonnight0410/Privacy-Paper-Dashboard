from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from uuid import uuid4


def _post_form(url: str, data: dict, timeout: int = 45) -> dict:
    body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw)


def _post_json(url: str, data: dict, timeout: int = 45) -> dict:
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw)


def _configured(config: dict | None) -> bool:
    if not config or not config.get("enabled"):
        return False
    provider = (config.get("provider") or "").strip()
    if provider == "baidu":
        return bool((config.get("app_id") or "").strip() and (config.get("secret_key") or "").strip())
    if provider == "libretranslate":
        return bool((config.get("base_url") or "").strip())
    return False


def translate_text(text: str, config: dict | None, retries: int = 2) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    if not _configured(config):
        raise ValueError("Machine translation provider is not configured")

    provider = (config.get("provider") or "").strip()
    source_lang = (config.get("source_lang") or "en").strip()
    target_lang = (config.get("target_lang") or "zh").strip()
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            if provider == "baidu":
                return translate_baidu(text, config, source_lang, target_lang)
            if provider == "libretranslate":
                return translate_libretranslate(text, config, source_lang, target_lang)
            raise ValueError(f"Unsupported machine translation provider: {provider}")
        except (KeyError, json.JSONDecodeError, urllib.error.URLError, TimeoutError, ValueError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(1.2 * (attempt + 1))
                continue
            raise
    if last_error:
        raise last_error
    raise RuntimeError("Machine translation failed")


def translate_baidu(text: str, config: dict, source_lang: str, target_lang: str) -> str:
    app_id = (config.get("app_id") or "").strip()
    secret_key = (config.get("secret_key") or "").strip()
    endpoint = (config.get("base_url") or "https://fanyi-api.baidu.com/api/trans/vip/translate").strip()
    salt = uuid4().hex[:10]
    sign_raw = f"{app_id}{text}{salt}{secret_key}".encode("utf-8")
    sign = hashlib.md5(sign_raw).hexdigest()
    data = _post_form(
        endpoint,
        {
            "q": text,
            "from": source_lang,
            "to": target_lang,
            "appid": app_id,
            "salt": salt,
            "sign": sign,
        },
    )
    if data.get("error_code"):
        raise ValueError(f"Baidu Translate error {data.get('error_code')}: {data.get('error_msg')}")
    results = data.get("trans_result") or []
    return "\n".join(str(item.get("dst") or "").strip() for item in results if item.get("dst")).strip()


def translate_libretranslate(text: str, config: dict, source_lang: str, target_lang: str) -> str:
    endpoint = (config.get("base_url") or "https://libretranslate.com/translate").strip().rstrip("/")
    if not endpoint.endswith("/translate"):
        endpoint = f"{endpoint}/translate"
    payload = {
        "q": text,
        "source": source_lang,
        "target": target_lang,
        "format": "text",
    }
    api_key = (config.get("api_key") or "").strip()
    if api_key:
        payload["api_key"] = api_key
    data = _post_json(endpoint, payload)
    if data.get("error"):
        raise ValueError(f"LibreTranslate error: {data.get('error')}")
    translated = data.get("translatedText")
    if isinstance(translated, list):
        return "\n".join(str(item).strip() for item in translated if str(item).strip())
    return str(translated or "").strip()
