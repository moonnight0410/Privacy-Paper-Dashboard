from __future__ import annotations

import datetime as dt
import http.client
import html
import json
import re
import ssl
import time
import urllib.parse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "sources.json"
REFERENCE_SOURCES_PATH = PROJECT_ROOT / "参考论文来源列表.md"


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
    "enabled_fetch_sources": [
        "arxiv",
        "ieee_sp",
        "acm_ccs",
        "usenix_security",
        "ndss",
        "crypto",
        "asiacrypt",
        "popets",
        "ieee_tifs",
        "acm_tops",
        "journal_cryptology",
        "ieee_tdsc",
    ],
    "fetch_rows": 12,
    "fetch_days": 1095,
    "fetch_min_score": 45,
    "fetch_max_age_days": 1095,
}


FETCH_SOURCE_CATALOG = [
    {
        "key": "arxiv",
        "name": "arXiv cs.CR",
        "category": "preprint",
        "tier": "Preprint",
        "source_ids": [],
    },
    {
        "key": "ieee_sp",
        "name": "IEEE Symposium on Security and Privacy",
        "category": "conference",
        "tier": "Tier 1",
        "source_ids": [
            "https://openalex.org/S4363606603",
            "https://openalex.org/S4306418833",
        ],
    },
    {
        "key": "acm_ccs",
        "name": "ACM Conference on Computer and Communications Security",
        "category": "conference",
        "tier": "Tier 1",
        "source_ids": [
            "https://openalex.org/S4363608815",
            "https://openalex.org/S4306417956",
        ],
    },
    {
        "key": "usenix_security",
        "name": "USENIX Security Symposium",
        "category": "conference",
        "tier": "Tier 1",
        "source_ids": [
            "https://openalex.org/S4306421123",
        ],
    },
    {
        "key": "ndss",
        "name": "Network and Distributed System Security Symposium",
        "category": "conference",
        "tier": "Tier 1",
        "source_ids": [
            "https://openalex.org/S4306420590",
        ],
    },
    {
        "key": "crypto",
        "name": "International Cryptology Conference",
        "category": "conference",
        "tier": "Tier 1",
        "source_ids": [
            "https://openalex.org/S4306419976",
        ],
    },
    {
        "key": "asiacrypt",
        "name": "International Conference on the Theory and Application of Cryptology and Information Security",
        "category": "conference",
        "tier": "Tier 1",
        "source_ids": [
            "https://openalex.org/S4306419886",
        ],
    },
    {
        "key": "popets",
        "name": "Proceedings on Privacy Enhancing Technologies",
        "category": "journal",
        "tier": "Tier 1",
        "source_ids": [
            "https://openalex.org/S4210183172",
        ],
    },
    {
        "key": "ieee_tifs",
        "name": "IEEE Transactions on Information Forensics and Security",
        "category": "journal",
        "tier": "Tier 1",
        "source_ids": [
            "https://openalex.org/S61310614",
        ],
    },
    {
        "key": "acm_tops",
        "name": "ACM Transactions on Privacy and Security",
        "category": "journal",
        "tier": "Tier 1",
        "source_ids": [
            "https://openalex.org/S4210174050",
        ],
    },
    {
        "key": "journal_cryptology",
        "name": "Journal of Cryptology",
        "category": "journal",
        "tier": "Tier 1",
        "source_ids": [
            "https://openalex.org/S190936789",
        ],
    },
    {
        "key": "ieee_tkde",
        "name": "IEEE Transactions on Knowledge and Data Engineering",
        "category": "journal",
        "tier": "Tier 1",
        "source_ids": [
            "https://openalex.org/S30698027",
        ],
    },
    {
        "key": "acm_tods",
        "name": "ACM Transactions on Database Systems",
        "category": "journal",
        "tier": "Tier 1",
        "source_ids": [
            "https://openalex.org/S90119964",
        ],
    },
    {
        "key": "ieee_tdsc",
        "name": "IEEE Transactions on Dependable and Secure Computing",
        "category": "journal",
        "tier": "Tier 1",
        "source_ids": [
            "https://openalex.org/S133795288",
        ],
    },
]


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


