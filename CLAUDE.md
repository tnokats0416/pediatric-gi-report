# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

小児消化器領域の最新論文を自動収集し、日本語で簡潔に要約して公開するサイト。**医療者向け**（専門用語を許容、平易化はしない）。

- 論文取得元: PubMed（E-utilities API）。小児消化器関連（IBD、便秘、GERD、肝疾患、栄養、内視鏡等）のクエリで新着を検索
- 要約生成: Claude APIでabstractを日本語要約（PMID/DOI/原文リンクを必ず併記）
- 更新方式: GitHub Actionsのcronで「取得→要約→サイト再ビルド→デプロイ」を自動実行（人手介入なし）
- ホスティング: GitHub Pages想定
- 免責事項: 「AIによる自動要約であり、正確性は原著論文で確認すること」を明記する

## 重要な設計判断

- 新着論文はPMIDで重複排除する（取得済みIDを永続化して管理）
- 要約には出典リンクを必ず添える。AI要約単体で完結させない
- GitHub Secretsに `ANTHROPIC_API_KEY` を登録して要約生成に使用する
- 対象雑誌はJPGN, PGHN, Gastroenterology, Gut, Hepatology, J Hepatol, Clin Gastroenterol Hepatol, Intest Res（`scripts/fetch_pubmed.py`）
- GitHub Actionsは `workflow_dispatch` のみ（自動cronなし、手動実行）
- 要約は「背景/方法/結果/臨床的示唆」の4行固定フォーマットで生成させ（`scripts/summarize.py`のSYSTEM_PROMPT）、`scripts/build_site.py`でこれをパースし色分けされたカード表示にしている。フォーマットが崩れた場合はプレーンテキストにフォールバックする
- 公式グラフィカルアブストラクトの自動取得は実装していない（対象雑誌はWiley/Elsevier/BMJ等でボット対策により直接取得不可、かつ対象記事はEurope PMCでもOA化前でほぼ取得不可なため）。`graphical_abstract_url` フィールドを手動で設定すれば画像優先表示・失敗時カードへのフォールバックには対応済み

## アーキテクチャ

- `scripts/fetch_pubmed.py`: PubMed E-utilitiesから新着論文を取得し `data/papers.json` にPMIDで重複排除して保存（要約は行わない）
- `scripts/summarize.py`: `summary_ja` が未設定の記事にClaude API（`claude-sonnet-5`）で日本語要約を生成
- `scripts/build_site.py`: `data/papers.json` から `docs/index.html` を生成（外部テンプレートエンジン不使用、標準ライブラリのみ）
- `.claude/skills/論文更新/SKILL.md`: 上記3スクリプトの実行〜コミット〜push確認までを行うスキル
- `.github/workflows/update.yml`: 同じパイプラインをGitHub Actions上で手動実行するワークフロー
- 公開先: GitHub Pages（`main`ブランチの`/docs`、Publicリポジトリ） https://tnokats0416.github.io/pediatric-gi-report/
