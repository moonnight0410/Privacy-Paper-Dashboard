import React from 'react';
import { createRoot } from 'react-dom/client';
import {
  ArrowLeft,
  Archive,
  BookOpenCheck,
  CheckCircle2,
  Clock3,
  Download,
  ExternalLink,
  FileUp,
  History,
  Languages,
  ListFilter,
  Loader2,
  Link2,
  Play,
  RotateCcw,
  Search,
  Settings2,
  ShieldCheck,
  Sparkles,
  XCircle,
} from 'lucide-react';
import './styles.css';

const DEFAULT_API_HOST = (() => {
  if (typeof window === 'undefined') return '127.0.0.1';
  if (window.location.protocol === 'file:') return '127.0.0.1';
  const host = window.location.hostname;
  if (!host || host === 'localhost' || host === '127.0.0.1' || host === '::1' || host === '[::1]') {
    return '127.0.0.1';
  }
  return host;
})();

const API_BASE = import.meta.env.VITE_API_BASE ?? `http://${DEFAULT_API_HOST}:8000`;

const STATUS_META = {
  candidate: { label: '\u5019\u9009', icon: ListFilter },
  reading: { label: '\u5f85\u8bfb', icon: Clock3 },
  selected: { label: '\u5165\u9009', icon: CheckCircle2 },
  shared: { label: '\u5df2\u5206\u4eab', icon: BookOpenCheck },
  rejected: { label: '\u9a73\u56de', icon: XCircle },
};

const PAGE_META = {
  latest: { label: '\u672c\u6b21\u6293\u53d6', icon: Play },
  reading: { label: '\u5f85\u8bfb\u8bba\u6587', icon: Clock3 },
  today: { label: '\u5019\u9009\u6c60', icon: ListFilter },
  selected: { label: '\u5df2\u9009\u6587\u7ae0', icon: CheckCircle2 },
  history: { label: '\u5386\u53f2\u5e93', icon: Archive },
  config: { label: '\u6765\u6e90/\u5173\u952e\u8bcd\u914d\u7f6e', icon: Settings2 },
  logs: { label: '\u8fd0\u884c\u65e5\u5fd7', icon: History },
};

const SOURCE_TYPE_META = {
  international_academic: { label: '\u56fd\u9645\u5b66\u672f', tone: 'academic' },
  domestic_authority: { label: '\u56fd\u5185\u6743\u5a01', tone: 'authority' },
  wechat_authority: { label: '\u516c\u4f17\u53f7', tone: 'wechat' },
  search: { label: '\u641c\u7d22\u6765\u6e90', tone: 'search' },
};

const UI_STATUS_META = {
  candidate: { label: '\u5019\u9009', icon: ListFilter },
  reading: { label: '\u5f85\u8bfb', icon: Clock3 },
  selected: { label: '\u5165\u9009', icon: CheckCircle2 },
  shared: { label: '\u5df2\u5206\u4eab', icon: BookOpenCheck },
  rejected: { label: '\u9a73\u56de', icon: XCircle },
};

const UI_PAGE_META = {
  latest: { label: '\u672c\u6b21\u6293\u53d6', icon: Play },
  reading: { label: '\u5f85\u8bfb\u8bba\u6587', icon: Clock3 },
  today: { label: '\u5019\u9009\u6c60', icon: ListFilter },
  selected: { label: '\u5df2\u9009\u6587\u7ae0', icon: CheckCircle2 },
  history: { label: '\u5386\u53f2\u5e93', icon: Archive },
  config: { label: '\u6765\u6e90/\u5173\u952e\u8bcd\u914d\u7f6e', icon: Settings2 },
  logs: { label: '\u8fd0\u884c\u65e5\u5fd7', icon: History },
};

const UI_SOURCE_TYPE_META = {
  international_academic: { label: '\u56fd\u9645\u5b66\u672f', tone: 'academic' },
  domestic_authority: { label: '\u56fd\u5185\u6743\u5a01', tone: 'authority' },
  wechat_authority: { label: '\u516c\u4f17\u53f7', tone: 'wechat' },
  search: { label: '\u641c\u7d22\u6765\u6e90', tone: 'search' },
};

const AI_PROVIDERS = {
  other: { label: '\u5176\u4ed6 / OpenAI-compatible', baseUrl: '', model: '' },
  custom: { label: '\u81ea\u5b9a\u4e49 OpenAI-compatible', baseUrl: '', model: '' },
  deepseek: { label: 'DeepSeek', baseUrl: 'https://api.deepseek.com', model: 'deepseek-chat' },
  qwen: { label: '\u901a\u4e49\u5343\u95ee / DashScope', baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1', model: 'qwen-plus' },
  glm: { label: 'GLM / \u667a\u8c31', baseUrl: 'https://open.bigmodel.cn/api/paas/v4', model: 'glm-4-flash' },
  doubao: { label: '\u8c46\u5305 / \u706b\u5c71\u65b9\u821f', baseUrl: 'https://ark.cn-beijing.volces.com/api/v3', model: '' },
};

const DEFAULT_AI_CONFIG = {
  provider: 'deepseek',
  base_url: AI_PROVIDERS.deepseek.baseUrl,
  model: AI_PROVIDERS.deepseek.model,
  api_key: '',
  max_input_chars: 6000,
};

const TRANSLATION_PROVIDERS = {
  baidu: { label: '\u767e\u5ea6\u7ffb\u8bd1', baseUrl: 'https://fanyi-api.baidu.com/api/trans/vip/translate' },
  libretranslate: { label: 'LibreTranslate', baseUrl: 'https://libretranslate.com/translate' },
};

const DEFAULT_TRANSLATION_CONFIG = {
  enabled: false,
  provider: 'baidu',
  base_url: TRANSLATION_PROVIDERS.baidu.baseUrl,
  app_id: '',
  secret_key: '',
  api_key: '',
  source_lang: 'en',
  target_lang: 'zh',
};

function loadAIConfig() {
  try {
    return { ...DEFAULT_AI_CONFIG, ...(JSON.parse(localStorage.getItem('privacy-radar-ai-config') || '{}')) };
  } catch {
    return DEFAULT_AI_CONFIG;
  }
}

function saveAIConfig(config) {
  localStorage.setItem('privacy-radar-ai-config', JSON.stringify(config));
}

function loadTranslationConfig() {
  try {
    return { ...DEFAULT_TRANSLATION_CONFIG, ...(JSON.parse(localStorage.getItem('privacy-radar-translation-config') || '{}')) };
  } catch {
    return DEFAULT_TRANSLATION_CONFIG;
  }
}

function saveTranslationConfig(config) {
  localStorage.setItem('privacy-radar-translation-config', JSON.stringify(config));
}

function loadUIState(key, fallback) {
  try {
    const stored = localStorage.getItem(key);
    if (!stored) return fallback;
    return { ...fallback, ...JSON.parse(stored) };
  } catch {
    return fallback;
  }
}

function saveUIState(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

const TOP_VENUES = [
  'ieee symposium on security and privacy',
  'ieee s&p',
  'acm ccs',
  'usenix security',
  'ndss',
  'crypto',
  'eurocrypt',
  'asiacrypt',
  'sigmod',
  'vldb',
  'pvldb',
  'popets',
  'neurips',
  'icml',
  'iclr',
];

const JOURNAL_VENUES = [
  'ieee tifs',
  'ieee tkde',
  'ieee tdsc',
  'acm tops',
  'acm tods',
  'journal',
  'transactions',
];

const PREPRINT_VENUES = [
  'arxiv',
  'arxiv.org',
];

function getSourceBadges(article) {
  const haystack = `${article.source || ''} ${article.url || ''}`.toLowerCase();
  let sourceType = UI_SOURCE_TYPE_META[article.source_type] ?? { label: article.source_type || '\u5176\u4ed6\u6765\u6e90', tone: 'other' };
  if (article.source_type === 'imported') {
    if (haystack.includes('mp.weixin.qq.com')) {
      sourceType = UI_SOURCE_TYPE_META.wechat_authority;
    } else if (
      haystack.includes('arxiv.org')
      || haystack.includes('openreview.net')
      || haystack.includes('ieee.org')
      || haystack.includes('acm.org')
      || haystack.includes('springer')
      || haystack.includes('nature.com')
      || haystack.includes('sciencedirect.com')
      || haystack.includes('usenix.org')
      || haystack.includes('ndss-symposium.org')
      || haystack.includes('iacr.org')
    ) {
      sourceType = UI_SOURCE_TYPE_META.international_academic;
    } else if (
      haystack.includes('gov.cn')
      || haystack.includes('caict.ac.cn')
      || haystack.includes('tc260.org.cn')
      || haystack.includes('ccf.org.cn')
    ) {
      sourceType = UI_SOURCE_TYPE_META.domestic_authority;
    } else {
      sourceType = { label: '\u5176\u4ed6\u6765\u6e90', tone: 'other' };
    }
  }
  let venue = { label: '\u5176\u4ed6', tone: 'other' };
  if (article.source_type === 'wechat_authority' || haystack.includes('mp.weixin.qq.com')) {
    venue = { label: '\u516c\u4f17\u53f7', tone: 'wechat' };
  } else if (PREPRINT_VENUES.some((name) => haystack.includes(name))) {
    venue = { label: '\u9884\u5370\u672c', tone: 'preprint' };
  } else if (TOP_VENUES.some((name) => haystack.includes(name))) {
    venue = { label: '\u9876\u4f1a', tone: 'conference' };
  } else if (JOURNAL_VENUES.some((name) => haystack.includes(name))) {
    venue = { label: '\u671f\u520a', tone: 'journal' };
  }
  return { sourceType, venue };
}

async function api(path, options) {
  const response = await fetch(`${API_BASE}${path}`, options);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `HTTP ${response.status}`);
  }
  return response.json();
}

