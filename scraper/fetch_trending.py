#!/usr/bin/env python3
"""
GitHub Trending scraper + humorous blog post generator.
No external LLM required — uses templates with humor injection.
"""
import json
import os
import re
import random
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ── config ───────────────────────────────────────────────────────
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "site" / "posts"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
TRENDING_URL = "https://github.com/trending"

# ── humor templates ──────────────────────────────────────────────

TITLE_TEMPLATES = [
    "🚀 今日 GitHub 热搜：{top_repo} 霸榜，开发者集体失眠",
    "🔥 GitHub 日报 {date}：今天的代码，明天的 bug",
    "📡 GitHub 雷达 {date}：{top_repo} 带着 {stars} 颗星杀过来了",
    "🍿 程序员今日吃瓜：{top_repo} 爆火，{language} 又双叒叕赢了",
    "🌍 GitHub 今日战报：谁在提交代码，谁在制造 issue",
    "🐼 GitHub 趋势速递 {date}：{count} 个项目今天值得你 star",
    "⚡️ GitHub 热搜榜 {date}：{top_repo} 让 {stars} 个开发者点了收藏",
    "🤖 AI 日报不能写？没事，GitHub 日报照常营业 | {date}",
]

INTROS = [
    "早上好，各位键盘侠。今天的 GitHub Trending 告诉我们：世界各地的开发者们依然在不睡觉地写代码。以下是今日战况 ⬇️",
    "又到了一天一度的「看看别人在卷什么」环节。准备好你的 star 键，Let's go 🚀",
    "每天打开 GitHub Trending 的瞬间，就像拆盲盒——你不知道会看到一个改变世界的项目，还是又一个「用 Rust 重写一切」的尝试。今日拆盒结果如下：",
    "众所周知，GitHub Trending 是程序员界的「今日头条」。今日头条播报开始 📢",
    "起床上班第一件事：打开电脑。第二件事：打开 GitHub Trending 看看又有多少大牛做出了你一年前的 TODO 项目 😭",
    "今日 GitHub 浓度检测完毕。以下是高浓度项目报告 ☕️",
    "警告：以下内容可能导致大量 star 行为、clone 冲动以及「我也能做」的幻觉。请谨慎阅读 ⚠️",
    "各位摸鱼选手请注意，今日 GitHub Trending 已更新。老板不在的时候看看正好 👀",
]

OUTROS = [
    "以上就是今天的 GitHub 热搜。去 star 吧，反正你的 repo 列表已经 3000+ 了，不在乎多几个。",
    "今天的播报就到这里。记得多喝水，少熬夜，代码跑得过初一跑不过十五。明天见 👋",
    "如果你觉得这些项目不够有趣，不妨自己造一个——然后你就会发现，GitHub Trending 上的项目背后都是无数个不眠之夜。🌙",
    "散会！今天又有 N 个新项目加入了你的「迟早会看」收藏夹。我懂的。",
    "下课！去给这些项目贡献 PR 吧——或者至少把 star 点了，给开发者一点心理安慰。",
]

REPO_JOKES = [
    lambda r: f"**{r['name']}** — {r['desc'][:80]}...  {r.get('stars_today', '?')} 人今天被这个项目征服。它的存在证明了：好代码不需要 README 写三页。",
    lambda r: f"**{r['name']}** 今天拿了 {r.get('stars_today', '?')} 颗星星，比某些人一辈子拿的赞还多 ⭐",
    lambda r: f"**{r['name']}** — {r.get('lang', 'Unknown')} 写的，当然好（不是）。{r['desc'][:60]}...  {r.get('stars_today', '?')} 人表示「先 star 为敬」。",
    lambda r: f"**{r['name']}** — 如果你还没 star，那你可能错过了今天的船票。{r.get('stars_today', '?')} 人已经上船了。",
    lambda r: f"**{r['name']}** — {r['desc'][:70]}... 翻译成人话就是：又一个「简单、快速、强大」的东西，而且这次可能是真的。",
    lambda r: f"**{r['name']}** — 用 {r.get('lang', '某种神秘语言')} 写就。今天获得了 {r.get('stars_today', '?')} 颗星，证明 {r.get('lang', '它')} 还活着且活得挺好。",
    lambda r: f"**{r['name']}** — {r['desc'][:60]}...  听起来像个周末项目，但它已经有 {r.get('total_stars', '?')} 总星了。周末项目，认真的吗？",
]

