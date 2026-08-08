#!/usr/bin/env python3
"""
data/papers.json のうち summary_ja / title_ja が未生成のレコードに、Claude APIで日本語化を付与する。

- abstractがあり summary_ja が未生成の記事: タイトル訳 + 4項目要約を1回のリクエストで生成
- 上記以外でtitle_jaが未生成の記事（abstractがない記事、または要約済みでタイトル訳のみ未生成の記事）:
  タイトル訳のみを軽量なリクエストで生成（既存の要約文はそのまま保持し、再生成コストをかけない）

環境変数 ANTHROPIC_API_KEY が必要（未設定ならエラーで終了）。
"""
import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-5"  # 医療情報の要約なので精度重視。コストを抑えたい場合は claude-haiku-4-5-20251001 に変更可
ANTHROPIC_VERSION = "2023-06-01"

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PAPERS_PATH = DATA_DIR / "papers.json"

REQUEST_INTERVAL_SEC = 0.5

SYSTEM_PROMPT = (
    "あなたは小児消化器領域を専門とする医師向けに、英語の医学論文タイトル・抄録を日本語化するアシスタントです。"
    "読者は医療者なので専門用語はそのまま使ってよく、平易化は不要です。"
    "以下の形式で出力してください（前置きや結びの文、装飾記号は不要）。\n"
    "1行目: 論文タイトルの日本語訳のみ\n"
    "2行目以降: 次の4項目を簡潔な箇条書きで（各1〜2文、合計200字程度まで）\n"
    "・背景\n・方法\n・結果\n・臨床的示唆\n"
    "推測や原文にない情報は追加しないでください。"
)

TITLE_SYSTEM_PROMPT = (
    "あなたは医学論文のタイトルを日本語に翻訳するアシスタントです。"
    "読者は医療者なので専門用語はそのまま使ってよく、平易化は不要です。"
    "日本語訳のタイトルのみを1行で出力してください（前置き・引用符・記号は不要）。"
)


def build_user_prompt(article: dict) -> str:
    return (
        f"タイトル: {article['title']}\n\n"
        f"抄録:\n{article['abstract']}"
    )


def build_title_prompt(article: dict) -> str:
    return f"タイトル: {article['title']}"


def parse_combined_response(text: str) -> tuple[str, str]:
    lines = [l for l in text.strip().split("\n") if l.strip()]
    if not lines:
        return "", ""
    title_ja = lines[0].strip()
    summary_ja = "\n".join(lines[1:]).strip()
    return title_ja, summary_ja


def call_claude(system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("エラー: 環境変数 ANTHROPIC_API_KEY が未設定です", file=sys.stderr)
        sys.exit(1)

    payload = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": user_prompt}
        ],
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as res:
        body = json.loads(res.read())
    return "".join(block.get("text", "") for block in body.get("content", []))


def load_papers() -> dict:
    if not PAPERS_PATH.exists():
        print("エラー: data/papers.json が見つかりません。先に fetch_pubmed.py を実行してください", file=sys.stderr)
        sys.exit(1)
    return json.loads(PAPERS_PATH.read_text(encoding="utf-8"))


def save_papers(papers: dict) -> None:
    PAPERS_PATH.write_text(
        json.dumps(papers, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="処理する件数の上限（動作確認用）")
    args = parser.parse_args()

    papers = load_papers()

    work: list[tuple[str, dict]] = []
    for article in papers.values():
        if article.get("abstract") and not article.get("summary_ja"):
            # abstractがあり要約未生成 → タイトル訳+要約をまとめて生成
            work.append(("full", article))
        elif not article.get("title_ja"):
            # abstractがない（要約対象外）、または要約済みでタイトル訳のみ未生成
            work.append(("title_only", article))

    if args.limit is not None:
        work = work[: args.limit]

    full_count = sum(1 for kind, _ in work if kind == "full")
    title_only_count = sum(1 for kind, _ in work if kind == "title_only")
    print(
        f"処理対象: {full_count}件（新規タイトル訳+要約）, {title_only_count}件（タイトル訳のみ）",
        file=sys.stderr,
    )

    done = 0
    for kind, article in work:
        try:
            if kind == "full":
                text = call_claude(SYSTEM_PROMPT, build_user_prompt(article), 500)
                title_ja, summary_ja = parse_combined_response(text)
                if title_ja:
                    article["title_ja"] = title_ja
                if summary_ja:
                    article["summary_ja"] = summary_ja
            else:
                title_ja = call_claude(TITLE_SYSTEM_PROMPT, build_title_prompt(article), 100).strip()
                if title_ja:
                    article["title_ja"] = title_ja
        except Exception as e:  # noqa: BLE001 - バッチ処理なので1件の失敗で全体を止めない
            print(f"警告: PMID {article['pmid']} の処理に失敗: {e}", file=sys.stderr)
            continue

        done += 1

        # 数件ごとに保存し、途中失敗しても進捗を失わないようにする
        if done % 5 == 0:
            save_papers(papers)
        time.sleep(REQUEST_INTERVAL_SEC)

    save_papers(papers)
    print(f"完了: {done}/{len(work)}件を処理しました", file=sys.stderr)


if __name__ == "__main__":
    main()
