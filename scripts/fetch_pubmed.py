#!/usr/bin/env python3
"""
PubMedから小児消化器領域の新着論文を取得し、data/papers.json に追記する（PMIDで重複排除）。

このスクリプト単体では日本語要約は行わない（要約は別スクリプトで後付けする）。
"""
import json
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PAPERS_PATH = DATA_DIR / "papers.json"

# 小児消化器専門誌: 全件を対象にする
PEDIATRIC_SPECIFIC_JOURNALS = [
    "J Pediatr Gastroenterol Nutr",  # Journal of Pediatric Gastroenterology and Nutrition (JPGN)
    "Pediatr Gastroenterol Hepatol Nutr",  # Pediatric Gastroenterology, Hepatology & Nutrition (PGHN)
]

# 消化器・肝臓の総合誌（成人領域も扱うため、小児関連の記事のみに絞り込む）
GENERAL_JOURNALS = [
    "Gastroenterology",
    "Gut",
    "Hepatology",
    "J Hepatol",  # Journal of Hepatology
    "Clin Gastroenterol Hepatol",  # Clinical Gastroenterology and Hepatology
    "Intest Res",  # Intestinal Research
]

PEDIATRIC_FILTER = '(child[MeSH Terms] OR pediatric[tiab] OR paediatric[tiab])'


def _journal_or(journals: list[str]) -> str:
    return "(" + " OR ".join(f'"{j}"[ta]' for j in journals) + ")"


SEARCH_TERM = (
    f"({_journal_or(PEDIATRIC_SPECIFIC_JOURNALS)} OR "
    f"({_journal_or(GENERAL_JOURNALS)} AND {PEDIATRIC_FILTER}))"
)

# 直近何日分を対象にするか
RELDATE_DAYS = 14
RETMAX = 50
REQUEST_INTERVAL_SEC = 0.4  # NCBI利用ガイドライン（無登録時は3req/sec以下）


def http_get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "pediatric-gi-digest/0.1"})
    with urllib.request.urlopen(req, timeout=30) as res:
        return res.read()


def esearch() -> list[str]:
    params = {
        "db": "pubmed",
        "term": SEARCH_TERM,
        "retmax": str(RETMAX),
        "retmode": "json",
        "datetype": "pdat",
        "reldate": str(RELDATE_DAYS),
        "sort": "pub+date",
    }
    url = f"{EUTILS_BASE}/esearch.fcgi?{urllib.parse.urlencode(params)}"
    body = http_get(url)
    data = json.loads(body)
    return data.get("esearchresult", {}).get("idlist", [])


def efetch(pmids: list[str]) -> list[dict]:
    if not pmids:
        return []
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "rettype": "abstract",
        "retmode": "xml",
    }
    url = f"{EUTILS_BASE}/efetch.fcgi?{urllib.parse.urlencode(params)}"
    body = http_get(url)
    root = ET.fromstring(body)

    articles = []
    for art in root.findall(".//PubmedArticle"):
        pmid_el = art.find(".//PMID")
        pmid = pmid_el.text if pmid_el is not None else None
        if not pmid:
            continue

        title_el = art.find(".//ArticleTitle")
        title = "".join(title_el.itertext()).strip() if title_el is not None else ""

        abstract_parts = [
            "".join(t.itertext()).strip()
            for t in art.findall(".//Abstract/AbstractText")
        ]
        abstract = "\n".join(p for p in abstract_parts if p)

        journal_el = art.find(".//Journal/Title")
        journal = journal_el.text if journal_el is not None else ""

        year_el = art.find(".//JournalIssue/PubDate/Year")
        medline_date_el = art.find(".//JournalIssue/PubDate/MedlineDate")
        pub_date = (
            year_el.text if year_el is not None
            else (medline_date_el.text if medline_date_el is not None else "")
        )

        doi = ""
        for aid in art.findall(".//ArticleIdList/ArticleId"):
            if aid.get("IdType") == "doi":
                doi = aid.text or ""

        articles.append({
            "pmid": pmid,
            "title": title,
            "abstract": abstract,
            "journal": journal,
            "pub_date": pub_date,
            "doi": doi,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "summary_ja": None,  # 後段の要約スクリプトが埋める
        })
    return articles


def load_existing() -> dict:
    if PAPERS_PATH.exists():
        return json.loads(PAPERS_PATH.read_text(encoding="utf-8"))
    return {}


def save(papers: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PAPERS_PATH.write_text(
        json.dumps(papers, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    existing = load_existing()
    pmids = esearch()
    new_pmids = [p for p in pmids if p not in existing]

    print(f"検索結果: {len(pmids)}件 / 新規: {len(new_pmids)}件", file=sys.stderr)

    # efetchは一度に多数投げすぎないようバッチ分割
    batch_size = 20
    new_articles: list[dict] = []
    for i in range(0, len(new_pmids), batch_size):
        batch = new_pmids[i:i + batch_size]
        new_articles.extend(efetch(batch))
        time.sleep(REQUEST_INTERVAL_SEC)

    today = date.today().isoformat()
    for article in new_articles:
        article["first_seen"] = today  # サイト上でNEW表示するために使う
        existing[article["pmid"]] = article

    save(existing)
    print(f"data/papers.json に {len(new_articles)}件を追加保存しました", file=sys.stderr)


if __name__ == "__main__":
    main()