def fetch_text(url: str, timeout: int = 25, retries: int = 3) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 privacy-paper-dashboard/1.0",
            "Accept": "application/rss+xml, application/atom+xml, application/json, text/html, */*",
        },
    )
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                charset = resp.headers.get_content_charset() or "utf-8"
                return raw.decode(charset, errors="replace")
        except (http.client.IncompleteRead, ssl.SSLError, urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(1.2 * (attempt + 1))
                continue
            raise
    if last_error:
        raise last_error
    return ""


def strip_tags(value: str) -> str:
    value = re.sub(r"<script[\s\S]*?</script>", " ", value, flags=re.I)
    value = re.sub(r"<style[\s\S]*?</style>", " ", value, flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    return html.unescape(re.sub(r"\s+", " ", value)).strip()


class PageMetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, list[str]] = {}
        self.title_parts: list[str] = []
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "title":
            self._in_title = True
            return
        if tag.lower() != "meta":
            return
        attr_map = {key.lower(): (value or "").strip() for key, value in attrs}
        name = (attr_map.get("name") or attr_map.get("property") or "").lower()
        content = attr_map.get("content", "")
        if name and content:
            self.meta.setdefault(name, []).append(strip_tags(content))

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data)

    @property
    def title(self) -> str:
        return strip_tags(" ".join(self.title_parts))


def first_meta(meta: dict[str, list[str]], *names: str) -> str:
    for name in names:
        values = meta.get(name.lower()) or []
        for value in values:
            if value.strip():
                return value.strip()
    return ""


def first_json_string(text: str, *names: str) -> str:
    for name in names:
        match = re.search(rf'"{re.escape(name)}"\s*:\s*"((?:\\.|[^"])*)"', text)
        if not match:
            continue
        raw = match.group(1)
        try:
            return strip_tags(json.loads(f'"{raw}"'))
        except json.JSONDecodeError:
            return strip_tags(raw.replace('\\"', '"'))
    return ""


ACADEMIC_HOSTS = {
    "arxiv.org": "arXiv",
    "openreview.net": "OpenReview",
    "ieeexplore.ieee.org": "IEEE Xplore",
    "dl.acm.org": "ACM Digital Library",
    "doi.org": "DOI",
    "link.springer.com": "Springer",
    "www.nature.com": "Nature",
    "www.sciencedirect.com": "ScienceDirect",
    "www.usenix.org": "USENIX",
    "www.ndss-symposium.org": "NDSS",
    "eprint.iacr.org": "IACR ePrint",
}

ACADEMIC_HOST_SUFFIXES = (
    "arxiv.org",
    "openreview.net",
    "ieee.org",
    "acm.org",
    "springer.com",
    "nature.com",
    "sciencedirect.com",
    "usenix.org",
    "ndss-symposium.org",
    "iacr.org",
    "semanticscholar.org",
)

DOMESTIC_AUTHORITY_SUFFIXES = (
    "gov.cn",
    "caict.ac.cn",
    "tc260.org.cn",
    "ccf.org.cn",
)


def normalize_import_source_label(source: str, host: str) -> str:
    source = re.sub(r"\s+", " ", source).strip(" |-")
    lowered = source.casefold()
    if lowered in {"arxiv.org", "arxiv"}:
        return "arXiv"
    if lowered in {"ieee xplore"} and host.endswith("ieeexplore.ieee.org"):
        return "IEEE Xplore"
    return source


def infer_import_source(host: str, meta: dict[str, list[str]], raw_text: str = "") -> tuple[str, str]:
    host = host.lower()
    source = first_meta(
        meta,
        "citation_conference_title",
        "citation_journal_title",
        "citation_book_title",
        "citation_technical_report_institution",
        "prism.publicationname",
        "dc.source",
        "citation_publisher",
        "og:site_name",
        "application-name",
    )
    if not source and raw_text:
        source = first_json_string(
            raw_text,
            "displayPublicationTitle",
            "publicationTitle",
            "journalTitle",
            "bookTitle",
        )
    source = normalize_import_source_label(source, host)
    if host.endswith("mp.weixin.qq.com"):
        return source or "微信公众号", "wechat_authority"
    if source:
        return source, "international_academic"
    for domain, label in ACADEMIC_HOSTS.items():
        if host == domain or host.endswith(f".{domain}"):
            return label, "international_academic"
    if any(host == suffix or host.endswith(f".{suffix}") for suffix in DOMESTIC_AUTHORITY_SUFFIXES):
        return host, "domestic_authority"
    if any(host == suffix or host.endswith(f".{suffix}") for suffix in ACADEMIC_HOST_SUFFIXES):
        return host, "international_academic"
    return host, "search"


