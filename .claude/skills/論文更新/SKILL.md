---
name: 論文更新
description: 小児消化器 論文まとめサイトの更新パイプライン（PubMed取得→Claude要約→サイト生成→コミット/push）を実行する。「論文サイトを更新して」「最新の論文を取り込んで」「サイトを最新化して」等のリクエストで使う。
---

# 小児消化器 論文まとめサイト 更新

このリポジトリ配下のパイプラインを順番に実行し、PubMedの新着論文を取得 → 日本語要約 → サイト再生成 → コミットまで行う。

## 前提

- 対象雑誌: JPGN, PGHN, Gastroenterology, Gut, Hepatology, J Hepatol, Clin Gastroenterol Hepatol, Intest Res
  （`scripts/fetch_pubmed.py` の `PEDIATRIC_SPECIFIC_JOURNALS` / `GENERAL_JOURNALS` を参照。変更する場合はこのファイルを編集する）
- ローカル実行には `.env` に `ANTHROPIC_API_KEY` が設定されている必要がある

## 手順

1. プロジェクトルートに移動する
2. `set -a && source .env && set +a && python3 scripts/fetch_pubmed.py` を実行し、新着論文を `data/papers.json` に追記する
3. 取得件数を確認する。0件なら、その旨を伝えて要約以降はスキップしてよいか確認する
4. `python3 scripts/summarize.py` を実行し、未要約の論文にClaude API（`claude-sonnet-5`）で日本語要約を生成する
   - API課金が発生するため、件数が多い場合（目安10件以上）は事前に概算コストを伝えて実行の確認を取る
5. `python3 scripts/build_site.py` を実行し、`docs/index.html` を再生成する
6. `git add data/papers.json docs/` → 変更があれば `git commit -m "chore: 論文まとめ自動更新"`
7. **push前に必ずユーザーに確認する**（グローバル方針: git pushは事前確認必須）。確認が取れたら `git push`

## 注意点

- `data/papers.json` は既存データとPMIDで重複排除されるため、再実行しても安全
- 新規追加論文には `fetch_pubmed.py` が `first_seen`（取得日）を付与し、`build_site.py` が直近7日以内ならNEWバッジを表示する（`NEW_BADGE_DAYS`で調整可）
- サイト上の「更新を実行」ボタンはGitHub Actionsの実行ページへのリンクのみ（サイト訪問者が直接実行することはできない設計）
- ブックマークは各ブラウザのlocalStorageに保存され、サーバー側やリポジトリには保存されない
- 対象雑誌を変更したい場合は `scripts/fetch_pubmed.py` の `PEDIATRIC_SPECIFIC_JOURNALS` / `GENERAL_JOURNALS` を編集する
- GitHub Actions（Actionsタブから手動実行）でも同じ処理が実行できる。ローカル実行はテストや即時反映したい場合に使う
- サイト公開先: https://tnokats0416.github.io/pediatric-gi-report/
