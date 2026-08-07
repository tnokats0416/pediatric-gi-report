#!/usr/bin/env python3
"""
data/papers.json から静的サイト（docs/index.html）を生成する。
外部テンプレートエンジンには依存せず、標準ライブラリのみで組み立てる。
"""
import html
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAPERS_PATH = ROOT / "data" / "papers.json"
DOCS_DIR = ROOT / "docs"

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
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #14181a;
      --fg: #eaeaea;
      --muted: #9a9a9a;
      --border: #2c3234;
      --accent: #4fd1b8;
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
  article {{
    border-bottom: 1px solid var(--border);
    padding: 1.25rem 0;
  }}
  article h2 {{
    font-size: 1.05rem;
    margin: 0 0 0.4rem;
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
</header>
<main>
{articles}
</main>
<footer>
  <p>データ提供: PubMed（NCBI）。要約生成: Anthropic Claude API。</p>
</footer>
</body>
</html>
"""

ARTICLE_TEMPLATE = """<article>
  <h2>{title}</h2>
  <p class="meta">{journal}{pub_date_sep}{pub_date} ・ PMID: <a href="{url}" target="_blank" rel="noopener">{pmid}</a>{doi_link}</p>
  <p class="summary">{summary}</p>
</article>"""


def esc(s: str) -> str:
    return html.escape(s or "")


def render_article(article: dict) -> str:
    doi_link = ""
    if article.get("doi"):
        doi_link = f' ・ DOI: <a href="https://doi.org/{esc(article["doi"])}" target="_blank" rel="noopener">{esc(article["doi"])}</a>'

    summary = article.get("summary_ja") or "(要約は準備中です)"

    return ARTICLE_TEMPLATE.format(
        title=esc(article.get("title", "")),
        journal=esc(article.get("journal", "")),
        pub_date_sep=" ・ " if article.get("journal") and article.get("pub_date") else "",
        pub_date=esc(article.get("pub_date", "")),
        url=esc(article.get("url", "")),
        pmid=esc(article.get("pmid", "")),
        doi_link=doi_link,
        summary=esc(summary),
    )


def main() -> None:
    papers = json.loads(PAPERS_PATH.read_text(encoding="utf-8")) if PAPERS_PATH.exists() else {}

    # pub_date は年のみのことがあるため、PMID（新しいほど大きい）を主なソートキーにする
    articles = sorted(papers.values(), key=lambda a: int(a.get("pmid", 0)), reverse=True)

    articles_html = "\n".join(render_article(a) for a in articles) or "<p>まだ論文がありません。</p>"

    updated = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")

    page = PAGE_TEMPLATE.format(updated=updated, articles=articles_html)

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "index.html").write_text(page, encoding="utf-8")
    (DOCS_DIR / ".nojekyll").write_text("", encoding="utf-8")

    print(f"docs/index.html を生成しました（{len(articles)}件）")


if __name__ == "__main__":
    main()
