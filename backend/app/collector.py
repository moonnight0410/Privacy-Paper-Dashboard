from __future__ import annotations

import datetime as dt
import html
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "sources.json"


DEFAULT_CONFIG = {
    "keywords": [
        "data security",
        "privacy protection",
        "privacy preserving",
        "private data",
        "differential privacy",
        "federated learning",
        "secure multiparty computation",
        "multi-party computation",
        "homomorphic encryption",
        "zero-knowledge",
        "zero knowledge",
        "trusted execution",
        "confidential computing",
        "data governance",
        "personal information protection",
        "数据安全",
        "隐私保护",
        "隐私计算",
        "个人信息保护",
        "数据治理",
        "联邦学习",
        "差分隐私",
        "安全多方计算",
        "同态加密",
        "零知识证明",
        "可信执行环境",
        "数据要素",
        "大模型安全",
    ],
    "hot_terms": [
        "LLM",
        "large language model",
        "AI",
        "agent",
        "RAG",
        "synthetic data",
        "attack",
        "leakage",
        "compliance",
        "cross-border",
        "大模型",
        "人工智能",
        "生成式",
        "数据出境",
        "合规",
        "泄露",
        "攻击",
        "测评",
        "治理",
    ],
    "exclude_terms": [
        "招聘",
        "招生",
        "培训",
        "课程",
        "会议通知",
        "征稿",
        "广告",
        "优惠",
        "sale",
        "course",
        "job",
        "call for papers",
    ],
    "authority_venues": [
        "IEEE Symposium on Security and Privacy",
        "IEEE S&P",
        "ACM CCS",
        "USENIX Security",
        "NDSS",
        "CRYPTO",
        "EUROCRYPT",
        "ASIACRYPT",
        "SIGMOD",
        "VLDB",
        "PVLDB",
        "PoPETs",
        "NeurIPS",
        "ICML",
        "ICLR",
        "IEEE TIFS",
        "ACM TOPS",
        "Journal of Cryptology",
        "IEEE TKDE",
        "ACM TODS",
        "IEEE TDSC",
    ],
    "bing_queries": [
        {
            "name": "CAICT",
            "type": "domestic_authority",
            "query": "site:caict.ac.cn (数据安全 OR 隐私保护 OR 个人信息保护 OR 隐私计算) (研究 OR 报告 OR 白皮书 OR 前沿)",
        },
        {
            "name": "TC260",
            "type": "domestic_authority",
            "query": "site:tc260.org.cn (数据安全 OR 隐私保护 OR 个人信息保护 OR 数据治理)",
        },
        {
            "name": "CCF",
            "type": "domestic_authority",
            "query": "site:ccf.org.cn (数据安全 OR 隐私保护 OR 隐私计算 OR 联邦学习 OR 差分隐私)",
        },
        {
            "name": "WeChat authority",
            "type": "wechat_authority",
            "query": "site:mp.weixin.qq.com (数据安全 OR 隐私保护 OR 个人信息保护 OR 隐私计算) (中国信通院 OR CCF OR 中国网络空间安全协会 OR 数据安全推进计划)",
        },
        {
            "name": "IEEE Xplore",
            "type": "international_academic",
            "query": 'site:ieeexplore.ieee.org ("privacy preserving" OR "data security" OR "differential privacy" OR "federated learning")',
        },
        {
            "name": "ACM Digital Library",
            "type": "international_academic",
            "query": 'site:dl.acm.org ("privacy preserving" OR "data security" OR "differential privacy" OR "federated learning")',
        },
        {
            "name": "USENIX",
            "type": "international_academic",
            "query": 'site:usenix.org ("privacy preserving" OR "data security" OR "differential privacy" OR "federated learning")',
        },
    ],
}


@dataclass
class Candidate:
    title: str
    url: str
    source: str
    source_type: str
    published: str = ""
    summary: str = ""
    authors: str = ""
    score: int = 0
    reasons: list[str] = field(default_factory=list)


