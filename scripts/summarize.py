#!/usr/bin/env python3
"""
data/papers.json のうち summary_ja が未生成のレコードに、Claude APIで日本語要約を付与する。

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
    "あなたは小児消化器領域を専門とする医師向けに、英語の医学論文抄録を日本語で要約するアシスタントです。"
    "読者は医療者なので専門用語はそのまま使ってよく、平易化は不要です。"
    "出力は以下の4項目を簡潔な箇条書きで示してください（各1〜2文、合計200字程度まで）。\n"
    "・背景\n・方法\n・結果\n・臨床的示唆\n"
    "推測や原文にない情報は追加しないでください。前置きや結びの文は不要で、箇条書きのみを出力してください。"
)


def build_user_prompt(article: dict) -> str:
    return (
        f"タイトル: {article['title']}\n\n"
        f"抄録:\n{article['abstract']}"
    )


def call_claude(article: dict) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("エラー: 環境変数 ANTHROPIC_API_KEY が未設定です", file=sys.stderr)
        sys.exit(1)

    payload = {
        "model": MODEL,
        "max_tokens": 500,
        "system": SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": build_user_prompt(article)}
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
    parser.add_argument("--limit", type=int, default=None, help="要約する件数の上限（動作確認用）")
    args = parser.parse_args()

    papers = load_papers()
    targets = [p for p in papers.values() if not p.get("summary_ja") and p.get("abstract")]
    if args.limit is not None:
        targets = targets[: args.limit]

    print(f"要約対象: {len(targets)}件", file=sys.stderr)

    done = 0
    for article in targets:
        try:
            summary = call_claude(article)
        except Exception as e:  # noqa: BLE001 - バッチ処理なので1件の失敗で全体を止めない
            print(f"警告: PMID {article['pmid']} の要約に失敗: {e}", file=sys.stderr)
            continue

        papers[article["pmid"]]["summary_ja"] = summary.strip()
        done += 1

        # 数件ごとに保存し、途中失敗しても進捗を失わないようにする
        if done % 5 == 0:
            save_papers(papers)
        time.sleep(REQUEST_INTERVAL_SEC)

    save_papers(papers)
    print(f"完了: {done}/{len(targets)}件を要約しました", file=sys.stderr)


if __name__ == "__main__":
    main()