LANG_OBSERVATIONS = {
    "Rust": [
        "Rust 项目又上榜了。我就问一句：你们到底写了多少遍「用 Rust 重写」？ 🦀",
        "Rust 选手今天依然活跃。他们的信念是：能用 lifetime 解决的问题，绝不用 GC。",
    ],
    "Python": [
        "Python 再次上榜。简单、优雅，唯一的问题是缩进错了会爆炸 🐍",
        "Python 选手：pip install 一下，问题解决了一半。另一半是版本冲突。",
    ],
    "TypeScript": [
        "TypeScript 项目上榜。类型安全的快乐，只有写过 any 的人才能体会。",
        "TypeScript 又来了。记住：any 是毒药，never 是解药。",
    ],
    "JavaScript": [
        "JavaScript 项目今天也上榜了。`npm install` 之后你的 node_modules 又多了 800 个依赖。",
    ],
    "Go": [
        "Go 语言项目上榜。简洁、并发、没有泛型——等等，现在有了。",
    ],
    "C++": [
        "C++ 项目今天上榜。Segfault 是每个 C++ 程序员的成人礼。",
    ],
    "C": [
        "C 语言：50 年了，依然是操作系统和嵌入式的不二之选。致敬。",
    ],
}

# ── scraping ─────────────────────────────────────────────────────

def fetch_trending(proxies=None):
    """Fetch and parse GitHub Trending page."""
    r = requests.get(TRENDING_URL, headers=HEADERS, proxies=proxies, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    
    repos = []
    for article in soup.find_all("article", class_="Box-row"):
        repo = {}
        
        # Name + owner
        h2 = article.find("h2", class_="h3")
        if h2 and h2.find("a"):
            href = h2.find("a").get("href", "")
            repo["name"] = href.strip("/")
            repo["url"] = f"https://github.com{href}"
        
        # Description
        desc = article.find("p", class_="col-9")
        repo["desc"] = desc.text.strip() if desc else ""
        
        # Language
        lang = article.find("span", itemprop="programmingLanguage")
        repo["lang"] = lang.text.strip() if lang else "Unknown"
        
        # Stars today
        for span in article.find_all("span"):
            txt = span.text.strip()
            if "stars today" in txt:
                repo["stars_today"] = txt
        
        # Total stars + forks from links
        for a in article.find_all("a", class_="Link"):
            txt = a.text.strip()
            href = a.get("href", "")
            if "/stargazers" in href and txt:
                repo["total_stars"] = txt
            elif "/forks" in href and txt:
                repo["forks"] = txt
        
        repos.append(repo)
    
    return repos


# ── blog generation ──────────────────────────────────────────────

def generate_blog(repos, date_str):
    """Generate a humorous markdown blog post from trending repos."""
    lines = []
    
    top = repos[0] if repos else {"name": "某个神秘项目", "stars_today": "?"}
    top_name = top["name"].split("/")[-1] if "/" in top["name"] else top["name"]
    
    # Title
    title_tmpl = random.choice(TITLE_TEMPLATES)
    title = title_tmpl.format(
        top_repo=top_name,
        date=date_str,
        stars=top.get("stars_today", "?"),
        language=top.get("lang", "Unknown"),
        count=len(repos),
    )
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"> 📅 {date_str}  |  🔍 共收录 {len(repos)} 个热门项目")
    lines.append("")
    
    # Intro
    lines.append(random.choice(INTROS))
    lines.append("")
    
    # Stats overview
    lines.append("---")
    lines.append("")
    lines.append("## 📊 今日统计")
    lines.append("")
    
    langs = {}
    for r in repos:
        l = r.get("lang", "Unknown")
        langs[l] = langs.get(l, 0) + 1
    
    top_langs = sorted(langs.items(), key=lambda x: x[1], reverse=True)[:5]
    lang_line = " | ".join(f"**{l}**: {c}" for l, c in top_langs)
    lines.append(f"主力语言：{lang_line}")
    
    # Language observation
    if top_langs:
        top_lang = top_langs[0][0]
        if top_lang in LANG_OBSERVATIONS:
            lines.append("")
            lines.append(f"> {random.choice(LANG_OBSERVATIONS[top_lang])}")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Repo list
    lines.append("## 🔥 热门项目 Top 10")
    lines.append("")
    
    for i, repo in enumerate(repos[:10]):
        lines.append(f"### {i+1}. {repo['name']}")
        lines.append("")
        lines.append(random.choice(REPO_JOKES)(repo))
        lines.append("")
        
        # Stats row
        stats_parts = []
        if "stars_today" in repo:
            stats_parts.append(f"⭐ {repo['stars_today']}")
        if "total_stars" in repo:
            stats_parts.append(f"📦 总星 {repo['total_stars']}")
        if "forks" in repo:
            stats_parts.append(f"🍴 {repo['forks']}")
        if "lang" in repo:
            stats_parts.append(f"💻 {repo['lang']}")
        
        lines.append(" | ".join(stats_parts))
        lines.append(f"[🔗 查看项目]({repo['url']})")
        lines.append("")
    
    # Honorable mentions
    if len(repos) > 10:
        lines.append("---")
        lines.append("")
        lines.append("## 🫡 荣誉提名")
        lines.append("")
        for repo in repos[10:15]:
            name_short = repo["name"].split("/")[-1] if "/" in repo["name"] else repo["name"]
            lines.append(f"- **{repo['name']}** — {repo['desc'][:80]}{'...' if len(repo['desc']) > 80 else ''}  ⭐ {repo.get('stars_today', '?')}")
        lines.append("")
    
    # Outro
    lines.append("---")
    lines.append("")
    lines.append(random.choice(OUTROS))
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*🤖 本文由自动化脚本生成。幽默感如有冒犯，纯属巧合。数据来源：github.com/trending*")
    
    return "\n".join(lines)