def fetch_text(url: str, timeout: int = 25) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 privacy-paper-dashboard/1.0",
            "Accept": "application/rss+xml, application/atom+xml, application/json, text/html, */*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        charset = resp.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="replace")


def strip_tags(value: str) -> str:
    value = re.sub(r"<script[\s\S]*?</script>", " ", value, flags=re.I)
    value = re.sub(r"<style[\s\S]*?</style>", " ", value, flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    return html.unescape(re.sub(r"\s+", " ", value)).strip()


def normalize_title(value: str) -> str:
    value = html.unescape(strip_tags(value)).lower()
    value = re.sub(r"https?://\S+", " ", value)
    value = re.sub(r"[\W_]+", " ", value, flags=re.U)
    return re.sub(r"\s+", " ", value).strip()


def has_cjk(value: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", value))


def term_in_text(term: str, text: str) -> bool:
    if has_cjk(term):
        return term.lower() in text.lower()
    escaped = re.escape(term)
    return bool(re.search(rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])", text, flags=re.I))


def matching_terms(terms: Iterable[str], text: str) -> list[str]:
    return [term for term in terms if term_in_text(term, text)]


def canonical_url(value: str) -> str:
    if not value:
        return ""
    parsed = urllib.parse.urlsplit(html.unescape(value.strip()))
    host = parsed.netloc.lower()
    path = re.sub(r"/+$", "", parsed.path)
    query_pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=False)
    if host.endswith("mp.weixin.qq.com"):
        keep = {"__biz", "mid", "idx", "sn"}
        query_pairs = [(k, v) for k, v in query_pairs if k in keep]
    else:
        query_pairs = [
            (k, v)
            for k, v in query_pairs
            if not k.lower().startswith("utm_")
            and k.lower() not in {"spm", "from", "source", "share_token"}
        ]
    query = urllib.parse.urlencode(sorted(query_pairs))
    return urllib.parse.urlunsplit((parsed.scheme.lower() or "https", host, path, query, ""))


def site_domains_from_query(query: str) -> list[str]:
    domains = re.findall(r"site:([A-Za-z0-9.-]+\.[A-Za-z]{2,})", query, flags=re.I)
    return [domain.lower() for domain in domains]


def url_matches_domains(url: str, domains: Iterable[str]) -> bool:
    domains = list(domains)
    if not domains:
        return True
    host = urllib.parse.urlsplit(html.unescape(url.strip())).netloc.lower()
    return any(host == domain or host.endswith(f".{domain}") for domain in domains)


def parse_date(value: str) -> str:
    if not value:
        return ""
    value = value.strip()
    known_formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d",
    ]
    for fmt in known_formats:
        try:
            return dt.datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    match = re.search(r"20\d{2}[-/.]\d{1,2}[-/.]\d{1,2}", value)
    if match:
        year, month, day = re.split(r"[-/.]", match.group(0))
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    return ""


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> dict:
    config = json.loads(json.dumps(DEFAULT_CONFIG, ensure_ascii=False))
    if path.exists():
        user_config = json.loads(path.read_text(encoding="utf-8"))
        for key, value in user_config.items():
            config[key] = value
    return config


def save_config(config: dict, path: Path = DEFAULT_CONFIG_PATH) -> None:
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def tag_local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    if ":" in tag:
        return tag.rsplit(":", 1)[1]
    return tag


def get_text(element: ET.Element, names: Iterable[str]) -> str:
    wanted = {tag_local_name(name) for name in names}
    for child in list(element):
        if tag_local_name(child.tag) in wanted and child.text:
            return strip_tags(child.text)
    return ""


def fetch_iacr() -> list[Candidate]:
    text = fetch_text("https://eprint.iacr.org/rss/rss.xml")
    root = ET.fromstring(text)
    results = []
    for item in root.findall(".//item"):
        title = get_text(item, ["title"])
        link = get_text(item, ["link"])
        desc = get_text(item, ["description"])
        pub = parse_date(get_text(item, ["pubDate"]))
        if title and link:
            results.append(Candidate(title, link, "IACR ePrint", "international_academic", pub, desc))
    return results