function hasAIConfig(config) {
  return Boolean(config.api_key?.trim() && config.base_url?.trim() && config.model?.trim());
}

function hasTranslationConfig(config) {
  if (!config.enabled) return false;
  if (config.provider === 'baidu') return Boolean(config.app_id?.trim() && config.secret_key?.trim());
  if (config.provider === 'libretranslate') return Boolean(config.base_url?.trim());
  return false;
}

function hasEnrichmentConfig(aiConfig, translationConfig) {
  return hasAIConfig(aiConfig) || hasTranslationConfig(translationConfig);
}

function formatBatchLabel(batch) {
  const value = String(batch || '').trim();
  if (!value) return '未记录批次';
  return value.replace('T', ' ').slice(0, 19);
}

function formatDateTime(value) {
  const text = String(value || '').trim();
  if (!text) return '未记录';
  return text.replace('T', ' ').slice(0, 19);
}

function summarizeBatchNotice(actionLabel, result) {
  const stats = result?.stats || {};
  const total = stats.total ?? 0;
  const processed = stats.processed ?? 0;
  const failed = stats.failed ?? 0;
  const failures = Array.isArray(result?.failures) ? result.failures : [];
  if (!failed) {
    return `${actionLabel}完成：待处理 ${total} 条，成功 ${processed} 条，失败 0 条。`;
  }
  const preview = failures
    .slice(0, 3)
    .map((item) => item?.title || item?.id || '未命名条目')
    .join('；');
  const suffix = failures.length > 3 ? '；其余失败可在运行日志查看。' : '。';
  return `${actionLabel}完成：待处理 ${total} 条，成功 ${processed} 条，失败 ${failed} 条。失败样本：${preview}${suffix}`;
}