# ── main ─────────────────────────────────────────────────────────

def main():
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    
    # Proxy support
    proxies = None
    http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
    https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if http_proxy or https_proxy:
        proxies = {"http": http_proxy, "https": https_proxy}
    
    print(f"🔍 Fetching GitHub Trending for {date_str}...")
    repos = fetch_trending(proxies=proxies)
    print(f"✅ Found {len(repos)} trending repos")
    
    # Generate blog
    blog = generate_blog(repos, date_str)
    
    # Save as JSON (raw data + rendered blog)
    output = {
        "date": date_str,
        "repos": repos,
        "blog_md": blog,
        "generated_at": now.isoformat(),
    }
    
    # Save daily file
    filepath = OUTPUT_DIR / f"{date_str}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    # Update index and generate static HTML
    update_index()
    generate_static_html()
    
    print(f"📝 Saved to {filepath}")
    
    # Print first few lines of blog as preview
    print("\n" + "=" * 60)
    print("📰 BLOG PREVIEW:")
    print("=" * 60)
    for line in blog.split("\n")[:15]:
        print(line)


def update_index():
    """Update posts index JSON for the frontend."""
    index_path = OUTPUT_DIR / "index.json"
    posts = []
    
    for f in sorted(OUTPUT_DIR.glob("????-??-??.json")):
        try:
            with open(f, "r") as fp:
                data = json.load(fp)
            posts.append({
                "date": data["date"],
                "count": len(data.get("repos", [])),
                "top_repo": data["repos"][0]["name"] if data.get("repos") else None,
                "top_stars": data["repos"][0].get("stars_today", "") if data.get("repos") else "",
            })
        except (json.JSONDecodeError, KeyError, IndexError):
            continue
    
    with open(index_path, "w") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)
    
    print(f"📋 Updated index: {len(posts)} posts")


def generate_static_html():
    """Generate static index.html and per-post HTML files."""
    import html as _html
    
    SITE_DIR = OUTPUT_DIR.parent
    INDEX_TEMPLATE = SITE_DIR / "index.html"
    
    # Collect all posts
    all_posts = []
    for f in sorted(OUTPUT_DIR.glob("????-??-??.json"), reverse=True):
        try:
            with open(f, "r") as fp:
                data = json.load(fp)
            all_posts.append(data)
        except (json.JSONDecodeError, KeyError):
            continue
    
    if not all_posts:
        return
    
    # Calculate stats
    post_count = len(all_posts)
    total_repos = sum(len(d.get("repos", [])) for d in all_posts)
    top_stars = ""
    for d in all_posts:
        if d.get("repos"):
            s = d["repos"][0].get("stars_today", "")
            if s and (not top_stars or _parse_star_num(s) > _parse_star_num(top_stars)):
                top_stars = s
    
    # Build post cards
    cards = []
    for d in all_posts:
        date = d["date"]
        date_display = _format_date_cn(date)
        top = d["repos"][0] if d.get("repos") else {}
        top_name = top.get("name", "")
        top_short = top_name.split("/")[-1] if "/" in top_name else top_name
        stars = top.get("stars_today", "")
        count = len(d.get("repos", []))
        
        cards.append(
            f'<a href="posts/{date}.html" class="post-card">'
            f'<div class="post-card-left">'
            f'<span class="post-card-date">{_html.escape(date_display)}</span>'
            f'<span class="post-card-meta"><span>📦 {count} 个项目</span></span>'
            f'</div>'
            f'<div class="post-card-right">'
            f'<span class="post-card-repo">{_html.escape(top_short) if top_short else "—"}</span>'
            f'<span class="post-card-stars">{stars}</span>'
            f'</div>'
            f'</a>'
        )
    
    # Read template and fill
    with open(INDEX_TEMPLATE, "r") as f:
        html = f.read()
    
    html = html.replace("{{post_count}}", str(post_count))
    html = html.replace("{{total_repos}}", str(total_repos))
    html = html.replace("{{top_stars}}", top_stars or "—")
    html = html.replace("{{post_cards}}", "\n    ".join(cards))
    
    with open(INDEX_TEMPLATE, "w") as f:
        f.write(html)
    
    print(f"🌐 Generated index.html with {post_count} post cards")
    
    # Generate per-post HTML pages
    for d in all_posts:
        _generate_post_html(d)


