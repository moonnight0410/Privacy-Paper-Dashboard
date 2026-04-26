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
  ListFilter,
  Loader2,
  Play,
  RotateCcw,
  Search,
  Settings2,
  ShieldCheck,
  Sparkles,
  XCircle,
} from 'lucide-react';
import './styles.css';

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8000';

const STATUS_META = {
  candidate: { label: '候选', icon: ListFilter },
  reading: { label: '待读', icon: Clock3 },
  selected: { label: '入选', icon: CheckCircle2 },
  shared: { label: '已分享', icon: BookOpenCheck },
  rejected: { label: '驳回', icon: XCircle },
};

const PAGE_META = {
  today: { label: '今日候选', icon: ListFilter },
  selected: { label: '已选文章', icon: CheckCircle2 },
  history: { label: '历史库', icon: Archive },
  config: { label: '来源/关键词配置', icon: Settings2 },
  logs: { label: '运行日志', icon: History },
};

const SOURCE_TYPE_META = {
  international_academic: { label: '国际学术', tone: 'academic' },
  domestic_authority: { label: '国内权威', tone: 'authority' },
  wechat_authority: { label: '公众号', tone: 'wechat' },
  search: { label: '搜索来源', tone: 'search' },
};

const AI_PROVIDERS = {
  other: { label: '其他供应商 / OpenAI-compatible', baseUrl: '', model: '' },
  custom: { label: '自定义 OpenAI-compatible', baseUrl: '', model: '' },
  deepseek: { label: 'DeepSeek', baseUrl: 'https://api.deepseek.com', model: 'deepseek-chat' },
  qwen: { label: '通义千问 / 阿里百炼', baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1', model: 'qwen-plus' },
  glm: { label: 'GLM / 智谱', baseUrl: 'https://open.bigmodel.cn/api/paas/v4', model: 'glm-4-flash' },
  doubao: { label: '豆包 / 火山方舟', baseUrl: 'https://ark.cn-beijing.volces.com/api/v3', model: '' },
};

const DEFAULT_AI_CONFIG = {
  provider: 'deepseek',
  base_url: AI_PROVIDERS.deepseek.baseUrl,
  model: AI_PROVIDERS.deepseek.model,
  api_key: '',
  max_input_chars: 6000,
};

const TRANSLATION_PROVIDERS = {
  baidu: { label: '百度翻译', baseUrl: 'https://fanyi-api.baidu.com/api/trans/vip/translate' },
  libretranslate: { label: 'LibreTranslate 兼容接口', baseUrl: 'https://libretranslate.com/translate' },
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

function getSourceBadges(article) {
  const sourceType = SOURCE_TYPE_META[article.source_type] ?? { label: article.source_type || '其他来源', tone: 'other' };
  const haystack = `${article.source || ''} ${article.url || ''}`.toLowerCase();
  let venue = { label: '其他', tone: 'other' };
  if (article.source_type === 'wechat_authority' || haystack.includes('mp.weixin.qq.com')) {
    venue = { label: '公众号', tone: 'wechat' };
  } else if (TOP_VENUES.some((name) => haystack.includes(name))) {
    venue = { label: '顶会', tone: 'conference' };
  } else if (JOURNAL_VENUES.some((name) => haystack.includes(name))) {
    venue = { label: '期刊', tone: 'journal' };
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

function App() {
  const [page, setPage] = React.useState('today');
  const [articles, setArticles] = React.useState([]);
  const [logs, setLogs] = React.useState([]);
  const [config, setConfig] = React.useState(null);
  const [aiConfig, setAIConfig] = React.useState(loadAIConfig);
  const [translationConfig, setTranslationConfig] = React.useState(loadTranslationConfig);
  const [detail, setDetail] = React.useState(null);
  const [previousPage, setPreviousPage] = React.useState('today');
  const [query, setQuery] = React.useState('');
  const [busy, setBusy] = React.useState(false);
  const [notice, setNotice] = React.useState('');

  const statusForPage = React.useMemo(() => {
    if (page === 'today') return 'candidate';
    if (page === 'selected') return 'selected';
    return null;
  }, [page]);

  const loadArticles = React.useCallback(async () => {
    const params = new URLSearchParams();
    if (statusForPage) params.set('status', statusForPage);
    if (query.trim()) params.set('q', query.trim());
    const data = await api(`/api/articles?${params.toString()}`);
    setArticles(data);
  }, [query, statusForPage]);

  const loadLogs = React.useCallback(async () => {
    setLogs(await api('/api/logs'));
  }, []);

  const loadConfig = React.useCallback(async () => {
    setConfig(await api('/api/config'));
  }, []);

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
      setPage('today');
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

  const runAIEnrich = async () => {
    if (!hasEnrichmentConfig(aiConfig, translationConfig)) {
      setNotice('请先在“来源/关键词配置”里填写 AI 配置，或启用并填写机器翻译配置。');
      return;
    }
    const batchStatus = page === 'today' ? 'candidate' : page === 'selected' ? 'selected' : 'all';
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
        body: JSON.stringify({ ai: aiConfig, translation: translationConfig, status: batchStatus, limit: 200 }),
      });
      setNotice(`AI 补齐完成：待处理 ${result.stats.total} 条，成功 ${result.stats.processed} 条，失败 ${result.stats.failed} 条。`);
      await loadArticles();
    } catch (error) {
      setNotice(`AI 生成失败：${error.message}`);
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
          {Object.entries(PAGE_META).map(([key, item]) => {
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
            <h1>{page === 'detail' ? '论文详情' : PAGE_META[page].label}</h1>
          </div>
          <div className="actions">
            <label className="iconButton" title="上传腾讯文档 CSV 去重">
              <FileUp size={18} />
              <input type="file" accept=".csv,.txt,.md" onChange={uploadSeen} />
            </label>
            <button className="iconButton" onClick={refresh} title="刷新">
              <RotateCcw size={18} />
            </button>
            {(page === 'today' || page === 'selected' || page === 'history' || page === 'detail') && (
              <button className="secondary" onClick={runAIEnrich} disabled={busy || (page === 'detail' && !detail)}>
                {busy ? <Loader2 className="spin" size={18} /> : <Sparkles size={18} />}
                补齐标题/摘要翻译
              </button>
            )}
            <button className="primary" onClick={runFetch} disabled={busy}>
              {busy ? <Loader2 className="spin" size={18} /> : <Play size={18} />}
              抓取今日候选
            </button>
          </div>
        </header>

        {notice && <div className="notice">{notice}</div>}

        {(page === 'today' || page === 'selected' || page === 'history') && (
          <ArticlePage
            page={page}
            articles={articles}
            query={query}
            setQuery={setQuery}
            openDetail={openDetail}
            changeStatus={changeStatus}
            exportMarkdown={exportMarkdown}
          />
        )}
        {page === 'detail' && (
          <DetailPage article={detail} changeStatus={changeStatus} close={closeDetail} />
        )}
        {page === 'config' && (
          <ConfigPage
            config={config}
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

function ArticlePage({ page, articles, query, setQuery, openDetail, changeStatus, exportMarkdown }) {
  const [markShared, setMarkShared] = React.useState(true);
  const stats = React.useMemo(() => {
    const total = articles.length;
    const average = total ? Math.round(articles.reduce((sum, item) => sum + item.score, 0) / total) : 0;
    const selected = articles.filter((item) => item.status === 'selected').length;
    return { total, average, selected };
  }, [articles]);

  return (
    <div className="contentGrid">
      <section className="listPanel">
        <div className="toolstrip">
          <div className="searchBox">
            <Search size={17} />
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索标题、摘要或来源" />
          </div>
          {page === 'selected' && (
            <div className="exportBox">
              <label>
                <input type="checkbox" checked={markShared} onChange={(event) => setMarkShared(event.target.checked)} />
                导出后标记已分享
              </label>
              <button className="secondary" onClick={() => exportMarkdown(markShared)}>
                <Download size={17} />
                导出 Markdown
              </button>
            </div>
          )}
        </div>
        <div className="articleList">
          {articles.map((article) => (
            <ArticleRow key={article.id} article={article} openDetail={openDetail} changeStatus={changeStatus} />
          ))}
          {!articles.length && <div className="empty">暂无条目。可以先抓取今日候选，或调整筛选条件。</div>}
        </div>
      </section>
      <aside className="metrics">
        <Metric label="当前条目" value={stats.total} />
        <Metric label="平均评分" value={stats.average} />
        <Metric label="入选数量" value={stats.selected} />
        <div className="statusLegend">
          {Object.entries(STATUS_META).map(([key, item]) => {
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

function ArticleRow({ article, openDetail, changeStatus }) {
  const StatusIcon = STATUS_META[article.status]?.icon ?? ListFilter;
  const badges = getSourceBadges(article);
  const translatedTitle = article.translated_title?.trim();
  return (
    <article className="articleRow" onClick={() => openDetail(article)}>
      <div className="score">{article.score}</div>
      <div className="articleMain">
        <h2>{translatedTitle || article.title}</h2>
        {translatedTitle && <p className="originalTitle">{article.title}</p>}
        <div className="metaLine">
          <span className={`sourceBadge ${badges.sourceType.tone}`}>{badges.sourceType.label}</span>
          <span className={`venueBadge ${badges.venue.tone}`}>{badges.venue.label}</span>
          <span>{article.source || '未知来源'}</span>
          <span>{article.published || '无日期'}</span>
          <span className={`status ${article.status}`}>
            <StatusIcon size={14} />
            {STATUS_META[article.status]?.label}
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
      {Object.entries(STATUS_META).map(([status, item]) => {
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
  const translatedTitle = article.translated_title?.trim();
  return (
    <section className="detailPage">
      <button className="secondary backButton" onClick={close}>
        <ArrowLeft size={18} />
        返回列表
      </button>
      <div className="detailScore">{article.score}</div>
      <h2>{translatedTitle || article.title}</h2>
      {translatedTitle && <p className="originalTitle detailOriginalTitle">{article.title}</p>}
      <div className="detailMeta">
        <span className={`sourceBadge ${badges.sourceType.tone}`}>{badges.sourceType.label}</span>
        <span className={`venueBadge ${badges.venue.tone}`}>{badges.venue.label}</span>
        <span>{article.source}</span>
        <span>{article.published || '无日期'}</span>
        <span>{STATUS_META[article.status]?.label}</span>
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
        <h3>AI 推荐理由</h3>
        {(article.ai_recommendation || []).length > 0 ? (
          <ul>
            {article.ai_recommendation.map((reason) => <li key={reason}>{reason}</li>)}
          </ul>
        ) : (
          <p>暂未生成 AI 推荐理由。</p>
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
  return next;
}

function sourceName(source) {
  return source?.full_name || '';
}

function sourceLabel(source) {
  const alias = source?.alias?.trim();
  const fullName = sourceName(source);
  return alias && alias !== fullName ? `${alias} · ${fullName}` : fullName;
}

function ConfigPage({ config, saveConfig, aiConfig, setAIConfig, translationConfig, setTranslationConfig }) {
  const [draft, setDraft] = React.useState('');
  const [sourceQuery, setSourceQuery] = React.useState('');
  const [showKey, setShowKey] = React.useState(false);
  const [showTranslationSecret, setShowTranslationSecret] = React.useState(false);
  React.useEffect(() => {
    if (config) setDraft(JSON.stringify(config, null, 2));
  }, [config]);
  const parsedDraft = React.useMemo(() => {
    try {
      return JSON.parse(draft || '{}');
    } catch {
      return null;
    }
  }, [draft]);
  const referenceSources = parsedDraft?.reference_sources || config?.reference_sources || [];
  const selectedSourceNames = React.useMemo(() => {
    const configured = parsedDraft?.enabled_reference_sources;
    if (Array.isArray(configured)) {
      return new Set(configured);
    }
    return new Set(referenceSources.map(sourceName).filter(Boolean));
  }, [parsedDraft, referenceSources]);
  const filteredSources = React.useMemo(() => {
    const keyword = sourceQuery.trim().toLowerCase();
    if (!keyword) return referenceSources;
    return referenceSources.filter((source) => {
      const text = `${source.category || ''} ${source.tier || ''} ${source.full_name || ''} ${source.alias || ''}`.toLowerCase();
      return text.includes(keyword);
    });
  }, [referenceSources, sourceQuery]);
  const selectedCount = referenceSources.filter((source) => selectedSourceNames.has(sourceName(source))).length;
  const updateDraftConfig = (updater) => {
    if (!parsedDraft) return;
    const next = updater(parsedDraft);
    setDraft(JSON.stringify(next, null, 2));
  };
  const setSourceSelection = (fullName, checked) => {
    updateDraftConfig((current) => {
      const currentSources = current.reference_sources || referenceSources;
      const selected = new Set(
        Array.isArray(current.enabled_reference_sources)
          ? current.enabled_reference_sources
          : currentSources.map(sourceName).filter(Boolean),
      );
      if (checked) selected.add(fullName);
      else selected.delete(fullName);
      return { ...current, enabled_reference_sources: currentSources.map(sourceName).filter((name) => selected.has(name)) };
    });
  };
  const setFilteredSources = (checked) => {
    updateDraftConfig((current) => {
      const currentSources = current.reference_sources || referenceSources;
      const selected = new Set(
        Array.isArray(current.enabled_reference_sources)
          ? current.enabled_reference_sources
          : currentSources.map(sourceName).filter(Boolean),
      );
      filteredSources.map(sourceName).filter(Boolean).forEach((name) => {
        if (checked) selected.add(name);
        else selected.delete(name);
      });
      return { ...current, enabled_reference_sources: currentSources.map(sourceName).filter((name) => selected.has(name)) };
    });
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
    saveConfig(runtimeConfigToPersisted(JSON.parse(draft)));
  };
  return (
    <div className="settingsStack">
      <section className="aiPanel">
        <div className="panelTitle">
          <h2>抓取期刊/会议来源</h2>
          <span>{selectedCount} / {referenceSources.length} 已选择</span>
        </div>
        <div className="sourceToolbar">
          <div className="searchBox sourceSearch">
            <Search size={17} />
            <input value={sourceQuery} onChange={(event) => setSourceQuery(event.target.value)} placeholder="搜索期刊、会议、简称或梯队" />
          </div>
          <button className="secondary" onClick={() => setFilteredSources(true)} disabled={!parsedDraft || !filteredSources.length}>全选当前</button>
          <button className="secondary" onClick={() => setFilteredSources(false)} disabled={!parsedDraft || !filteredSources.length}>清空当前</button>
        </div>
        <div className="sourceList">
          {filteredSources.map((source) => {
            const fullName = sourceName(source);
            return (
              <label className="sourceItem" key={fullName}>
                <input
                  type="checkbox"
                  checked={selectedSourceNames.has(fullName)}
                  onChange={(event) => setSourceSelection(fullName, event.target.checked)}
                  disabled={!parsedDraft}
                />
                <span>
                  <strong>{sourceLabel(source)}</strong>
                  <small>{[source.category, source.tier].filter(Boolean).join(' / ')}</small>
                </span>
              </label>
            );
          })}
          {!filteredSources.length && <div className="empty inlineEmpty">没有匹配的来源。</div>}
        </div>
      </section>
      <section className="aiPanel">
        <div className="panelTitle">
          <h2>AI 摘要与推荐</h2>
          <span>API Key 仅保存在浏览器 localStorage，不写入后端。</span>
        </div>
        <div className="aiGrid">
          <label>
            <span>供应商</span>
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
            <input value={aiConfig.model} onChange={(event) => updateAIConfig({ model: event.target.value })} placeholder="例如 deepseek-chat / qwen-plus" />
          </label>
          <label>
            <span>API Key</span>
            <div className="keyInput">
              <input
                type={showKey ? 'text' : 'password'}
                value={aiConfig.api_key}
                onChange={(event) => updateAIConfig({ api_key: event.target.value })}
                placeholder="仅保存在当前浏览器"
              />
              <button className="secondary" onClick={() => setShowKey((value) => !value)}>{showKey ? '隐藏' : '显示'}</button>
            </div>
          </label>
        </div>
      </section>
      <section className="aiPanel">
        <div className="panelTitle">
          <h2>机器翻译摘要</h2>
          <span>启用后标题和摘要走翻译 API；AI 只负责推荐理由，可不填写 AI 配置。</span>
        </div>
        <div className="aiGrid">
          <label className="toggleLabel">
            <span>启用机器翻译</span>
            <input
              type="checkbox"
              checked={translationConfig.enabled}
              onChange={(event) => updateTranslationConfig({ enabled: event.target.checked })}
            />
          </label>
          <label>
            <span>翻译供应商</span>
            <select value={translationConfig.provider} onChange={(event) => changeTranslationProvider(event.target.value)}>
              {Object.entries(TRANSLATION_PROVIDERS).map(([key, provider]) => (
                <option key={key} value={key}>{provider.label}</option>
              ))}
            </select>
          </label>
          <label>
            <span>接口地址</span>
            <input value={translationConfig.base_url} onChange={(event) => updateTranslationConfig({ base_url: event.target.value })} />
          </label>
          <label>
            <span>源语言 / 目标语言</span>
            <div className="inlineInputs">
              <input value={translationConfig.source_lang} onChange={(event) => updateTranslationConfig({ source_lang: event.target.value })} />
              <input value={translationConfig.target_lang} onChange={(event) => updateTranslationConfig({ target_lang: event.target.value })} />
            </div>
          </label>
          {translationConfig.provider === 'baidu' ? (
            <>
              <label>
                <span>百度 App ID</span>
                <input value={translationConfig.app_id} onChange={(event) => updateTranslationConfig({ app_id: event.target.value })} />
              </label>
              <label>
                <span>百度密钥</span>
                <div className="keyInput">
                  <input
                    type={showTranslationSecret ? 'text' : 'password'}
                    value={translationConfig.secret_key}
                    onChange={(event) => updateTranslationConfig({ secret_key: event.target.value })}
                    placeholder="仅保存在当前浏览器"
                  />
                  <button className="secondary" onClick={() => setShowTranslationSecret((value) => !value)}>{showTranslationSecret ? '隐藏' : '显示'}</button>
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
                placeholder="可选，仅保存在当前浏览器"
              />
            </label>
          )}
        </div>
      </section>
      <section className="configPanel">
        <textarea value={draft} onChange={(event) => setDraft(event.target.value)} spellCheck="false" />
        <div className="configActions">
          <button className="primary" onClick={submit}>
            <Settings2 size={18} />
            保存配置
          </button>
        </div>
      </section>
    </div>
  );
}

function LogsPage({ logs }) {
  return (
    <section className="logs">
      {logs.map((log) => (
        <article className="logRow" key={log.id}>
          <div>
            <strong>{log.status}</strong>
            <span>{log.finished_at}</span>
          </div>
          <p>{log.message}</p>
          <code>
            来源 {JSON.stringify(log.source_counts)} / 候选 {log.candidates_total} / 新增 {log.inserted_count} / 更新 {log.updated_count} / 过滤 {log.filtered_count} / 去重 {log.duplicate_count}
          </code>
          {log.failures?.length > 0 && <pre>{log.failures.join('\n')}</pre>}
        </article>
      ))}
      {!logs.length && <div className="empty">暂无运行日志。</div>}
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