function parseImportUrls(raw) {
  const text = String(raw || '').trim();
  if (!text) return [];
  const matches = text.match(/https?:\/\/[^\s<>"']+/g) || [];
  return Array.from(new Set(matches.map((item) => item.trim()).filter(Boolean)));
}

function App() {
  const [page, setPage] = React.useState('today');
  const [articles, setArticles] = React.useState([]);
  const [logs, setLogs] = React.useState([]);
  const [config, setConfig] = React.useState(null);
  const [configDraft, setConfigDraft] = React.useState('');
  const [aiConfig, setAIConfig] = React.useState(loadAIConfig);
  const [translationConfig, setTranslationConfig] = React.useState(loadTranslationConfig);
  const [detail, setDetail] = React.useState(null);
  const [previousPage, setPreviousPage] = React.useState('today');
  const [queryByPage, setQueryByPage] = React.useState(() => loadUIState('privacy-radar-query-by-page', {}));
  const [busy, setBusy] = React.useState(false);
  const [notice, setNotice] = React.useState('');
  const [importUrl, setImportUrl] = React.useState('');
  const query = queryByPage[page] || '';

  const statusForPage = React.useMemo(() => {
    if (page === 'latest') return 'candidate';
    if (page === 'today') return 'candidate';
    if (page === 'reading') return 'reading';
    if (page === 'selected') return 'selected';
    if (page === 'history') return null;
    return null;
  }, [page]);

  const loadArticles = React.useCallback(async () => {
    const params = new URLSearchParams();
    if (statusForPage) params.set('status', statusForPage);
    if (page === 'latest') params.set('latest_fetch_only', '1');
    if (query.trim()) params.set('q', query.trim());
    const data = await api(`/api/articles?${params.toString()}`);
    setArticles(data);
  }, [page, query, statusForPage]);

  const loadLogs = React.useCallback(async () => {
    setLogs(await api('/api/logs'));
  }, []);

  const loadConfig = React.useCallback(async () => {
    const nextConfig = await api('/api/config');
    setConfig(nextConfig);
    setConfigDraft((current) => (current.trim() ? current : JSON.stringify(nextConfig, null, 2)));
  }, []);

  React.useEffect(() => {
    loadConfig().catch((error) => setNotice(error.message));
  }, [loadConfig]);

  React.useEffect(() => {
    if (page === 'config') {
      loadConfig().catch((error) => setNotice(error.message));
      return;
    }
    if (page === 'logs') {
      loadLogs().catch((error) => setNotice(error.message));
      return;
    }
    if (page === 'detail') {
      return;
    }
    loadArticles().catch((error) => setNotice(error.message));
  }, [loadArticles, loadConfig, loadLogs, page]);

  React.useEffect(() => {
    saveUIState('privacy-radar-query-by-page', queryByPage);
  }, [queryByPage]);

  const runFetch = async () => {
    setBusy(true);
    setNotice('正在抓取候选来源...');
    try {
      const result = await api('/api/fetch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rows: 30, days: 30, min_score: 45, max_age_days: 90, dry_run: false }),
      });
      setNotice(`抓取完成：候选 ${result.candidates_total} 条，新增 ${result.stats.inserted} 条，去重 ${result.stats.duplicates} 条。`);
      setPage('latest');
      await loadArticles();
      if (hasEnrichmentConfig(aiConfig, translationConfig)) {
        try {
          setNotice('抓取完成，正在串行生成标题/摘要翻译和推荐理由...');
          const aiResult = await api('/api/ai/enrich-batch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ai: aiConfig, translation: translationConfig, status: 'candidate', limit: 100 }),
          });
          setNotice(`AI 生成完成：处理 ${aiResult.stats.processed} 条，失败 ${aiResult.stats.failed} 条。`);
          await loadArticles();
        } catch (error) {
          setNotice(`抓取已完成，但 AI 生成失败：${error.message}`);
        }
      }
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(false);
    }
  };

  const runConfiguredFetch = async () => {
    setBusy(true);
    setNotice('\u6b63\u5728\u6293\u53d6\u5019\u9009\u8bba\u6587...');
    try {
      const activeConfig = config ?? await api('/api/config');
      if (!config) setConfig(activeConfig);
      const enabledSources = activeConfig.enabled_fetch_sources || [];
      if (!enabledSources.length) {
        throw new Error('\u8bf7\u5148\u5728\u8bbe\u7f6e\u9875\u9009\u62e9\u6293\u53d6\u6765\u6e90');
      }
      const result = await api('/api/fetch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          rows: activeConfig.fetch_rows ?? 12,
          days: activeConfig.fetch_days ?? 1095,
          min_score: activeConfig.fetch_min_score ?? 45,
          max_age_days: activeConfig.fetch_max_age_days ?? 1095,
          dry_run: false,
        }),
      });
      const sourceCount = Object.keys(result.source_counts || {}).length;
      setNotice(`\u6293\u53d6\u5b8c\u6210\uff1a${sourceCount} \u4e2a\u6765\u6e90\uff0c${result.candidates_total} \u6761\u539f\u59cb\u7ed3\u679c\uff0c\u65b0\u589e ${result.stats.inserted} \u6761\uff0c\u91cd\u590d ${result.stats.duplicates} \u6761\uff0c\u8fc7\u6ee4 ${result.stats.filtered} \u6761\u3002`);
      setPage('latest');
      await loadArticles();
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(false);
    }
  };

  const runLegacyAIEnrich = async () => {
    if (!hasEnrichmentConfig(aiConfig, translationConfig)) {
      setNotice('请先在“来源/关键词配置”里填写 AI 配置，或启用并填写机器翻译配置。');
      return;
    }
    const batchStatus = page === 'latest'
      ? 'candidate'
      : page === 'today'
      ? 'candidate'
      : page === 'reading'
        ? 'reading'
        : page === 'selected'
          ? 'selected'
          : page === 'history'
            ? 'all'
            : 'all';
    const isDetail = page === 'detail' && detail?.id;
    setBusy(true);
    try {
      setNotice(isDetail ? '正在生成当前论文的标题/摘要翻译和推荐理由...' : '正在补齐当前范围内的标题/摘要翻译和推荐理由...');
      if (isDetail) {
        const result = await api('/api/ai/enrich', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ai: aiConfig, translation: translationConfig, article_id: detail.id }),
        });
        setDetail(result.article);
        setNotice('当前论文的标题/摘要翻译和推荐理由已生成。');
        return;
      }
      const result = await api('/api/ai/enrich-batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ai: aiConfig, translation: translationConfig, status: batchStatus, limit: 200, latest_fetch_only: page === 'latest' }),
      });
      setNotice(summarizeBatchNotice('AI 补齐', result));
      await loadArticles();
    } catch (error) {
      setNotice(`AI 生成失败：${error.message}`);
    } finally {
      setBusy(false);
    }
  };

  const batchStatus = page === 'latest'
    ? 'candidate'
    : page === 'today'
    ? 'candidate'
    : page === 'reading'
      ? 'reading'
        : page === 'selected'
          ? 'selected'
          : page === 'history'
            ? 'all'
            : 'all';
  const latestFetchOnly = page === 'latest';
  const isDetailPage = page === 'detail' && detail?.id;

  const runTranslationEnrich = async () => {
    if (!hasTranslationConfig(translationConfig)) {
      setNotice('请先在设置页启用并填写机器翻译配置。');
      return;
    }
    setBusy(true);
    try {
      setNotice(isDetailPage ? '正在翻译当前论文的标题和摘要...' : '正在翻译当前范围内的标题和摘要...');
      if (isDetailPage) {
        const result = await api('/api/ai/enrich', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            ai: DEFAULT_AI_CONFIG,
            translation: translationConfig,
            article_id: detail.id,
            translate: true,
            recommend: false,
          }),
        });
        setDetail(result.article);
        setNotice('当前论文的标题和摘要已翻译。');
        return;
      }
      const result = await api('/api/ai/enrich-batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ai: DEFAULT_AI_CONFIG,
          translation: translationConfig,
          status: batchStatus,
          limit: 200,
          translate: true,
          recommend: false,
          latest_fetch_only: latestFetchOnly,
        }),
      });
      setNotice(summarizeBatchNotice('翻译', result));
      await loadArticles();
    } catch (error) {
      setNotice(`翻译失败：${error.message}`);
    } finally {
      setBusy(false);
    }
  };

  const runAIEnrich = async () => {
    if (!hasAIConfig(aiConfig)) {
      setNotice('请先在设置页填写 AI 配置。');
      return;
    }
    setBusy(true);
    try {
      setNotice(isDetailPage ? '正在生成当前论文的 AI 解读...' : '正在生成当前范围内的 AI 解读...');
      if (isDetailPage) {
        const result = await api('/api/ai/enrich', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            ai: aiConfig,
            translation: translationConfig,
            article_id: detail.id,
            translate: false,
            recommend: true,
          }),
        });
        setDetail(result.article);
        setNotice('当前论文的 AI 解读已生成。');
        return;
      }
      const result = await api('/api/ai/enrich-batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ai: aiConfig,
          translation: translationConfig,
          status: batchStatus,
          limit: 200,
          translate: false,
          recommend: true,
          latest_fetch_only: latestFetchOnly,
        }),
      });
      setNotice(summarizeBatchNotice('AI 解读', result));
      await loadArticles();
    } catch (error) {
      setNotice(`AI 解读失败：${error.message}`);
    } finally {
      setBusy(false);
    }
  };

  const refresh = async () => {
    setBusy(true);
    try {
      if (page === 'logs') await loadLogs();
      else if (page === 'config') await loadConfig();
      else if (page === 'detail' && detail) setDetail(await api(`/api/articles/${detail.id}`));
      else await loadArticles();
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(false);
    }
  };

  const openDetail = async (article) => {
    setPreviousPage(page);
    setDetail(await api(`/api/articles/${article.id}`));
    setPage('detail');
  };

  const closeDetail = () => {
    setDetail(null);
    setPage(previousPage);
  };

  const changeStatus = async (article, status) => {
    const updated = await api(`/api/articles/${article.id}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    });
    setNotice(`已标记为${STATUS_META[status].label}`);
    setDetail((current) => (current?.id === updated.id ? updated : current));
    await loadArticles();
  };

  const bulkChangeStatus = async (articleIds, status) => {
    const ids = Array.from(new Set((articleIds || []).filter(Boolean)));
    if (!ids.length) return;
    setBusy(true);
    try {
      const results = await Promise.allSettled(
        ids.map((articleId) => api(`/api/articles/${articleId}/status`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status }),
        })),
      );
      const success = results.filter((item) => item.status === 'fulfilled').length;
      const failed = results.length - success;
      setNotice(`批量标记为${STATUS_META[status].label}：成功 ${success} 篇，失败 ${failed} 篇。`);
      await loadArticles();
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(false);
    }
  };

  const uploadSeen = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const form = new FormData();
    form.append('file', file);
    setBusy(true);
    try {
      const result = await api('/api/upload-seen', { method: 'POST', body: form });
      setNotice(`已写入去重库：${result.inserted} 条，解析标题 ${result.titles} 个、链接 ${result.urls} 个。`);
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(false);
      event.target.value = '';
    }
  };

  const importArticleUrl = async (event) => {
    event.preventDefault();
    const urls = parseImportUrls(importUrl);
    if (!urls.length) {
      setNotice('请粘贴至少一个有效的论文链接。');
      return;
    }
    const importStatus = page === 'selected' ? 'selected' : page === 'reading' ? 'reading' : page === 'today' ? 'candidate' : 'shared';
    setBusy(true);
    setNotice(urls.length === 1 ? '正在抓取目标论文...' : `正在批量抓取 ${urls.length} 条论文链接...`);
    try {
      const results = await Promise.allSettled(
        urls.map((url) => api('/api/articles/import-url', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url, status: importStatus }),
        })),
      );
      const successResults = results.filter((item) => item.status === 'fulfilled').map((item) => item.value);
      const createdCount = successResults.filter((item) => item.created).length;
      const updatedCount = successResults.length - createdCount;
      const failedEntries = results
        .map((item, index) => ({ item, url: urls[index] }))
        .filter(({ item }) => item.status === 'rejected');
      setImportUrl('');
      const targetPage = importStatus === 'shared' ? 'history' : importStatus === 'selected' ? 'selected' : importStatus === 'reading' ? 'reading' : 'today';
      setPage(targetPage);
      if (!successResults.length) {
        const firstFailure = failedEntries[0]?.item?.reason?.message || '批量导入失败';
        throw new Error(firstFailure);
      }
      const failurePreview = failedEntries
        .slice(0, 2)
        .map(({ url }) => url)
        .join('；');
      const failureSuffix = failedEntries.length > 2 ? '；其余失败项请重试。' : '';
      setNotice(
        failedEntries.length
          ? `批量导入完成：新增 ${createdCount} 条，更新 ${updatedCount} 条，失败 ${failedEntries.length} 条。失败样本：${failurePreview}${failureSuffix}`
          : `批量导入完成：新增 ${createdCount} 条，更新 ${updatedCount} 条。`,
      );
      if (page === targetPage) await loadArticles();
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(false);
    }
  };

  const exportMarkdown = async (markShared) => {
    const result = await api('/api/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mark_shared: markShared }),
    });
    const blob = new Blob([result.markdown], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = result.filename;
    anchor.click();
    URL.revokeObjectURL(url);
    setNotice(`已导出 ${result.count} 条入选文章${markShared ? '，并标记为已分享' : ''}。`);
    await loadArticles();
  };

  const saveConfig = async (nextConfig) => {
    setBusy(true);
    try {
      const result = await api('/api/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(nextConfig),
      });
      setConfig(result.config);
      setConfigDraft(JSON.stringify(result.config, null, 2));
      setNotice('配置已保存。');
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="shell">
      <aside className="rail">
        <div className="brand">
          <ShieldCheck size={28} />
          <div>
            <strong>Privacy Radar</strong>
            <span>研究情报筛选</span>
          </div>
        </div>
        <nav>
          {Object.entries(UI_PAGE_META).map(([key, item]) => {
            const Icon = item.icon;
            return (
              <button key={key} className={page === key || (page === 'detail' && previousPage === key) ? 'nav active' : 'nav'} onClick={() => { setPage(key); setDetail(null); }}>
                <Icon size={18} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">DATA SECURITY / PRIVACY PROTECTION</p>
            <h1>{page === 'detail' ? '论文详情' : UI_PAGE_META[page].label}</h1>
          </div>
          <div className="actions">
            <label className="iconButton" title="上传腾讯文档 CSV 去重">
              <FileUp size={18} />
              <input type="file" accept=".csv,.txt,.md" onChange={uploadSeen} />
            </label>
            <button className="iconButton" onClick={refresh} title="刷新">
              <RotateCcw size={18} />
            </button>
            {(page === 'latest' || page === 'today' || page === 'reading' || page === 'selected' || page === 'history' || page === 'detail') && (
              <button className="secondary" onClick={runTranslationEnrich} disabled={busy || (page === 'detail' && !detail)}>
                {busy ? <Loader2 className="spin" size={18} /> : <Languages size={18} />}
                翻译标题/摘要
              </button>
            )}
            {(page === 'latest' || page === 'today' || page === 'reading' || page === 'selected' || page === 'history' || page === 'detail') && (
              <button className="secondary" onClick={runAIEnrich} disabled={busy || (page === 'detail' && !detail)}>
                {busy ? <Loader2 className="spin" size={18} /> : <Sparkles size={18} />}
                AI生成解读
              </button>
            )}
            <button className="primary" onClick={runConfiguredFetch} disabled={busy}>
              {busy ? <Loader2 className="spin" size={18} /> : <Play size={18} />}
              开始抓取
            </button>
          </div>
        </header>

        {notice && <div className="notice">{notice}</div>}

        {(page === 'latest' || page === 'today' || page === 'reading' || page === 'selected' || page === 'history') && (
          <ArticlePage
            key={page}
            page={page}
            articles={articles}
            query={query}
            setQuery={(value) => setQueryByPage((current) => ({ ...current, [page]: value }))}
            openDetail={openDetail}
            changeStatus={changeStatus}
            bulkChangeStatus={bulkChangeStatus}
            exportMarkdown={exportMarkdown}
            importUrl={importUrl}
            setImportUrl={setImportUrl}
            importArticleUrl={importArticleUrl}
            busy={busy}
          />
        )}
        {page === 'detail' && (
          <DetailPage article={detail} changeStatus={changeStatus} close={closeDetail} />
        )}
        {page === 'config' && (
          <ConfigPage
            config={config}
            draft={configDraft}
            setDraft={setConfigDraft}
            saveConfig={saveConfig}
            aiConfig={aiConfig}
            setAIConfig={setAIConfig}
            translationConfig={translationConfig}
            setTranslationConfig={setTranslationConfig}
          />
        )}
        {page === 'logs' && <LogsPage logs={logs} />}
      </section>
    </main>
  );
}

function ArticlePage({ page, articles, query, setQuery, openDetail, changeStatus, bulkChangeStatus, exportMarkdown, importUrl, setImportUrl, importArticleUrl, busy }) {
  const defaultFilters = React.useMemo(() => ({
    markShared: true,
    sourceFilter: 'all',
    venueFilter: 'all',
    statusFilter: 'all',
    translationFilter: 'all',
    aiFilter: 'all',
    batchFilter: 'all',
    pendingOnly: false,
  }), []);
  const [pageFilters, setPageFilters] = React.useState(() => loadUIState(`privacy-radar-filters-${page}`, defaultFilters));
  const [selectedIds, setSelectedIds] = React.useState([]);
  const {
    markShared,
    sourceFilter,
    venueFilter,
    statusFilter,
    translationFilter,
    aiFilter,
    batchFilter,
    pendingOnly,
  } = pageFilters;

  React.useEffect(() => {
    setPageFilters(loadUIState(`privacy-radar-filters-${page}`, defaultFilters));
    setSelectedIds([]);
  }, [defaultFilters, page]);

  React.useEffect(() => {
    saveUIState(`privacy-radar-filters-${page}`, pageFilters);
  }, [page, pageFilters]);

  const updateFilters = (patch) => {
    setPageFilters((current) => ({ ...current, ...patch }));
  };

  const batchOptions = React.useMemo(() => {
    const values = Array.from(new Set(articles.map((article) => String(article.fetch_batch || '').trim())));
    return values.sort((a, b) => b.localeCompare(a));
  }, [articles]);

  const filteredArticles = React.useMemo(() => {
    return articles.filter((article) => {
      const badges = getSourceBadges(article);
      const sourceTone = badges.sourceType.tone || 'other';
      const venueTone = badges.venue.tone || 'other';
      const hasTranslation = Boolean(article.translated_title?.trim() || article.translated_summary?.trim());
      const hasAI = Array.isArray(article.ai_recommendation) && article.ai_recommendation.length > 0;
      if (sourceFilter !== 'all' && sourceTone !== sourceFilter) return false;
      if (venueFilter !== 'all' && venueTone !== venueFilter) return false;
      if (statusFilter !== 'all' && article.status !== statusFilter) return false;
      if (translationFilter === 'translated' && !hasTranslation) return false;
      if (translationFilter === 'untranslated' && hasTranslation) return false;
      if (aiFilter === 'generated' && !hasAI) return false;
      if (aiFilter === 'missing' && hasAI) return false;
      if (batchFilter !== 'all' && String(article.fetch_batch || '') !== batchFilter) return false;
      if (pendingOnly && (hasTranslation || hasAI)) return false;
      return true;
    });
  }, [aiFilter, articles, batchFilter, pendingOnly, sourceFilter, statusFilter, translationFilter, venueFilter]);

  React.useEffect(() => {
    const validIds = new Set(filteredArticles.map((article) => article.id));
    setSelectedIds((current) => current.filter((id) => validIds.has(id)));
  }, [filteredArticles]);

  const stats = React.useMemo(() => {
    const total = filteredArticles.length;
    const average = total ? Math.round(filteredArticles.reduce((sum, item) => sum + item.score, 0) / total) : 0;
    const selected = filteredArticles.filter((item) => item.status === 'selected').length;
    return { total, average, selected };
  }, [filteredArticles]);

  const selectable = page === 'latest';
  const allFilteredSelected = selectable && filteredArticles.length > 0 && filteredArticles.every((article) => selectedIds.includes(article.id));

  const toggleSelected = (articleId) => {
    setSelectedIds((current) => (
      current.includes(articleId)
        ? current.filter((id) => id !== articleId)
        : [...current, articleId]
    ));
  };

  const toggleSelectAll = () => {
    if (!selectable) return;
    setSelectedIds(allFilteredSelected ? [] : filteredArticles.map((article) => article.id));
  };

  const handleBulkStatus = async (status) => {
    await bulkChangeStatus(selectedIds, status);
    setSelectedIds([]);
  };

  return (
    <div className="contentGrid">
      <section className="listPanel">
        <div className="toolstrip toolstripFilters">
          <div className="filterStack">
            <div className="searchBox">
              <Search size={17} />
              <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索标题、摘要或来源" />
            </div>
            <div className="filterRow">
              <select value={sourceFilter} onChange={(event) => updateFilters({ sourceFilter: event.target.value })}>
                <option value="all">全部来源</option>
                <option value="academic">国际学术</option>
                <option value="authority">国内权威</option>
                <option value="wechat">公众号</option>
                <option value="search">搜索来源</option>
              </select>
              <select value={venueFilter} onChange={(event) => updateFilters({ venueFilter: event.target.value })}>
                <option value="all">全部会刊</option>
                <option value="conference">顶会</option>
                <option value="journal">期刊</option>
                <option value="preprint">预印本</option>
                <option value="wechat">公众号</option>
                <option value="other">其他</option>
              </select>
              <select value={statusFilter} onChange={(event) => updateFilters({ statusFilter: event.target.value })}>
                <option value="all">全部状态</option>
                <option value="candidate">候选</option>
                <option value="reading">待读</option>
                <option value="selected">已选</option>
                <option value="shared">已分享</option>
                <option value="rejected">驳回</option>
              </select>
              <select value={translationFilter} onChange={(event) => updateFilters({ translationFilter: event.target.value })}>
                <option value="all">翻译状态</option>
                <option value="translated">已翻译</option>
                <option value="untranslated">未翻译</option>
              </select>
              <select value={aiFilter} onChange={(event) => updateFilters({ aiFilter: event.target.value })}>
                <option value="all">解读状态</option>
                <option value="generated">已解读</option>
                <option value="missing">未解读</option>
              </select>
              {page === 'today' && (
                <select value={batchFilter} onChange={(event) => updateFilters({ batchFilter: event.target.value })}>
                  <option value="all">全部批次</option>
                  {batchOptions.map((batch) => (
                    <option key={batch || 'empty'} value={batch}>{formatBatchLabel(batch)}</option>
                  ))}
                </select>
              )}
              <label className="toggleFilter">
                <input type="checkbox" checked={pendingOnly} onChange={(event) => updateFilters({ pendingOnly: event.target.checked })} />
                <span>只看未处理</span>
              </label>
            </div>
          </div>
          {page === 'latest' && (
            <div className="bulkBox">
              <label className="toggleFilter bulkSelectAll">
                <input type="checkbox" checked={allFilteredSelected} onChange={toggleSelectAll} />
                <span>全选当前</span>
              </label>
              <span className="bulkCount">已选 {selectedIds.length} 篇</span>
              <button className="secondary" onClick={() => handleBulkStatus('reading')} disabled={busy || !selectedIds.length}>
                标记待读
              </button>
              <button className="secondary" onClick={() => handleBulkStatus('selected')} disabled={busy || !selectedIds.length}>
                标记已选
              </button>
              <button className="secondary" onClick={() => handleBulkStatus('rejected')} disabled={busy || !selectedIds.length}>
                批量驳回
              </button>
            </div>
          )}
          {page === 'selected' && (
            <div className="exportBox">
              <label>
                <input type="checkbox" checked={markShared} onChange={(event) => updateFilters({ markShared: event.target.checked })} />
                导出后标记已分享
              </label>
              <button className="secondary" onClick={() => exportMarkdown(markShared)}>
                <Download size={17} />
                导出 Markdown
              </button>
            </div>
          )}
          {(page === 'today' || page === 'reading' || page === 'selected' || page === 'history') && (
            <form className="importBox" onSubmit={importArticleUrl}>
              <div className="importUrlBox">
                <div className="importUrlHead">
                  <Link2 size={17} />
                  <span>导入论文链接</span>
                </div>
                <textarea
                  value={importUrl}
                  onChange={(event) => setImportUrl(event.target.value)}
                  placeholder={
                    page === 'selected'
                      ? '每行一个链接，导入到已选文章'
                      : page === 'reading'
                        ? '每行一个链接，导入到待读论文'
                        : page === 'today'
                          ? '每行一个链接，导入到候选池'
                          : '每行一个链接，导入到历史库'
                  }
                />
              </div>
              <button className="secondary" disabled={busy || !parseImportUrls(importUrl).length}>
                <FileUp size={17} />
                批量导入
              </button>
            </form>
          )}
        </div>
        <div className="articleList">
          {filteredArticles.map((article) => (
            <ArticleRow
              key={article.id}
              article={article}
              openDetail={openDetail}
              changeStatus={changeStatus}
              selectable={selectable}
              selected={selectedIds.includes(article.id)}
              toggleSelected={toggleSelected}
            />
          ))}
          {!filteredArticles.length && (
            <div className="empty">
              {page === 'latest'
                ? '最近一次抓取还没有新增候选，先执行一次抓取，或检查本次结果是否都被去重/过滤。'
                : '没有匹配的条目，可以调整筛选条件或导入论文链接。'}
            </div>
          )}
        </div>
      </section>
      <aside className="metrics">
        <Metric label="当前条目" value={stats.total} />
        <Metric label="平均评分" value={stats.average} />
        <Metric label="已选数量" value={stats.selected} />
        <div className="statusLegend">
          {Object.entries(UI_STATUS_META).map(([key, item]) => {
            const Icon = item.icon;
            return (
              <span key={key}>
                <Icon size={14} />
                {item.label}
              </span>
            );
          })}
        </div>
      </aside>
    </div>
  );
}

function ArticleRow({ article, openDetail, changeStatus, selectable = false, selected = false, toggleSelected = () => {} }) {
  const StatusIcon = UI_STATUS_META[article.status]?.icon ?? ListFilter;
  const badges = getSourceBadges(article);
  const englishTitle = article.title?.trim();
  const translatedTitle = article.translated_title?.trim();
  const displayTitle = englishTitle || translatedTitle || '未命名论文';
  return (
    <article className={selectable ? 'articleRow selectable' : 'articleRow'} onClick={() => openDetail(article)}>
      {selectable && (
        <label className="rowSelector" onClick={(event) => event.stopPropagation()}>
          <input type="checkbox" checked={selected} onChange={() => toggleSelected(article.id)} />
        </label>
      )}
      <div className="score">{article.score}</div>
      <div className="articleMain">
        <h2>{displayTitle}</h2>
        {translatedTitle && translatedTitle !== displayTitle && <p className="translatedTitle">{translatedTitle}</p>}
        <div className="metaLine">
          <span className={`sourceBadge ${badges.sourceType.tone}`}>{badges.sourceType.label}</span>
          <span className={`venueBadge ${badges.venue.tone}`}>{badges.venue.label}</span>
          <span>{article.source || '未知来源'}</span>
          <span>{article.published || '无日期'}</span>
          <span>首次发现 {formatDateTime(article.created_at)}</span>
          <span>最近抓取 {formatDateTime(article.last_fetch_at)}</span>
          <span className={`status ${article.status}`}>
            <StatusIcon size={14} />
            {UI_STATUS_META[article.status]?.label}
          </span>
        </div>
        <p>{(article.reasons || []).slice(0, 3).join('；') || '暂无推荐理由'}</p>
      </div>
      <div className="rowActions" onClick={(event) => event.stopPropagation()}>
        <StatusButtons article={article} changeStatus={changeStatus} compact />
        <a href={article.url} target="_blank" rel="noreferrer" className="iconButton" title="打开原文">
          <ExternalLink size={16} />
        </a>
      </div>
    </article>
  );
}

function StatusButtons({ article, changeStatus, compact = false }) {
  return (
    <div className={compact ? 'statusButtons compact' : 'statusButtons'}>
      {Object.entries(UI_STATUS_META).map(([status, item]) => {
        const Icon = item.icon;
        return (
          <button
            key={status}
            className={article.status === status ? 'statusButton active' : 'statusButton'}
            onClick={() => changeStatus(article, status)}
            title={item.label}
          >
            <Icon size={15} />
            {!compact && item.label}
          </button>
        );
      })}
    </div>
  );
}

function DetailPage({ article, changeStatus, close }) {
  if (!article) {
    return (
      <section className="detailPage mutedPanel">
        <ShieldCheck size={30} />
        <p>选择一篇文章查看摘要、作者、评分和推荐理由。</p>
      </section>
    );
  }
  const badges = getSourceBadges(article);
  const englishTitle = article.title?.trim();
  const translatedTitle = article.translated_title?.trim();
  const displayTitle = englishTitle || translatedTitle || '未命名论文';
  return (
    <section className="detailPage">
      <button className="secondary backButton" onClick={close}>
        <ArrowLeft size={18} />
        返回列表
      </button>
      <div className="detailScore">{article.score}</div>
      <h2>{displayTitle}</h2>
      {translatedTitle && translatedTitle !== displayTitle && <p className="translatedTitle detailTranslatedTitle">{translatedTitle}</p>}
      <div className="detailMeta">
        <span className={`sourceBadge ${badges.sourceType.tone}`}>{badges.sourceType.label}</span>
        <span className={`venueBadge ${badges.venue.tone}`}>{badges.venue.label}</span>
        <span>{article.source}</span>
        <span>{article.published || '无日期'}</span>
        <span>首次发现 {formatDateTime(article.created_at)}</span>
        <span>最近抓取 {formatDateTime(article.last_fetch_at)}</span>
        <span>{UI_STATUS_META[article.status]?.label}</span>
      </div>
      <StatusButtons article={article} changeStatus={changeStatus} />
      <section>
        <h3>英文原摘要</h3>
        <p>{article.summary || '暂无摘要。'}</p>
      </section>
      <section>
        <h3>中文摘要</h3>
        <p>{article.translated_summary || '暂未生成中文摘要。'}</p>
      </section>
      <section>
        <h3>AI 解读</h3>
        {(article.ai_recommendation || []).length > 0 ? (
          <ul>
            {article.ai_recommendation.map((reason) => <li key={reason}>{reason}</li>)}
          </ul>
        ) : (
          <p>暂未生成 AI 解读。</p>
        )}
      </section>
      <section>
        <h3>作者</h3>
        <p>{article.authors || '暂无作者信息。'}</p>
      </section>
      <section>
        <h3>推荐理由</h3>
        <ul>
          {(article.reasons || []).map((reason) => <li key={reason}>{reason}</li>)}
        </ul>
      </section>
      <a className="primary wide" href={article.url} target="_blank" rel="noreferrer">
        <ExternalLink size={18} />
        打开原始链接
      </a>
    </section>
  );
}

function runtimeConfigToPersisted(config) {
  const next = { ...(config || {}) };
  delete next.reference_sources;
  delete next.fetch_source_catalog;
  return next;
}

function fetchSourceName(source) {
  return source?.name || '';
}

function fetchSourceLabel(source) {
  const parts = [source?.tier, source?.category].filter(Boolean);
  return parts.length ? `${fetchSourceName(source)} (${parts.join(' / ')})` : fetchSourceName(source);
}

function ConfigPage({ config, draft, setDraft, saveConfig, aiConfig, setAIConfig, translationConfig, setTranslationConfig }) {
  const [sourceQuery, setSourceQuery] = React.useState('');
  const [showKey, setShowKey] = React.useState(false);
  const [showTranslationSecret, setShowTranslationSecret] = React.useState(false);

  const parsedDraft = React.useMemo(() => {
    try {
      return JSON.parse(draft || '{}');
    } catch {
      return null;
    }
  }, [draft]);

  const sourceCatalog = parsedDraft?.fetch_source_catalog || config?.fetch_source_catalog || [];
  const selectedSourceKeys = React.useMemo(() => {
    const configured = parsedDraft?.enabled_fetch_sources;
    if (Array.isArray(configured)) {
      return new Set(configured);
    }
    return new Set(sourceCatalog.map((source) => source.key).filter(Boolean));
  }, [parsedDraft, sourceCatalog]);

  const filteredSources = React.useMemo(() => {
    const keyword = sourceQuery.trim().toLowerCase();
    if (!keyword) return sourceCatalog;
    return sourceCatalog.filter((source) => {
      const text = `${source.key || ''} ${source.name || ''} ${source.category || ''} ${source.tier || ''}`.toLowerCase();
      return text.includes(keyword);
    });
  }, [sourceCatalog, sourceQuery]);

  const selectedCount = sourceCatalog.filter((source) => selectedSourceKeys.has(source.key)).length;

  const updateDraftConfig = (updater) => {
    if (!parsedDraft) return;
    const next = updater(parsedDraft);
    setDraft(JSON.stringify(next, null, 2));
  };

  const parseInteger = (value, fallback) => {
    const next = Number.parseInt(String(value ?? '').trim(), 10);
    return Number.isFinite(next) ? next : fallback;
  };

  const setSourceSelection = (key, checked) => {
    updateDraftConfig((current) => {
      const currentSources = current.fetch_source_catalog || sourceCatalog;
      const selected = new Set(
        Array.isArray(current.enabled_fetch_sources)
          ? current.enabled_fetch_sources
          : currentSources.map((source) => source.key).filter(Boolean),
      );
      if (checked) selected.add(key);
      else selected.delete(key);
      return {
        ...current,
        enabled_fetch_sources: currentSources.map((source) => source.key).filter((item) => selected.has(item)),
      };
    });
  };

  const setBatchSelection = (keys, checked) => {
    updateDraftConfig((current) => {
      const currentSources = current.fetch_source_catalog || sourceCatalog;
      const selected = new Set(
        Array.isArray(current.enabled_fetch_sources)
          ? current.enabled_fetch_sources
          : currentSources.map((source) => source.key).filter(Boolean),
      );
      keys.filter(Boolean).forEach((key) => {
        if (checked) selected.add(key);
        else selected.delete(key);
      });
      return {
        ...current,
        enabled_fetch_sources: currentSources.map((source) => source.key).filter((item) => selected.has(item)),
      };
    });
  };

  const updateFetchValue = (field, fallback) => (event) => {
    updateDraftConfig((current) => ({
      ...current,
      [field]: parseInteger(event.target.value, fallback),
    }));
  };

  const updateAIConfig = (patch) => {
    const next = { ...aiConfig, ...patch };
    setAIConfig(next);
    saveAIConfig(next);
  };

  const changeProvider = (provider) => {
    const preset = AI_PROVIDERS[provider] ?? AI_PROVIDERS.custom;
    updateAIConfig({
      provider,
      base_url: preset.baseUrl || aiConfig.base_url,
      model: preset.model || aiConfig.model,
    });
  };

  const updateTranslationConfig = (patch) => {
    const next = { ...translationConfig, ...patch };
    setTranslationConfig(next);
    saveTranslationConfig(next);
  };

  const changeTranslationProvider = (provider) => {
    const preset = TRANSLATION_PROVIDERS[provider] ?? TRANSLATION_PROVIDERS.baidu;
    updateTranslationConfig({
      provider,
      base_url: preset.baseUrl,
    });
  };

  const submit = () => {
    if (!parsedDraft) return;
    saveConfig(runtimeConfigToPersisted(JSON.parse(draft)));
  };

  const visibleKeys = filteredSources.map((source) => source.key);
  const conferenceKeys = sourceCatalog.filter((source) => source.category === 'conference').map((source) => source.key);
  const journalKeys = sourceCatalog.filter((source) => source.category === 'journal').map((source) => source.key);
  const preprintKeys = sourceCatalog.filter((source) => source.category === 'preprint').map((source) => source.key);

  return (
    <div className="settingsStack">
      <section className="aiPanel">
        <div className="panelTitle">
          <h2>{'\u6293\u53d6\u8303\u56f4'}</h2>
          <span>{selectedCount} / {sourceCatalog.length} {'\u5df2\u9009\u62e9'}</span>
        </div>
        <div className="sourceToolbar">
          <div className="searchBox sourceSearch">
            <Search size={17} />
            <input
              value={sourceQuery}
              onChange={(event) => setSourceQuery(event.target.value)}
              placeholder={'\u641c\u7d22\u4f1a\u8bae\u3001\u671f\u520a\u3001Tier \u6216 source key'}
            />
          </div>
          <button type="button" className="secondary" onClick={() => setBatchSelection(visibleKeys, true)} disabled={!parsedDraft || !visibleKeys.length}>
            {'\u5168\u9009\u5f53\u524d'}
          </button>
          <button type="button" className="secondary" onClick={() => setBatchSelection(visibleKeys, false)} disabled={!parsedDraft || !visibleKeys.length}>
            {'\u6e05\u7a7a\u5f53\u524d'}
          </button>
          <button type="button" className="secondary" onClick={() => setBatchSelection(conferenceKeys, true)} disabled={!parsedDraft || !conferenceKeys.length}>
            {'\u5168\u9009\u4f1a\u8bae'}
          </button>
          <button type="button" className="secondary" onClick={() => setBatchSelection(journalKeys, true)} disabled={!parsedDraft || !journalKeys.length}>
            {'\u5168\u9009\u671f\u520a'}
          </button>
          <button type="button" className="secondary" onClick={() => setBatchSelection(preprintKeys, true)} disabled={!parsedDraft || !preprintKeys.length}>
            {'\u5168\u9009\u9884\u5370\u672c'}
          </button>
        </div>
        <div className="sourceList">
          {filteredSources.map((source) => (
            <label className="sourceItem" key={source.key}>
              <input
                type="checkbox"
                checked={selectedSourceKeys.has(source.key)}
                onChange={(event) => setSourceSelection(source.key, event.target.checked)}
                disabled={!parsedDraft}
              />
              <span>
                <strong>{fetchSourceLabel(source)}</strong>
                <small>{source.key}</small>
              </span>
            </label>
          ))}
          {!filteredSources.length && <div className="empty inlineEmpty">{'\u6ca1\u6709\u5339\u914d\u7684\u6293\u53d6\u6e90\u3002'}</div>}
        </div>
      </section>

      <section className="aiPanel">
        <div className="panelTitle">
          <h2>{'\u6293\u53d6\u7b56\u7565'}</h2>
          <span>{'\u8fd9\u91cc\u53ea\u63a7\u5236\u6293\u53d6\uff0cAI \u7ffb\u8bd1/\u89e3\u8bfb\u5728\u4e0b\u65b9\u5355\u72ec\u914d\u7f6e\u3002'}</span>
        </div>
        <div className="aiGrid">
          <label>
            <span>{'\u6bcf\u4e2a source \u6293\u53d6\u6761\u6570'}</span>
            <input type="number" min="1" max="100" value={parsedDraft?.fetch_rows ?? ''} onChange={updateFetchValue('fetch_rows', config?.fetch_rows ?? 12)} />
          </label>
          <label>
            <span>{'\u56de\u6eaf\u5929\u6570'}</span>
            <input type="number" min="1" max="1095" value={parsedDraft?.fetch_days ?? ''} onChange={updateFetchValue('fetch_days', config?.fetch_days ?? 1095)} />
          </label>
          <label>
            <span>{'\u6700\u4f4e\u5165\u5e93\u5206\u6570'}</span>
            <input type="number" min="-100" max="200" value={parsedDraft?.fetch_min_score ?? ''} onChange={updateFetchValue('fetch_min_score', config?.fetch_min_score ?? 45)} />
          </label>
          <label>
            <span>{'\u6700\u5927\u53ef\u63a5\u53d7\u8bba\u6587\u5929\u9f84'}</span>
            <input type="number" min="0" max="1095" value={parsedDraft?.fetch_max_age_days ?? ''} onChange={updateFetchValue('fetch_max_age_days', config?.fetch_max_age_days ?? 1095)} />
          </label>
        </div>
      </section>

      <section className="aiPanel">
        <div className="panelTitle">
          <h2>{'AI \u6458\u8981\u4e0e\u89e3\u8bfb'}</h2>
          <span>{'API Key \u4ec5\u4fdd\u5b58\u5728\u6d4f\u89c8\u5668 localStorage\uff0c\u4e0d\u5199\u5165\u540e\u7aef\u3002'}</span>
        </div>
        <div className="aiGrid">
          <label>
            <span>{'\u4f9b\u5e94\u5546'}</span>
            <select value={aiConfig.provider === 'custom' ? 'other' : aiConfig.provider} onChange={(event) => changeProvider(event.target.value)}>
              {Object.entries(AI_PROVIDERS).filter(([key]) => key !== 'custom').map(([key, provider]) => (
                <option key={key} value={key}>{provider.label}</option>
              ))}
            </select>
          </label>
          <label>
            <span>Base URL</span>
            <input value={aiConfig.base_url} onChange={(event) => updateAIConfig({ base_url: event.target.value })} />
          </label>
          <label>
            <span>Model</span>
            <input value={aiConfig.model} onChange={(event) => updateAIConfig({ model: event.target.value })} placeholder={'deepseek-chat / qwen-plus'} />
          </label>
          <label>
            <span>API Key</span>
            <div className="keyInput">
              <input
                type={showKey ? 'text' : 'password'}
                value={aiConfig.api_key}
                onChange={(event) => updateAIConfig({ api_key: event.target.value })}
                placeholder={'\u4ec5\u4fdd\u5b58\u5728\u5f53\u524d\u6d4f\u89c8\u5668'}
              />
              <button className="secondary" onClick={() => setShowKey((value) => !value)}>{showKey ? '\u9690\u85cf' : '\u663e\u793a'}</button>
            </div>
          </label>
        </div>
      </section>

      <section className="aiPanel">
        <div className="panelTitle">
          <h2>{'\u673a\u5668\u7ffb\u8bd1'}</h2>
          <span>{'\u542f\u7528\u540e\u6807\u9898\u548c\u6458\u8981\u8d70\u7ffb\u8bd1 API\uff1bAI \u53ea\u8d1f\u8d23\u89e3\u8bfb\u4e0e\u63a8\u8350\u7406\u7531\u3002'}</span>
        </div>
        <div className="aiGrid">
          <label className="toggleLabel">
            <span>{'\u542f\u7528\u673a\u5668\u7ffb\u8bd1'}</span>
            <input type="checkbox" checked={translationConfig.enabled} onChange={(event) => updateTranslationConfig({ enabled: event.target.checked })} />
          </label>
          <label>
            <span>{'\u7ffb\u8bd1\u4f9b\u5e94\u5546'}</span>
            <select value={translationConfig.provider} onChange={(event) => changeTranslationProvider(event.target.value)}>
              {Object.entries(TRANSLATION_PROVIDERS).map(([key, provider]) => (
                <option key={key} value={key}>{provider.label}</option>
              ))}
            </select>
          </label>
          <label>
            <span>{'\u63a5\u53e3\u5730\u5740'}</span>
            <input value={translationConfig.base_url} onChange={(event) => updateTranslationConfig({ base_url: event.target.value })} />
          </label>
          <label>
            <span>{'\u6e90\u8bed\u8a00 / \u76ee\u6807\u8bed\u8a00'}</span>
            <div className="inlineInputs">
              <input value={translationConfig.source_lang} onChange={(event) => updateTranslationConfig({ source_lang: event.target.value })} />
              <input value={translationConfig.target_lang} onChange={(event) => updateTranslationConfig({ target_lang: event.target.value })} />
            </div>
          </label>
          {translationConfig.provider === 'baidu' ? (
            <>
              <label>
                <span>{'\u767e\u5ea6 App ID'}</span>
                <input value={translationConfig.app_id} onChange={(event) => updateTranslationConfig({ app_id: event.target.value })} />
              </label>
              <label>
                <span>{'\u767e\u5ea6\u5bc6\u94a5'}</span>
                <div className="keyInput">
                  <input
                    type={showTranslationSecret ? 'text' : 'password'}
                    value={translationConfig.secret_key}
                    onChange={(event) => updateTranslationConfig({ secret_key: event.target.value })}
                    placeholder={'\u4ec5\u4fdd\u5b58\u5728\u5f53\u524d\u6d4f\u89c8\u5668'}
                  />
                  <button className="secondary" onClick={() => setShowTranslationSecret((value) => !value)}>{showTranslationSecret ? '\u9690\u85cf' : '\u663e\u793a'}</button>
                </div>
              </label>
            </>
          ) : (
            <label>
              <span>API Key</span>
              <input
                type={showTranslationSecret ? 'text' : 'password'}
                value={translationConfig.api_key}
                onChange={(event) => updateTranslationConfig({ api_key: event.target.value })}
                placeholder={'\u53ef\u9009\uff0c\u4ec5\u4fdd\u5b58\u5728\u5f53\u524d\u6d4f\u89c8\u5668'}
              />
            </label>
          )}
        </div>
      </section>

      <section className="configPanel">
        <textarea value={draft} onChange={(event) => setDraft(event.target.value)} spellCheck="false" />
        <div className="configActions">
          <button className="primary" onClick={submit} disabled={!parsedDraft}>
            <Settings2 size={18} />
            {'\u4fdd\u5b58\u914d\u7f6e'}
          </button>
        </div>
      </section>
    </div>
  );
}

const LOG_ACTION_META = {
  fetch: '\u6293\u53d6',
  translate: '\u7ffb\u8bd1',
  ai: 'AI \u89e3\u8bfb',
  enrich: '\u7ffb\u8bd1 + AI \u89e3\u8bfb',
};

function formatLogSummary(log) {
  if (log.action_type === 'translate' || log.action_type === 'ai' || log.action_type === 'enrich') {
    const scope = log.source_counts?.scope || 'all';
    const latestFetchOnly = Boolean(log.source_counts?.latest_fetch_only);
    const scopeLabel = scope === 'single'
      ? '\u5355\u7bc7'
      : scope === 'all'
        ? '\u5168\u90e8'
        : UI_STATUS_META[scope]?.label || scope;
    const rangeLabel = latestFetchOnly ? `本次抓取 / ${scopeLabel}` : scopeLabel;
    return `范围 ${rangeLabel} / 待处理 ${log.candidates_total} / 成功 ${log.updated_count} / 失败 ${log.duplicate_count} / 跳过 ${log.filtered_count}`;
  }
  return `来源 ${JSON.stringify(log.source_counts)} / 候选 ${log.candidates_total} / 新增 ${log.inserted_count} / 更新 ${log.updated_count} / 过滤 ${log.filtered_count} / 去重 ${log.duplicate_count}`;
}

function LogsPage({ logs }) {
  const [filters, setFilters] = React.useState(() => loadUIState('privacy-radar-log-filters', {
    actionType: 'all',
    status: 'all',
    query: '',
  }));

  React.useEffect(() => {
    saveUIState('privacy-radar-log-filters', filters);
  }, [filters]);

  const filteredLogs = React.useMemo(() => {
    const keyword = filters.query.trim().toLowerCase();
    return logs.filter((log) => {
      if (filters.actionType !== 'all' && (log.action_type || 'fetch') !== filters.actionType) return false;
      if (filters.status !== 'all' && log.status !== filters.status) return false;
      if (!keyword) return true;
      const haystack = [
        log.message,
        formatLogSummary(log),
        ...(Array.isArray(log.failures) ? log.failures : []),
      ]
        .join(' ')
        .toLowerCase();
      return haystack.includes(keyword);
    });
  }, [filters, logs]);

  return (
    <section className="logs">
      <div className="toolstrip toolstripFilters logToolbar">
        <div className="filterStack">
          <div className="searchBox">
            <Search size={17} />
            <input
              value={filters.query}
              onChange={(event) => setFilters((current) => ({ ...current, query: event.target.value }))}
              placeholder="搜索日志消息或失败原因"
            />
          </div>
          <div className="filterRow">
            <select value={filters.actionType} onChange={(event) => setFilters((current) => ({ ...current, actionType: event.target.value }))}>
              <option value="all">全部动作</option>
              {Object.entries(LOG_ACTION_META).map(([key, label]) => (
                <option key={key} value={key}>{label}</option>
              ))}
            </select>
            <select value={filters.status} onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value }))}>
              <option value="all">全部状态</option>
              <option value="success">成功</option>
              <option value="partial">部分成功</option>
              <option value="failed">失败</option>
            </select>
          </div>
        </div>
        <div className="logMetrics">
          <span>当前 {filteredLogs.length} 条</span>
          <span>失败 {filteredLogs.filter((log) => log.status === 'failed').length} 条</span>
        </div>
      </div>
      {filteredLogs.map((log) => (
        <article className="logRow" key={log.id}>
          <div>
            <strong>{LOG_ACTION_META[log.action_type] || '\u6293\u53d6'} · {log.status}</strong>
            <span>{log.finished_at}</span>
          </div>
          <p>{log.message}</p>
          <code>{formatLogSummary(log)}</code>
          {log.failures?.length > 0 && (
            <details className="logFailures">
              <summary>失败详情（{log.failures.length}）</summary>
              <pre>{log.failures.join('\n')}</pre>
            </details>
          )}
        </article>
      ))}
      {!filteredLogs.length && <div className="empty">当前筛选条件下没有运行日志。</div>}
    </section>
  );
}

function Metric({ label, value }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);