def extract_doi_from_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(html.unescape(url.strip()))
    host = parsed.netloc.lower()
    path = parsed.path.strip()
    doi = ""
    if host == "doi.org":
        doi = path.lstrip("/")
    elif host.endswith("dl.acm.org"):
        match = re.search(r"^/doi/(?:abs/|full/|pdf/)?(10\.\d{4,9}/.+)$", path, flags=re.I)
        if match:
            doi = match.group(1)
    else:
        match = re.search(r"/(10\.\d{4,9}/[^?#]+)", path, flags=re.I)
        if match:
            doi = match.group(1)
    doi = doi.strip().strip("/")
    if doi.lower().endswith(".pdf"):
        doi = doi[:-4]
    return urllib.parse.unquote(doi)


def candidate_from_doi_metadata(url: str) -> Candidate | None:
    doi = extract_doi_from_url(url)
    if not doi:
        return None
    api_url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="")
    data = json.loads(fetch_text(api_url))
    item = data.get("message") or {}
    candidate = crossref_item_to_candidate(item)
    if not candidate:
        return None
    candidate.url = canonical_url(url)
    return candidate


def candidate_from_url(url: str, config: dict) -> Candidate:
    parsed = urllib.parse.urlsplit(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL must start with http:// or https://")

    try:
        candidate = candidate_from_doi_metadata(url)
    except Exception:
        candidate = None
    if candidate is None:
        text = fetch_text(url)
        parser = PageMetadataParser()
        parser.feed(text[:1_500_000])

        title = first_meta(
            parser.meta,
            "citation_title",
            "dc.title",
            "dcterms.title",
            "og:title",
            "twitter:title",
        ) or parser.title
        title = re.sub(r"\s+", " ", title).strip()
        if not title:
            raise ValueError("Unable to extract a paper title from this URL")

        summary = first_meta(
            parser.meta,
            "citation_abstract",
            "dc.description",
            "dcterms.description",
            "description",
            "og:description",
            "twitter:description",
        )
        published = parse_date(
            first_meta(
                parser.meta,
                "citation_publication_date",
                "citation_online_date",
                "citation_date",
                "article:published_time",
                "dc.date",
                "dcterms.issued",
            )
        )
        authors = "; ".join(parser.meta.get("citation_author", [])[:8]) or first_meta(
            parser.meta,
            "dc.creator",
            "author",
            "article:author",
        )
        source, source_type = infer_import_source(parsed.netloc.lower(), parser.meta, text)

        candidate = Candidate(
            title=title,
            url=canonical_url(url),
            source=source,
            source_type=source_type,
            published=published,
            summary=summary,
            authors=authors,
        )
    score_candidate(candidate, config)
    candidate.reasons.append("Manual URL import")
    return candidate


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
    if host.endswith("arxiv.org"):
        path = re.sub(r"^/pdf/(.+?)\.pdf$", r"/abs/\1", path)
        path = re.sub(r"^/html/(.+)$", r"/abs/\1", path)
        path = re.sub(r"(v\d+)$", "", path)
    elif host.endswith("ieeexplore.ieee.org"):
        path = path.replace("/abstract/document/", "/document/")
    elif host.endswith("dl.acm.org"):
        path = path.replace("/doi/abs/", "/doi/")
        path = path.replace("/doi/full/", "/doi/")
        path = re.sub(r"^/doi/pdf/(.+?)(?:\.pdf)?$", r"/doi/\1", path)
    elif host == "doi.org":
        path = path.lower()
    query_pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=False)
    if host.endswith("mp.weixin.qq.com"):
        keep = {"__biz", "mid", "idx", "sn"}
        query_pairs = [(k, v) for k, v in query_pairs if k in keep]
    elif host.endswith("openreview.net"):
        keep = {"id", "noteId"}
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
    config["fetch_source_catalog"] = json.loads(json.dumps(FETCH_SOURCE_CATALOG, ensure_ascii=False))
    reference_sources = load_reference_sources()
    config["reference_sources"] = reference_sources
    config["authority_venues"] = merge_unique(
        config.get("authority_venues", []),
        [item["full_name"] for item in reference_sources],
        [item["alias"] for item in reference_sources],
    )
    enabled_fetch_sources = config.get("enabled_fetch_sources")
    if not isinstance(enabled_fetch_sources, list):
        config["enabled_fetch_sources"] = [item["key"] for item in FETCH_SOURCE_CATALOG]
    config["fetch_days"] = max(1, min(int(config.get("fetch_days", 1095) or 1095), 1095))
    config["fetch_max_age_days"] = max(0, min(int(config.get("fetch_max_age_days", 1095) or 1095), 1095))
    return config


