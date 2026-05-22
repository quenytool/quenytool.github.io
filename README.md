# 🚀 GitHub Trend Digest

> 每天从 GitHub Trending 抓取热门项目，用幽默的风格解读技术趋势。

## 工作原理

```
GitHub Trending → Python 爬虫 → 幽默博客生成 → GitHub Pages 静态网站
     ↕                   ↕                  ↕
  每日自动抓取        模板+随机段子        纯静态，秒开
```

### 自动化流程

- **每日 00:30 UTC** — GitHub Actions 自动抓取 GitHub Trending
- **Python 脚本** — 解析页面数据，生成幽默风格 Markdown 博客
- **自动部署** — 提交 JSON 数据，部署到 GitHub Pages
- **静态网站** — 纯 HTML/CSS/JS，加载本地 JSON，零后端

## 项目结构

```
gh-trending-blog/
├── scraper/
│   └── fetch_trending.py     # 爬虫 + 博客生成器
├── site/
│   ├── index.html            # 静态网站主页
│   ├── css/style.css         # 样式 (Linear 风格暗色主题)
│   ├── js/main.js            # 前端逻辑
│   └── posts/                # 每日数据 (自动生成)
│       ├── index.json        # 文章索引
│       └── YYYY-MM-DD.json   # 单日数据
├── .github/workflows/
│   └── deploy.yml            # CI/CD 自动部署
└── README.md
```

## 本地运行

```bash
# 1. 安装依赖
pip install requests beautifulsoup4

# 2. 手动抓取一次
python scraper/fetch_trending.py

# 3. 本地预览网站
cd site && python -m http.server 8080
# 打开 http://localhost:8080
```

## 部署到 GitHub Pages

1. Fork 这个仓库
2. 在 Settings → Pages 中启用 GitHub Pages (Source: GitHub Actions)
3. 等待每日自动运行，或手动触发 Actions

## License

MIT
