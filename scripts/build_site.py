#!/usr/bin/env python3
"""
data/papers.json から静的サイト（docs/index.html）を生成する。
外部テンプレートエンジンには依存せず、標準ライブラリのみで組み立てる。
"""
import html
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAPERS_PATH = ROOT / "data" / "papers.json"
DOCS_DIR = ROOT / "docs"

# 更新ボタンから飛ばすGitHub Actionsの実行ページ（手動実行はGitHubへのログイン・書き込み権限が必要なため、
# サイト上のボタンからは誰でも直接実行できない設計にしている）
WORKFLOW_URL = "https://github.com/tnokats0416/pediatric-gi-report/actions/workflows/update.yml"

# first_seenからこの日数以内はNEWバッジを表示する
NEW_BADGE_DAYS = 7

PAGE_TEMPLATE = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>小児消化器 論文まとめ</title>
<style>
  :root {{
    color-scheme: light dark;
    --bg: #ffffff;
    --fg: #1a1a1a;
    --muted: #6b6b6b;
    --border: #e3e3e3;
    --accent: #0a6b5c;
    --sec-background: #2b6cb0;
    --sec-method: #6b46c1;
    --sec-result: #b7791f;
    --sec-implication: #0a6b5c;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #14181a;
      --fg: #eaeaea;
      --muted: #9a9a9a;
      --border: #2c3234;
      --accent: #4fd1b8;
      --sec-background: #63b3ed;
      --sec-method: #b794f4;
      --sec-result: #f6ad55;
      --sec-implication: #4fd1b8;
    }}
  }}
  body {{
    background: var(--bg);
    color: var(--fg);
    font-family: -apple-system, "Hiragino Sans", "Yu Gothic", sans-serif;
    max-width: 780px;
    margin: 0 auto;
    padding: 2rem 1.25rem 4rem;
    line-height: 1.7;
  }}
  header {{ margin-bottom: 2rem; }}
  h1 {{ font-size: 1.4rem; margin-bottom: 0.25rem; }}
  .updated {{ color: var(--muted); font-size: 0.85rem; }}
  .disclaimer {{
    font-size: 0.8rem;
    color: var(--muted);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.75rem 1rem;
    margin-top: 1rem;
  }}
  .toolbar {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.6rem;
    margin-top: 1rem;
  }}
  .btn {{
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    font-size: 0.8rem;
    font-family: inherit;
    color: var(--fg);
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 0.35rem 0.8rem;
    cursor: pointer;
    text-decoration: none;
  }}
  .btn:hover {{ border-color: var(--accent); color: var(--accent); }}
  .btn[aria-pressed="true"] {{
    background: var(--accent);
    border-color: var(--accent);
    color: var(--bg);
  }}
  .bookmark-count-label {{ font-size: 0.78rem; color: var(--muted); }}
  article {{
    border-bottom: 1px solid var(--border);
    padding: 1.25rem 0;
    position: relative;
  }}
  article h2 {{
    font-size: 1.05rem;
    margin: 0 0 0.4rem;
    padding-right: 2.2rem;
  }}
  .new-badge {{
    display: inline-block;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.03em;
    color: #fff;
    background: #e53e3e;
    border-radius: 4px;
    padding: 0.1rem 0.4rem;
    margin-right: 0.4rem;
    vertical-align: middle;
  }}
  .bookmark-btn {{
    position: absolute;
    top: 1.25rem;
    right: 0;
    font-size: 1.3rem;
    line-height: 1;
    background: none;
    border: none;
    cursor: pointer;
    color: var(--muted);
    padding: 0.1rem 0.3rem;
  }}
  .bookmark-btn[aria-pressed="true"] {{ color: #d69e2e; }}
  #bookmark-empty {{
    display: none;
    color: var(--muted);
    font-size: 0.9rem;
  }}
  .title-en {{
    font-size: 0.8rem;
    font-style: italic;
    color: var(--muted);
    margin: -0.15rem 0 0.5rem;
  }}
  .meta {{
    font-size: 0.8rem;
    color: var(--muted);
    margin-bottom: 0.6rem;
  }}
  .summary {{
    white-space: pre-line;
    font-size: 0.95rem;
  }}
  .abstract-image {{
    width: 100%;
    max-height: 420px;
    object-fit: contain;
    background: var(--border);
    border-radius: 8px;
    border: 1px solid var(--border);
    display: block;
    margin-bottom: 0.6rem;
  }}
  .abstract-image-caption {{
    font-size: 0.72rem;
    color: var(--muted);
    margin: -0.4rem 0 0.6rem;
  }}
  .abstract-card {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.7rem 1rem;
  }}
  @media (max-width: 480px) {{
    .abstract-card {{ grid-template-columns: 1fr; }}
  }}
  .abstract-card .section {{
    border-left: 3px solid var(--section-color, var(--accent));
    padding: 0.1rem 0 0.1rem 0.6rem;
  }}
  .abstract-card .section .label {{
    display: block;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    color: var(--section-color, var(--accent));
    margin-bottom: 0.15rem;
  }}
  .abstract-card .section .text {{
    font-size: 0.88rem;
    line-height: 1.55;
  }}
  a {{ color: var(--accent); }}
  footer {{
    margin-top: 3rem;
    font-size: 0.8rem;
    color: var(--muted);
  }}
