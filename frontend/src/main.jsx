import React from 'react';
import { createRoot } from 'react-dom/client';
import {
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

async function api(path, options) {
  const response = await fetch(`${API_BASE}${path}`, options);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `HTTP ${response.status}`);
  }
  return response.json();
}

function App() {
  const [page, setPage] = React.useState('today');
  const [articles, setArticles] = React.useState([]);
  const [logs, setLogs] = React.useState([]);
  const [config, setConfig] = React.useState(null);
  const [detail, setDetail] = React.useState(null);
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
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(false);
    }
  };

  const refresh = async () => {
    setBusy(true);
    try {
      if (page === 'logs') await loadLogs();
      else if (page === 'config') await loadConfig();
      else await loadArticles();
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(false);
    }
  };

  const openDetail = async (article) => {
    setDetail(await api(`/api/articles/${article.id}`));
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
              <button key={key} className={page === key ? 'nav active' : 'nav'} onClick={() => { setPage(key); setDetail(null); }}>
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
            <h1>{PAGE_META[page].label}</h1>
          </div>
          <div className="actions">
            <label className="iconButton" title="上传腾讯文档 CSV 去重">
              <FileUp size={18} />
              <input type="file" accept=".csv,.txt,.md" onChange={uploadSeen} />
            </label>
            <button className="iconButton" onClick={refresh} title="刷新">
              <RotateCcw size={18} />
            </button>
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
        {page === 'config' && <ConfigPage config={config} saveConfig={saveConfig} />}
        {page === 'logs' && <LogsPage logs={logs} />}
      </section>

      <DetailPanel article={detail} changeStatus={changeStatus} close={() => setDetail(null)} />
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
  return (
    <article className="articleRow" onClick={() => openDetail(article)}>
      <div className="score">{article.score}</div>
      <div className="articleMain">
        <h2>{article.title}</h2>
        <div className="metaLine">
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

function DetailPanel({ article, changeStatus, close }) {
  if (!article) {
    return (
      <aside className="detailPanel mutedPanel">
        <ShieldCheck size={30} />
        <p>选择一篇文章查看摘要、作者、评分和推荐理由。</p>
      </aside>
    );
  }
  return (
    <aside className="detailPanel">
      <button className="closeButton" onClick={close}>关闭</button>
      <div className="detailScore">{article.score}</div>
      <h2>{article.title}</h2>
      <div className="detailMeta">
        <span>{article.source}</span>
        <span>{article.published || '无日期'}</span>
        <span>{STATUS_META[article.status]?.label}</span>
      </div>
      <StatusButtons article={article} changeStatus={changeStatus} />
      <section>
        <h3>摘要</h3>
        <p>{article.summary || '暂无摘要。'}</p>
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
    </aside>
  );
}

function ConfigPage({ config, saveConfig }) {
  const [draft, setDraft] = React.useState('');
  React.useEffect(() => {
    if (config) setDraft(JSON.stringify(config, null, 2));
  }, [config]);
  const submit = () => {
    saveConfig(JSON.parse(draft));
  };
  return (
    <section className="configPanel">
      <textarea value={draft} onChange={(event) => setDraft(event.target.value)} spellCheck="false" />
      <div className="configActions">
        <button className="primary" onClick={submit}>
          <Settings2 size={18} />
          保存配置
        </button>
      </div>
    </section>
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
