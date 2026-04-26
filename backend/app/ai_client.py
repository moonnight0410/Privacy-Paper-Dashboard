from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

from .translation_client import translate_text


def chat_completions_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"


def compact_summary(summary: str, max_chars: int) -> str:
    summary = (summary or "").strip()
    if len(summary) <= max_chars:
        return summary
    head = summary[: max_chars // 2]
    tail = summary[-max_chars // 2 :]
    return f"{head}\n\n[摘要过长，中间内容已省略，请先基于保留内容压缩理解。]\n\n{tail}"


def build_prompt(article: dict, max_input_chars: int) -> str:
    reasons = article.get("reasons") or []
    summary = compact_summary(article.get("summary") or "", max_input_chars)
    return f"""
你是数据安全与隐私保护方向的学术论文筛选助手。请基于给定论文信息，完成英文摘要中文学术直译，并生成 3 条推荐理由。

输出必须是严格 JSON，不要 Markdown，不要额外解释：
{{
  "translated_title": "中文学术直译标题",
  "translated_summary": "中文学术直译摘要",
  "ai_recommendation": [
    "推荐理由1",
    "推荐理由2",
    "推荐理由3"
  ]
}}

翻译要求：
1. 使用中文学术直译风格，忠实保留技术含义。
2. 不要扩写不存在的信息。
3. 专有术语首次出现时可保留英文括注。
4. translated_title 翻译 title；如果 title 为空，translated_title 返回空字符串。
5. 如果摘要为空或信息不足，translated_summary 返回空字符串。

推荐理由要求：
1. 面向用户自己筛论文。
2. 只输出 3 条要点，每条 30-60 个中文字符左右。
3. 按重要性考虑：数据安全/隐私保护相关性；隐私计算、联邦学习、差分隐私、安全多方计算、同态加密等技术相关性；公安数据安全、政务数据治理、敏感数据保护场景潜在关系；是否适合作为论文选题或参考文献。
4. 不要夸大论文价值。相关性弱时如实说明。

论文信息：
title: {article.get("title") or ""}
source: {article.get("source") or ""}
source_type: {article.get("source_type") or ""}
published: {article.get("published") or ""}
score: {article.get("score") or ""}
reasons: {"；".join(str(item) for item in reasons)}
original English summary:
{summary}
""".strip()


def build_recommendation_prompt(article: dict, max_input_chars: int, translated_summary: str) -> str:
    reasons = article.get("reasons") or []
    summary = compact_summary(article.get("summary") or "", max_input_chars)
    translated_summary = compact_summary(translated_summary, max_input_chars)
    return f"""
你是数据安全与隐私保护方向的学术论文筛选助手。请基于给定论文信息，生成 3 条中文推荐理由。

输出必须是严格 JSON，不要 Markdown，不要额外解释：
{{
  "ai_recommendation": [
    "推荐理由1",
    "推荐理由2",
    "推荐理由3"
  ]
}}

推荐理由要求：
1. 面向用户自己筛论文。
2. 只输出 3 条要点，每条 30-60 个中文字符左右。
3. 按重要性考虑：数据安全/隐私保护相关性；隐私计算、联邦学习、差分隐私、安全多方计算、同态加密等技术相关性；公安数据安全、政务数据治理、敏感数据保护场景潜在关系；是否适合作为论文选题或参考文献。
4. 不要夸大论文价值。相关性弱时如实说明。

论文信息：
title: {article.get("title") or ""}
source: {article.get("source") or ""}
source_type: {article.get("source_type") or ""}
published: {article.get("published") or ""}
score: {article.get("score") or ""}
reasons: {"；".join(str(item) for item in reasons)}
Chinese summary:
{translated_summary}
original English summary:
{summary}
""".strip()


def parse_json_content(content: str) -> dict:
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end >= start:
        text = text[start : end + 1]
    data = json.loads(text)
    recommendation = data.get("ai_recommendation") or []
    if isinstance(recommendation, str):
        recommendation = [line.strip("- 0123456789.、") for line in recommendation.splitlines() if line.strip()]
    return {
        "translated_title": str(data.get("translated_title") or "").strip(),
        "translated_summary": str(data.get("translated_summary") or "").strip(),
        "ai_recommendation": [str(item).strip() for item in recommendation[:3] if str(item).strip()],
    }


def has_ai_config(ai_config: dict | None) -> bool:
    if not ai_config:
        return False
    return bool(
        (ai_config.get("api_key") or "").strip()
        and (ai_config.get("base_url") or "").strip()
        and (ai_config.get("model") or "").strip()
    )


def call_chat_json(prompt: str, ai_config: dict, retries: int = 2) -> dict:
    api_key = (ai_config.get("api_key") or "").strip()
    base_url = (ai_config.get("base_url") or "").strip()
    model = (ai_config.get("model") or "").strip()
    if not api_key or not base_url or not model:
        raise ValueError("AI provider, base URL, model, and API key are required")

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "你是严谨的中文学术翻译与论文筛选助手，只输出用户要求的 JSON。",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    url = chat_completions_url(base_url)
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=90) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            data = json.loads(raw)
            content = data["choices"][0]["message"]["content"]
            return parse_json_content(content)
        except (KeyError, json.JSONDecodeError, urllib.error.URLError, TimeoutError, ValueError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise
    if last_error:
        raise last_error
    raise RuntimeError("AI enrichment failed")


def enrich_article(article: dict, ai_config: dict | None, translation_config: dict | None = None, retries: int = 2) -> dict:
    max_input_chars = int((ai_config or {}).get("max_input_chars") or 6000)
    translated_title = ""
    translated_summary = ""
    ai_recommendation: list[str] = []

    if translation_config and translation_config.get("enabled"):
        translated_title = translate_text(article.get("title") or "", translation_config, retries=retries)
        translated_summary = translate_text(article.get("summary") or "", translation_config, retries=retries)

    if has_ai_config(ai_config):
        prompt = (
            build_recommendation_prompt(article, max_input_chars, translated_summary)
            if translated_summary
            else build_prompt(article, max_input_chars)
        )
        ai_result = call_chat_json(prompt, ai_config or {}, retries=retries)
        if not translated_title:
            translated_title = ai_result["translated_title"]
        if not translated_summary:
            translated_summary = ai_result["translated_summary"]
        ai_recommendation = ai_result["ai_recommendation"]
    elif not translated_title and not translated_summary:
        raise ValueError("AI config or machine translation config is required")
    else:
        ai_recommendation = article.get("ai_recommendation") or []

    return {
        "translated_title": translated_title,
        "translated_summary": translated_summary,
        "ai_recommendation": ai_recommendation,
    }