def save_config(config: dict, path: Path = DEFAULT_CONFIG_PATH) -> None:
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def merge_unique(*groups: Iterable[str]) -> list[str]:
    seen = set()
    results = []
    for group in groups:
        for value in group:
            value = (value or "").strip()
            if not value:
                continue
            key = value.casefold()
            if key not in seen:
                seen.add(key)
                results.append(value)
    return results


def clean_table_cell(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value)
    value = value.replace("&amp;", "&")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def load_reference_sources(path: Path = REFERENCE_SOURCES_PATH) -> list[dict]:
    if not path.exists():
        return []
    sources = []
    for raw_line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = raw_line.strip()
        if not line.startswith("|") or "---" in line:
            continue
        cells = [clean_table_cell(cell) for cell in line.strip("|").split("|")]
        header = cells[0] if cells else ""
        try:
            header_fixed = header.encode("latin1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            header_fixed = header
        if len(cells) < 4 or header in {"一级分类"} or header_fixed == "一级分类":
            continue
        category, tier, full_name, alias = cells[:4]
        if not full_name or full_name == "全称":
            continue
        sources.append(
            {
                "category": category,
                "tier": tier,
                "full_name": full_name,
                "alias": alias,
            }
        )
    return sources


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


def crossref_item_to_candidate(item: dict) -> Candidate | None:
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
        return Candidate(title, link, container or "Crossref", "international_academic", published, container, authors)
    return None


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
            candidate = crossref_item_to_candidate(item)
            if candidate:
                results.append(candidate)
        time.sleep(0.8)
    return results


def fetch_reference_source_crossref(config: dict, days: int) -> list[Candidate]:
    start = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    sources = config.get("reference_sources", [])
    enabled_sources = config.get("enabled_reference_sources")
    if isinstance(enabled_sources, list):
        enabled_names = {str(item).strip().casefold() for item in enabled_sources if str(item).strip()}
        if enabled_names:
            sources = [source for source in sources if (source.get("full_name") or "").casefold() in enabled_names]
        else:
            sources = []
    sources = sources[: int(config.get("reference_source_query_limit", 20))]
    rows = int(config.get("reference_source_query_rows", 5))
    results = []
    for source in sources:
        full_name = source.get("full_name", "")
        if not full_name:
            continue
        url = "https://api.crossref.org/works?" + urllib.parse.urlencode(
            {
                "query.container-title": full_name,
                "query.bibliographic": "privacy security data",
                "filter": f"from-pub-date:{start}",
                "sort": "published",
                "order": "desc",
                "rows": str(rows),
            }
        )
        data = json.loads(fetch_text(url))
        for item in data.get("message", {}).get("items", []):
            candidate = crossref_item_to_candidate(item)
            if candidate:
                candidate.source = candidate.source or full_name
                candidate.reasons.append(f"参考来源：{source.get('alias') or full_name}")
                results.append(candidate)
        time.sleep(0.8)
    return results


def rebuild_abstract(inverted_index: dict | None) -> str:
    if not inverted_index:
        return ""
    slots: dict[int, str] = {}
    for token, positions in inverted_index.items():
        for position in positions or []:
            if isinstance(position, int) and position not in slots:
                slots[position] = token
    if not slots:
        return ""
    return " ".join(slots[index] for index in sorted(slots))


def authors_from_authorships(authorships: list[dict] | None) -> str:
    if not authorships:
        return ""
    names = []
    for authorship in authorships[:8]:
        author = authorship.get("author") or {}
        name = (author.get("display_name") or "").strip()
        if name:
            names.append(name)
    return ", ".join(names)


def enabled_fetch_source_keys(config: dict) -> set[str]:
    selected = config.get("enabled_fetch_sources")
    if not isinstance(selected, list):
        return {spec["key"] for spec in FETCH_SOURCE_CATALOG}
    return {str(item).strip() for item in selected if str(item).strip()}


def enabled_fetch_sources(config: dict) -> list[dict]:
    selected_keys = enabled_fetch_source_keys(config)
    return [spec for spec in FETCH_SOURCE_CATALOG if spec["key"] in selected_keys]


def openalex_work_to_candidate(work: dict, source_name: str) -> Candidate | None:
    title = strip_tags(work.get("title") or "")
    if not title:
        return None
    primary_location = work.get("primary_location") or {}
    source = (primary_location.get("source") or {}).get("display_name") or source_name
    url = (
        primary_location.get("landing_page_url")
        or primary_location.get("pdf_url")
        or work.get("doi")
        or (work.get("ids") or {}).get("openalex")
        or ""
    )
    if not url:
        return None
    published = parse_date(work.get("publication_date") or "")
    summary = rebuild_abstract(work.get("abstract_inverted_index"))
    authors = authors_from_authorships(work.get("authorships"))
    candidate = Candidate(
        title=title,
        url=url,
        source=source_name,
        source_type="international_academic",
        published=published,
        summary=summary,
        authors=authors,
    )
    candidate.reasons.append(f"顶会第一梯队：{source_name}")
    return candidate


def fetch_openalex_sources(source_specs: list[dict], rows: int, days: int) -> tuple[list[Candidate], dict[str, int]]:
    start = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    candidates: list[Candidate] = []
    source_counts: dict[str, int] = {}
    for spec in source_specs:
        venue_total = 0
        for source_id in spec["source_ids"]:
            url = "https://api.openalex.org/works?" + urllib.parse.urlencode(
                {
                    "filter": f"primary_location.source.id:{source_id},from_publication_date:{start}",
                    "sort": "publication_date:desc",
                    "per-page": str(rows),
                }
            )
            data = json.loads(fetch_text(url))
            for work in data.get("results", []):
                candidate = openalex_work_to_candidate(work, spec["name"])
                if candidate:
                    candidates.append(candidate)
                    venue_total += 1
            time.sleep(0.6)
        source_counts[spec["name"]] = venue_total
    return candidates, source_counts


def fetch_top_tier_openalex(rows: int, days: int) -> tuple[list[Candidate], dict[str, int]]:
    top_tier_keys = {"ieee_sp", "acm_ccs", "usenix_security", "ndss"}
    source_specs = [spec for spec in FETCH_SOURCE_CATALOG if spec["key"] in top_tier_keys]
    return fetch_openalex_sources(source_specs, rows, days)


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
        ("Reference Sources", lambda: fetch_reference_source_crossref(config, days)),
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


def collect_candidates(config: dict, rows: int, days: int) -> tuple[list[Candidate], dict, list[str]]:
    selected_keys = enabled_fetch_source_keys(config)
    if not selected_keys:
        return [], {}, []

    candidates: list[Candidate] = []
    source_counts: dict[str, int] = {}
    failures: list[str] = []

    if "arxiv" in selected_keys:
        try:
            items = fetch_arxiv(rows)
            candidates.extend(items)
            source_counts["arXiv"] = len(items)
        except Exception as exc:
            source_counts["arXiv"] = 0
            failures.append(f"arXiv 抓取失败：{exc}")

    source_specs = [spec for spec in enabled_fetch_sources(config) if spec["key"] != "arxiv"]
    if source_specs:
        try:
            openalex_candidates, openalex_counts = fetch_openalex_sources(source_specs, rows, days)
            candidates.extend(openalex_candidates)
            source_counts.update(openalex_counts)
        except Exception as exc:
            failures.append(f"OpenAlex 抓取失败：{exc}")

    return candidates, source_counts, failures
