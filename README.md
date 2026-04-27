# Privacy Paper Dashboard

数据安全与隐私保护论文/文章可视化筛选系统。项目将原来的每日命令行筛选脚本重构为本机运行的 FastAPI + SQLite + React 工作台，用于抓取候选、筛选状态、去重、查看详情、上传腾讯文档 CSV 去重库，并导出可分享的 Markdown。

## 功能概览

- 手动触发抓取今日候选，不做自动定时任务。
- 数据来源包括 arXiv、IACR ePrint、Crossref、Bing RSS。
- 支持配置国内权威官网和微信公众号搜索关键词。
- 条目状态支持：候选、待读、入选、已分享、驳回。
- 详情页展示标题、摘要、作者、来源、发布时间、评分、推荐理由和原始链接。
- SQLite 持久化历史库，按规范化标题、规范化链接和近似标题去重。
- 上传腾讯文档导出的 CSV/Markdown/文本文件，写入去重库。
- 导出当前“入选”条目的 Markdown，并可同时标记为“已分享”。
- 运行日志记录每次抓取的来源数量、过滤数量、去重数量和失败原因。

## 项目结构

```text
backend/      FastAPI 后端服务
frontend/     React + Vite 前端工作台
data/         SQLite 数据库目录
scripts/      预留脚本目录
sources.json  来源、关键词和权威会议/期刊配置
start.bat     Windows 一键启动入口
```

## 一键启动

在 Windows 上双击 `start.bat`，或在项目根目录运行：

```powershell
.\start.bat
```

脚本会自动：

- 创建 `.venv` 后端虚拟环境。
- 安装 `backend/requirements.txt`。
- 安装 `frontend/package.json` 依赖。
- 构建前端静态资源。
- 启动 FastAPI：`http://127.0.0.1:8000`
- 打开浏览器访问工作台。

## 手动启动

后端：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

前端构建：

```powershell
cd frontend
npm install
npm run build
```

## 使用流程

1. 打开工作台：`http://127.0.0.1:8000/`。
2. 点击“抓取今日候选”，系统会调用后端抓取各来源并写入 SQLite。
3. 在“今日候选”中查看评分、来源、日期和推荐理由。
4. 点击条目查看详情，使用按钮切换候选、待读、入选、已分享或驳回。
5. 在“已选文章”中导出 Markdown。

## 腾讯文档 CSV 上传去重

腾讯文档网页通常不能作为稳定公开数据源读取。推荐做法：

1. 在腾讯文档中导出 CSV，或复制表格内容保存为 `.csv` / `.txt` / `.md`。
2. 在前端右上角点击上传按钮。
3. 系统会解析标题和链接，写入 `shared_history` 去重库。
4. 后续抓取不会重复展示这些已分享条目。

## Markdown 导出

进入“已选文章”页面后点击“导出 Markdown”。可以勾选“导出后标记已分享”，系统会：

- 下载当前入选条目的 Markdown 文件。
- 将这些条目状态改为“已分享”。
- 写入本地去重库，后续抓取自动排除。

## 配置来源和关键词

在“来源/关键词配置”页面可以直接编辑 `sources.json` 对应的 JSON：

- `keywords`：领域关键词。
- `hot_terms`：热点加分词。
- `exclude_terms`：过滤词。
- `authority_venues`：权威会议、期刊和机构名。
- `bing_queries`：国内权威官网、微信公众号或学术站点搜索入口。

> [!NOTE]
> Bing RSS 的 `site:` 查询会被后端二次校验域名，避免搜索结果被无关站点污染。

## GitHub 仓库

目标仓库名：`privacy-paper-dashboard`

目标可见性：Public

可使用 GitHub CLI 创建并推送：

```powershell
git init
git add .
git commit -m "Initial privacy paper dashboard"
gh repo create privacy-paper-dashboard --public --source . --remote origin --push
```
