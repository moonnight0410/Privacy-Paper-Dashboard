from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request

from .translation_client import translate_text


SYSTEM_PROMPT = """
你是严谨的论文解读助手。
你的输出必须以论文原文信息为基础，优先依据标题、摘要、来源、时间和给定线索进行判断。
禁止编造论文中没有出现的方法、实验、数据、结论、应用场景或政策含义。
如果信息不足，必须明确写出“基于摘要可判断”或“摘要未说明”，不要补全想象内容。
输出必须是合法 JSON，不要输出 Markdown，不要输出代码块，不要附加解释。
""".strip()


def chat_completions_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"


def candidate_chat_urls(base_url: str) -> list[str]:
    base = (base_url or "").strip().rstrip("/")
    if not base:
        return [""]
    urls = [chat_completions_url(base)]
    parsed = urllib.parse.urlsplit(base)
    path = parsed.path.rstrip("/")
    if not path.endswith("/v1") and not path.endswith("/chat/completions"):
        v1_base = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, f"{path}/v1", parsed.query, parsed.fragment))
        urls.append(chat_completions_url(v1_base))
    seen = set()
    results = []
    for url in urls:
        if url and url not in seen:
            seen.add(url)
            results.append(url)
    return results


def compact_summary(summary: str, max_chars: int) -> str:
    summary = (summary or "").strip()
    if len(summary) <= max_chars:
        return summary
    head = summary[: max_chars // 2]
    tail = summary[-max_chars // 2 :]
    return f"{head}\n\n[摘要过长，中间内容已省略，请仅基于保留内容进行判断]\n\n{tail}"


def format_reasons(reasons: list[object]) -> str:
    cleaned = [str(item).strip() for item in reasons if str(item).strip()]
    return "；".join(cleaned) if cleaned else "无"


def build_prompt(article: dict, max_input_chars: int) -> str:
    reasons = article.get("reasons") or []
    summary = compact_summary(article.get("summary") or "", max_input_chars)
    return f"""
请基于给定论文信息完成中文翻译和论文解读，输出严格符合以下 JSON 结构：
{{
  "translated_title": "中文学术直译标题",
  "translated_summary": "中文学术直译摘要",
  "ai_recommendation": [
    "核心观点：...",
    "关键内容摘录：...",
    "价值与边界：..."
  ]
}}

写作要求：
1. translated_title 与 translated_summary 必须忠实直译，保持学术表达，不得扩写。
2. ai_recommendation 必须是 3 条，每条 40-120 个中文字符，分别对应“核心观点”“关键内容摘录”“价值与边界”。
3. “核心观点”要先说论文主要主张或主要解决的问题。
4. “关键内容摘录”要概括论文摘要中明确出现的方法、机制、对象、结果或结论，只能摘录原文已有信息。
5. “价值与边界”要说明其对隐私保护、数据安全、可信 AI、合规治理或论文选题的参考价值；若摘要未说明实验效果、部署条件或适用范围，必须明确指出边界。
6. 不要使用“可能”“大概”这类空泛表述；信息不足时，直接写“基于摘要可判断……”或“摘要未说明……”。
7. 如果 title 为空，translated_title 返回空字符串；如果摘要为空，translated_summary 返回空字符串，且 3 条解读都要明确说明信息不足。

论文信息：
title: {article.get("title") or ""}
source: {article.get("source") or ""}
source_type: {article.get("source_type") or ""}
published: {article.get("published") or ""}
score: {article.get("score") or ""}
reasons: {format_reasons(reasons)}
original English summary:
{summary}
""".strip()


def build_recommendation_prompt(article: dict, max_input_chars: int, translated_summary: str) -> str:
    reasons = article.get("reasons") or []
    summary = compact_summary(article.get("summary") or "", max_input_chars)
    translated_summary = compact_summary(translated_summary, max_input_chars)
    return f"""
请基于给定论文信息生成中文论文解读，输出严格符合以下 JSON 结构：
{{
  "ai_recommendation": [
    "核心观点：...",
    "关键内容摘录：...",
    "价值与边界：..."
  ]
}}

写作要求：
1. 必须输出 3 条，分别对应“核心观点”“关键内容摘录”“价值与边界”。
2. 每条 40-120 个中文字符，要求可读、专业、可直接用于论文筛选记录。
3. “核心观点”概括论文的核心问题、方法或主张。
4. “关键内容摘录”只允许概括标题、中文摘要、英文摘要里明确写出的事实，不得补写实验指标、数据规模、制度效果等未出现内容。
5. “价值与边界”说明其与隐私、安全、可信 AI、数据治理或研究选题的关系；如果适用场景、性能收益或落地条件在摘要中没有说明，必须直接点明边界。
6. 全文以原论文真实性为准，不夸大，不拔高，不写宣传话术。

论文信息：
title: {article.get("title") or ""}
source: {article.get("source") or ""}
source_type: {article.get("source_type") or ""}
published: {article.get("published") or ""}
score: {article.get("score") or ""}
reasons: {format_reasons(reasons)}
Chinese summary:
{translated_summary}
original English summary:
{summary}
""".strip()


def normalize_recommendations(recommendation: list[str]) -> list[str]:
    labels = ["核心观点", "关键内容摘录", "价值与边界"]
    results: list[str] = []
    for index, label in enumerate(labels):
        item = recommendation[index].strip() if index < len(recommendation) else ""
        if not item:
            item = f"{label}：摘要未提供足够信息，暂无法给出更具体判断。"
        elif not item.startswith(f"{label}："):
            item = f"{label}：{item}"
        results.append(item)
    return results


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
        recommendation = [line.strip("- 0123456789.、)）") for line in recommendation.splitlines() if line.strip()]
    cleaned_recommendation = [str(item).strip() for item in recommendation if str(item).strip()]
    return {
        "translated_title": str(data.get("translated_title") or "").strip(),
        "translated_summary": str(data.get("translated_summary") or "").strip(),
        "ai_recommendation": normalize_recommendations(cleaned_recommendation[:3]),
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
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    urls = candidate_chat_urls(base_url)
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        for url in urls:
            try:
                req = urllib.request.Request(url, data=body, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=90) as resp:
                    raw = resp.read().decode("utf-8", errors="replace")
                data = json.loads(raw)
                content = data["choices"][0]["message"]["content"]
                return parse_json_content(content)
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace").strip()
                message = f"HTTP {exc.code} from {url}"
                if detail:
                    message += f": {detail[:400]}"
                last_error = RuntimeError(message)
                if exc.code == 404 and url != urls[-1]:
                    continue
                if attempt < retries:
                    time.sleep(1.5 * (attempt + 1))
                    break
                raise last_error
            except (KeyError, json.JSONDecodeError, urllib.error.URLError, TimeoutError, ValueError) as exc:
                last_error = exc
                if attempt < retries:
                    time.sleep(1.5 * (attempt + 1))
                    break
                raise
        else:
            continue
    if last_error:
        raise last_error
    raise RuntimeError("AI enrichment failed")


def enrich_article(
    article: dict,
    ai_config: dict | None,
    translation_config: dict | None = None,
    retries: int = 2,
    do_translation: bool = True,
    do_recommendation: bool = True,
) -> dict:
    max_input_chars = int((ai_config or {}).get("max_input_chars") or 6000)
    translated_title = (article.get("translated_title") or "").strip()
    translated_summary = (article.get("translated_summary") or "").strip()
    ai_recommendation: list[str] = list(article.get("ai_recommendation") or [])

    if do_translation and translation_config and translation_config.get("enabled"):
        translated_title = translate_text(article.get("title") or "", translation_config, retries=retries)
        translated_summary = translate_text(article.get("summary") or "", translation_config, retries=retries)

    if do_recommendation:
        if not has_ai_config(ai_config):
            raise ValueError("AI config is required for recommendation generation")
        prompt = (
            build_recommendation_prompt(article, max_input_chars, translated_summary)
            if translated_summary
            else build_prompt(article, max_input_chars)
        )
        ai_result = call_chat_json(prompt, ai_config or {}, retries=retries)
        if do_translation and not translated_title:
            translated_title = ai_result["translated_title"]
        if do_translation and not translated_summary:
            translated_summary = ai_result["translated_summary"]
        ai_recommendation = ai_result["ai_recommendation"]
    elif do_translation and not translated_title and not translated_summary:
        raise ValueError("Machine translation config is required")

    return {
        "translated_title": translated_title,
        "translated_summary": translated_summary,
        "ai_recommendation": ai_recommendation,
    }