</style>
</head>
<body>
<header>
  <h1>小児消化器 論文まとめ</h1>
  <p class="updated">最終更新: {updated}</p>
  <p class="disclaimer">
    本サイトはPubMed掲載論文の抄録をAI（Claude）が自動で日本語要約したものです。
    誤りや訳出のニュアンス差を含む可能性があるため、内容の正確性は必ず原著論文で確認してください。
  </p>
  <div class="toolbar">
    <a class="btn" href="{workflow_url}" target="_blank" rel="noopener">↻ 更新を実行（GitHub）</a>
    <button id="bookmark-filter-btn" class="btn" type="button" aria-pressed="false">☆ ブックマークのみ表示</button>
    <span class="bookmark-count-label">ブックマーク: <span id="bookmark-count">0</span>件</span>
  </div>
</header>
<main>
<p id="bookmark-empty">ブックマークした論文はまだありません。各論文右上の☆で追加できます。</p>
{articles}
</main>
<footer>
  <p>データ提供: PubMed（NCBI）。要約生成: Anthropic Claude API。</p>
  <p>ブックマークはこのブラウザ内（localStorage）にのみ保存され、他の端末とは同期されません。</p>
</footer>
<script>
(function () {{
  var KEY = "pgi-bookmarks";

  function getBookmarks() {{
    try {{
      return JSON.parse(localStorage.getItem(KEY) || "[]");
    }} catch (e) {{
      return [];
    }}
  }}

  function setBookmarks(list) {{
    localStorage.setItem(KEY, JSON.stringify(list));
  }}

  function updateCount() {{
    var el = document.getElementById("bookmark-count");
    if (el) el.textContent = getBookmarks().length;
  }}

  var filterActive = false;

  function applyFilter() {{
    var bookmarks = getBookmarks();
    document.querySelectorAll("article[data-pmid]").forEach(function (a) {{
      var pmid = a.getAttribute("data-pmid");
      a.style.display = (!filterActive || bookmarks.indexOf(pmid) !== -1) ? "" : "none";
    }});
    var empty = document.getElementById("bookmark-empty");
    if (empty) empty.style.display = (filterActive && bookmarks.length === 0) ? "" : "none";
  }}

  function toggleBookmark(btn) {{
    var article = btn.closest("article");
    var pmid = article.getAttribute("data-pmid");
    var list = getBookmarks();
    var idx = list.indexOf(pmid);
    if (idx === -1) {{
      list.push(pmid);
      btn.textContent = "★";
      btn.setAttribute("aria-pressed", "true");
    }} else {{
      list.splice(idx, 1);
      btn.textContent = "☆";
      btn.setAttribute("aria-pressed", "false");
    }}
    setBookmarks(list);
    updateCount();
    if (filterActive) applyFilter();
  }}

  function toggleFilter() {{
    filterActive = !filterActive;
    var btn = document.getElementById("bookmark-filter-btn");
    btn.setAttribute("aria-pressed", filterActive ? "true" : "false");
    btn.textContent = filterActive ? "★ すべて表示" : "☆ ブックマークのみ表示";
    applyFilter();
  }}

  document.addEventListener("DOMContentLoaded", function () {{
    var bookmarks = getBookmarks();
    document.querySelectorAll("article[data-pmid]").forEach(function (a) {{
      var pmid = a.getAttribute("data-pmid");
      var btn = a.querySelector(".bookmark-btn");
      if (btn && bookmarks.indexOf(pmid) !== -1) {{
        btn.textContent = "★";
        btn.setAttribute("aria-pressed", "true");
      }}
      if (btn) btn.addEventListener("click", function () {{ toggleBookmark(btn); }});
    }});
    updateCount();
    var filterBtn = document.getElementById("bookmark-filter-btn");
    if (filterBtn) filterBtn.addEventListener("click", toggleFilter);
  }});
}})();
</script>
</body>
</html>
"""

ARTICLE_TEMPLATE = """<article data-pmid="{pmid}">
  <button class="bookmark-btn" type="button" aria-pressed="false" aria-label="ブックマーク">☆</button>
  <h2>{new_badge}{title}</h2>
  {title_en_html}
  <p class="meta">{journal}{pub_date_sep}{pub_date} ・ PMID: <a href="{url}" target="_blank" rel="noopener">{pmid}</a>{doi_link}</p>
  {image_html}{abstract_html}