def fetch_arxiv(max_results: int) -> list[Candidate]:
    terms = [
        '"data security"',
        '"privacy preserving"',
        '"privacy protection"',
        '"differential privacy"',
        '"federated learning"',
        '"secure multiparty computation"',
        '"homomorphic encryption"',
        '"zero knowledge"',
        '"confidential computing"',
    ]
    query = "cat:cs.CR AND (" + " OR ".join(f"all:{term}" for term in terms) + ")"
    url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(
        {
            "search_query": query,
            "start": "0",
            "max_results": str(max_results),
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
    )
    root = ET.fromstring(fetch_text(url))
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    results = []
    for entry in root.findall("atom:entry", ns):
        title = get_text(entry, ["atom:title"])
        summary = get_text(entry, ["atom:summary"])
        link = ""
        for link_el in entry.findall("atom:link", ns):
            if link_el.attrib.get("rel") == "alternate":
                link = link_el.attrib.get("href", "")
                break
        authors = ", ".join(get_text(a, ["atom:name"]) for a in entry.findall("atom:author", ns))
        pub = parse_date(get_text(entry, ["atom:published"]))
        if title and link:
            results.append(Candidate(title, link, "arXiv cs.CR", "international_academic", pub, summary, authors))
    return results


def fetch_crossref(rows: int, days: int) -> list[Candidate]:
    start = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    queries = [
        "data security privacy protection",
        "privacy preserving data security",
        "differential privacy federated learning",
        "secure multiparty computation privacy",
    ]
    results = []
    for query in queries:
        url = "https://api.crossref.org/works?" + urllib.parse.urlencode(
            {
                "query.bibliographic": query,
                "filter": f"from-pub-date:{start}",
                "sort": "published",
                "order": "desc",
                "rows": str(rows),
            }
        )
        data = json.loads(fetch_text(url))
        for item in data.get("message", {}).get("items", []):
            title = " ".join(item.get("title") or []).strip()
            doi = item.get("DOI", "")
            link = item.get("URL") or (f"https://doi.org/{doi}" if doi else "")
            container = ", ".join(item.get("container-title") or [])
            date_parts = (
                item.get("published-print", {}).get("date-parts")
                or item.get("published-online", {}).get("date-parts")
                or item.get("published", {}).get("date-parts")
                or []
            )
            published = ""
            if date_parts and date_parts[0]:
                parts = date_parts[0] + [1, 1]
                published = f"{parts[0]:04d}-{parts[1]:02d}-{parts[2]:02d}"
            authors = "; ".join(
                " ".join(filter(None, [a.get("given", ""), a.get("family", "")]))
                for a in item.get("author", [])[:6]
            )
            if title and link:
                results.append(Candidate(title, link, container or "Crossref", "international_academic", published, container, authors))
        time.sleep(0.8)
    return results


def fetch_bing_rss(config: dict, rows: int) -> list[Candidate]:
    results = []
    for spec in config.get("bing_queries", []):
        query = spec["query"]
        required_domains = site_domains_from_query(query)
        url = "https://www.bing.com/search?" + urllib.parse.urlencode(
            {"q": query, "format": "rss", "count": rows, "mkt": "zh-CN", "setlang": "zh-cn"}
        )
        text = fetch_text(url)
        root = ET.fromstring(text)
        for item in root.findall(".//item"):
            title = get_text(item, ["title"])
            link = get_text(item, ["link"])
            desc = get_text(item, ["description"])
            pub = parse_date(get_text(item, ["pubDate"]))
            if title and link and url_matches_domains(link, required_domains):
                results.append(Candidate(title, link, spec.get("name", "Bing RSS"), spec.get("type", "search"), pub, desc))
        time.sleep(0.8)
    return results


def score_candidate(candidate: Candidate, config: dict) -> int:
    candidate.reasons.clear()
    text = f"{candidate.title} {candidate.summary} {candidate.source}"
    score = {
        "international_academic": 35,
        "domestic_authority": 28,
        "wechat_authority": 22,
        "search": 10,
    }.get(candidate.source_type, 12)
    candidate.reasons.append(f"来源类型：{candidate.source_type}")
    keyword_hits = matching_terms(config["keywords"], text)
    score += min(len(keyword_hits), 6) * 6
    if keyword_hits:
        candidate.reasons.append("关键词：" + "、".join(keyword_hits[:4]))
    hot_hits = matching_terms(config["hot_terms"], text)
    score += min(len(hot_hits), 4) * 4
    if hot_hits:
        candidate.reasons.append("热点：" + "、".join(hot_hits[:3]))
    authority_hits = matching_terms(config["authority_venues"], text)
    score += min(len(authority_hits), 2) * 18
    if authority_hits:
        candidate.reasons.append("权威来源：" + "、".join(authority_hits[:2]))
    if candidate.published:
        try:
            age = (dt.date.today() - dt.date.fromisoformat(candidate.published)).days
            if 0 <= age <= 3:
                score += 20
                candidate.reasons.append("3天内更新")
            elif 4 <= age <= 14:
                score += 12
                candidate.reasons.append("两周内更新")
            elif 15 <= age <= 45:
                score += 5
                candidate.reasons.append("近期更新")
        except ValueError:
            pass
    if any(term_in_text(term, candidate.title) for term in config["exclude_terms"]):
        score -= 100
    candidate.score = score
    return score


def relevant(candidate: Candidate, config: dict, min_score: int, max_age_days: int) -> bool:
    text = f"{candidate.title} {candidate.summary}"
    if any(term_in_text(term, text) for term in config["exclude_terms"]):
        return False
    if not any(term_in_text(kw, text) for kw in config["keywords"]):
        return False
    if candidate.published and max_age_days > 0:
        try:
            published_date = dt.date.fromisoformat(candidate.published)
            if published_date > dt.date.today() + dt.timedelta(days=7):
                return False
            if (dt.date.today() - published_date).days > max_age_days:
                return False
        except ValueError:
            pass
    return candidate.score >= min_score


def is_near_duplicate(title_norm: str, seen_titles: Iterable[str]) -> bool:
    for old in seen_titles:
        if not old:
            continue
        if title_norm == old or title_norm in old or old in title_norm:
            return True
        if SequenceMatcher(None, title_norm, old).ratio() >= 0.88:
            return True
    return False


def absorb_seen_text(text: str) -> tuple[set[str], set[str]]:
    seen_titles: set[str] = set()
    seen_urls: set[str] = set()
    for match in re.findall(r"https?://[^\s\])>\"']+", text):
        seen_urls.add(canonical_url(match))
    for line in text.splitlines():
        line = strip_tags(line).strip(" |,;\t")
        if not line or len(line) < 6 or line.startswith(("http://", "https://")):
            continue
        parts = [p.strip() for p in re.split(r"[\t,|，]", line) if p.strip()]
        for part in parts:
            norm = normalize_title(part)
            if len(norm) >= 8:
                seen_titles.add(norm)
    return seen_titles, seen_urls


def collect_candidates(config: dict, rows: int, days: int) -> tuple[list[Candidate], dict, list[str]]:
    candidates: list[Candidate] = []
    source_counts: dict[str, int] = {}
    failures: list[str] = []
    collectors = [
        ("arXiv", lambda: fetch_arxiv(rows)),
        ("IACR ePrint", fetch_iacr),
        ("Crossref", lambda: fetch_crossref(rows, days)),
        ("Bing RSS", lambda: fetch_bing_rss(config, rows)),
    ]
    for name, func in collectors:
        try:
            items = func()
            candidates.extend(items)
            source_counts[name] = len(items)
        except Exception as exc:
            source_counts[name] = 0
            failures.append(f"{name} 抓取失败：{exc}")
    return candidates, source_counts, failures