def _generate_post_html(data):
    """Generate a standalone HTML page for a single blog post."""
    import html as _html
    
    SITE_DIR = OUTPUT_DIR.parent
    date = data["date"]
    date_display = _format_date_cn(date)
    blog_md = data.get("blog_md", "")
    
    # Simple markdown-to-HTML conversion (no external lib needed)
    blog_html = _md_to_html(blog_md)
    
    page = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GitHub 日报 {date} — GH Trend Digest</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../css/style.css">
</head>
<body>

<nav class="nav">
  <div class="nav-inner">
    <a href="../" class="logo">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="11" stroke="currentColor" stroke-width="2"/>
        <path d="M8 12h8M12 8v8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      </svg>
      <span>GH Trend Digest</span>
    </a>
    <a href="../" class="nav-link">← 返回首页</a>
  </div>
</nav>

<main class="content" style="padding-top:32px;">
  <a href="../" class="btn-back">← 返回列表</a>
  <div class="detail-date" style="margin-top:16px;">📅 {_html.escape(date_display)}</div>
  <div class="detail-content" style="margin-top:24px;">
    {blog_html}
  </div>
</main>

<p style="text-align:center;color:var(--text-quaternary);font-size:13px;padding:48px 24px;">
  🤖 自动生成 · 数据来源 <a href="https://github.com/trending">GitHub Trending</a>
</p>

</body>
</html>'''
    
    post_path = OUTPUT_DIR / f"{date}.html"
    with open(post_path, "w") as f:
        f.write(page)


def _md_to_html(md: str) -> str:
    """Minimal markdown-to-HTML converter. Handles the common patterns our blog uses."""
    import html as _html
    import re
    
    lines = md.split("\n")
    out = []
    in_hr = False
    
    for line in lines:
        # Horizontal rule
        if line.strip() == "---":
            out.append("<hr>")
            continue
        
        # Headings
        if line.startswith("### "):
            out.append(f"<h3>{_html.escape(line[4:])}</h3>")
            continue
        if line.startswith("## "):
            out.append(f"<h2>{_html.escape(line[3:])}</h2>")
            continue
        if line.startswith("# "):
            out.append(f"<h1>{_html.escape(line[2:])}</h1>")
            continue
        
        # Blockquote
        if line.startswith("> "):
            out.append(f"<blockquote>{_format_inline(line[2:])}</blockquote>")
            continue
        
        # Empty line
        if not line.strip():
            out.append("")
            continue
        
        # Regular paragraph
        out.append(f"<p>{_format_inline(line)}</p>")
    
    return "\n".join(out)


def _format_inline(text: str) -> str:
    """Format inline markdown: bold, italic, code, links, emoji."""
    import html as _html
    import re
    
    t = _html.escape(text)
    
    # Inline code: `code`
    t = re.sub(r"`([^`]+)`", r'<code>\1</code>', t)
    
    # Bold: **text**
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
    
    # Italic: *text* (but not **)
    t = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', t)
    
    # Links: [text](url)
    t = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', t)
    
    # Images: ![alt](url)
    t = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1">', t)
    
    return t


def _parse_star_num(s: str) -> int:
    """Parse '2,123 stars today' -> 2123"""
    import re
    m = re.search(r'[\d,]+', s)
    if m:
        return int(m.group().replace(",", ""))
    return 0


def _format_date_cn(date_str: str) -> str:
    """Format YYYY-MM-DD to Chinese date string."""
    from datetime import datetime
    d = datetime.strptime(date_str, "%Y-%m-%d")
    weekdays = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]
    wd = weekdays[d.weekday()]
    return f"{d.year}年{d.month:02d}月{d.day:02d}日 {wd}"


if __name__ == "__main__":
    main()