</article>"""

# 要約テキストの行ラベルと、カード表示時のアクセントカラーの対応
SECTION_COLORS = {
    "背景": "var(--sec-background)",
    "方法": "var(--sec-method)",
    "結果": "var(--sec-result)",
    "臨床的示唆": "var(--sec-implication)",
}


def esc(s: str) -> str:
    return html.escape(s or "")


def parse_summary_sections(summary_ja: str) -> list[tuple[str, str]]:
    """「- 背景:...」「・方法：...」形式の要約テキストを (ラベル, 本文) のリストに分解する。"""
    sections = []
    for line in summary_ja.split("\n"):
        line = line.strip().lstrip("・-").strip()
        if not line:
            continue
        for sep in (":", "："):
            if sep in line:
                label, _, text = line.partition(sep)
                sections.append((label.strip(), text.strip()))
                break
        else:
            sections.append(("", line))
    return sections


def render_abstract_card(article: dict) -> str:
    """要約を背景/方法/結果/臨床的示唆の4分割カードとして描画する。
    想定外フォーマットの場合はプレーンテキストにフォールバックする。"""
    summary = article.get("summary_ja")
    if not summary:
        return '<p class="summary">(要約は準備中です)</p>'

    sections = parse_summary_sections(summary)
    if len(sections) != 4:
        return f'<p class="summary">{esc(summary)}</p>'

    cells = []
    for label, text in sections:
        color = SECTION_COLORS.get(label, "var(--accent)")
        cells.append(
            f'<div class="section" style="--section-color: {color}">'
            f'<span class="label">{esc(label)}</span>'
            f'<span class="text">{esc(text)}</span>'
            f"</div>"
        )
    return '<div class="abstract-card">' + "".join(cells) + "</div>"


def is_new(article: dict, today: date) -> bool:
    first_seen = article.get("first_seen")
    if not first_seen:
        return False
    try:
        seen_date = date.fromisoformat(first_seen)
    except ValueError:
        return False
    return (today - seen_date) <= timedelta(days=NEW_BADGE_DAYS)


def render_article(article: dict, today: date) -> str:
    title_ja = article.get("title_ja")
    title_en = article.get("title", "")
    if title_ja:
        title_html = esc(title_ja)
        title_en_html = f'<p class="title-en">{esc(title_en)}</p>'
    else:
        title_html = esc(title_en)
        title_en_html = ""

    doi_link = ""
    if article.get("doi"):
        doi_link = f' ・ DOI: <a href="https://doi.org/{esc(article["doi"])}" target="_blank" rel="noopener">{esc(article["doi"])}</a>'

    abstract_html = render_abstract_card(article)

    # graphical_abstract_url は現状は自動取得しない（対象雑誌はボット対策/エンバーゴにより
    # 機械的な取得がほぼ不可能なため）。手動で追記された場合のみ画像を優先表示し、
    # 読み込み失敗時は生成カードにフォールバックする。
    image_html = ""
    image_url = article.get("graphical_abstract_url")
    if image_url:
        abstract_html = abstract_html.replace('style="display:none">', '>', 1)  # 念のため
        abstract_html = abstract_html.replace(
            '<div class="abstract-card">', '<div class="abstract-card" style="display:none">', 1
        )
        if not abstract_html.startswith('<div class="abstract-card"'):
            abstract_html = f'<div style="display:none">{abstract_html}</div>'
        image_html = (
            f'<img class="abstract-image" src="{esc(image_url)}" '
            f'alt="{esc(article.get("title", ""))} のグラフィカルアブストラクト" '
            f'loading="lazy" referrerpolicy="no-referrer" '
            f"onerror=\"this.style.display='none'; this.nextElementSibling.style.display='';\">"
        )

    new_badge = '<span class="new-badge">NEW</span>' if is_new(article, today) else ""

    return ARTICLE_TEMPLATE.format(
        title=title_html,
        title_en_html=title_en_html,
        journal=esc(article.get("journal", "")),
        pub_date_sep=" ・ " if article.get("journal") and article.get("pub_date") else "",
        pub_date=esc(article.get("pub_date", "")),
        url=esc(article.get("url", "")),
        pmid=esc(article.get("pmid", "")),
        doi_link=doi_link,
        image_html=image_html,
        abstract_html=abstract_html,
        new_badge=new_badge,
    )


def main() -> None:
    papers = json.loads(PAPERS_PATH.read_text(encoding="utf-8")) if PAPERS_PATH.exists() else {}

    # pub_date は年のみのことがあるため、PMID（新しいほど大きい）を主なソートキーにする
    articles = sorted(papers.values(), key=lambda a: int(a.get("pmid", 0)), reverse=True)

    today = date.today()
    articles_html = "\n".join(render_article(a, today) for a in articles) or "<p>まだ論文がありません。</p>"

    updated = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")

    page = PAGE_TEMPLATE.format(updated=updated, articles=articles_html, workflow_url=WORKFLOW_URL)

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "index.html").write_text(page, encoding="utf-8")
    (DOCS_DIR / ".nojekyll").write_text("", encoding="utf-8")

    print(f"docs/index.html を生成しました（{len(articles)}件）")


if __name__ == "__main__":
    main()
