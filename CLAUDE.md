# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

小児消化器領域の最新論文を自動収集し、日本語で簡潔に要約して公開するサイト。**医療者向け**（専門用語を許容、平易化はしない）。

- 論文取得元: PubMed（E-utilities API）。小児消化器関連（IBD、便秘、GERD、肝疾患、栄養、内視鏡等）のクエリで新着を検索
- 要約生成: Claude APIでabstractを日本語要約（PMID/DOI/原文リンクを必ず併記）
- 更新方式: GitHub Actionsのcronで「取得→要約→サイト再ビルド→デプロイ」を自動実行（人手介入なし）
- ホスティング: GitHub Pages想定
- 免責事項: 「AIによる自動要約であり、正確性は原著論文で確認すること」を明記する

現時点ではコード未実装（フォルダは空）。上記は実装前に合意した方針であり、実装が進んだら本ファイルの「アーキテクチャ」「コマンド」節を実態に合わせて更新すること。

## 重要な設計判断

- 新着論文はPMIDで重複排除する（取得済みIDを永続化して管理）
- 要約には出典リンクを必ず添える。AI要約単体で完結させない
- GitHub Secretsに `ANTHROPIC_API_KEY` を登録して要約生成に使用する
