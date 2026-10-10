"""Probe Crossref discipline filtering and collect 10 metadata records.

Python standard library only. The comparison is not a classifier: a keyword
query and a journal scope are collection criteria, not article subject labels.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
API = "https://api.crossref.org"
SOURCES = {
    "subject_deprecation": "https://www.crossref.org/blog/subject-codes-incomplete-and-unreliable-have-got-to-go/",
    "deprecation_confirmation": "https://community.crossref.org/t/get-works-by-category-name/5799",
    "filters": "https://www.crossref.org/documentation/retrieve-metadata/rest-api/rest-api-filters/",
    "queries": "https://api.crossref.org/",
}


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def get_json(path: str, params: dict, output: Path, label: str) -> dict:
    """Save status, original JSON response and request parameters, even for 400s."""
    public_url = f"{API}{path}?{urlencode(params)}"
    actual_params = dict(params)
    contact = os.getenv("CROSSREF_MAILTO", "").strip()
    if contact:
        actual_params["mailto"] = contact
    request = Request(
        f"{API}{path}?{urlencode(actual_params)}",
        headers={"User-Agent": "AcademicPlatform-CrossrefDisciplineProbe/0.1", "Accept": "application/json"},
    )
    for attempt in range(1, 4):
        print(f"[{label}] request {attempt}/3: {public_url}", flush=True)
        started = time.monotonic()
        try:
            with urlopen(request, timeout=25) as response:
                status, headers, raw = response.status, response.headers, response.read()
        except HTTPError as exc:
            status, headers, raw = exc.code, exc.headers, exc.read()
        except (URLError, TimeoutError, OSError) as exc:
            write_json(output / f"{label}_network_error_{attempt}.json", {
                "request_url": public_url,
                "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
                "error": str(exc),
            })
            if attempt == 3 or "10013" in str(exc):
                raise RuntimeError(f"Network failure during {label}: {exc}") from exc
            time.sleep(attempt * 2)
            continue
        try:
            payload = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            payload = {"non_json_response": raw.decode("utf-8", errors="replace")}
        result = {
            "request_url": public_url,  # Contact email is deliberately omitted from artifacts.
            "request_params": params,
            "access_pool_requested": "polite" if contact else "public",
            "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "http_status": status,
            "attempt": attempt,
            "response_headers": {k: v for k, v in headers.items()
                                 if k.lower().startswith("x-rate-limit") or k.lower() == "retry-after"},
            "response": payload,
        }
        write_json(output / f"{label}.json", result)
        print(f"[{label}] HTTP {status}", flush=True)
        if status in {429, 500, 502, 503, 504} and attempt < 3:
            retry_after = headers.get("Retry-After", "")
            if retry_after.isdigit() and int(retry_after) > 60:
                raise RuntimeError(f"Rate limited; retry after {retry_after}s. Partial evidence saved.")
            time.sleep(max(attempt * 2, int(retry_after) if retry_after.isdigit() else 0))
            continue
        return result
    raise RuntimeError("Request retry limit reached")


def subject_state(item: dict) -> str:
    if "subject" not in item:
        return "missing"
    if not item["subject"]:
        return "empty"
    return "present"


def exclusion_reason(item: dict) -> str | None:
    """Conservative screening of obvious non-paper records, not a classifier."""
    title = " ".join(item.get("title", [])).strip().casefold()
    if not title:
        return "missing_title"
    if re.fullmatch(r"(editorial board|editorial|table of contents|contents|front matter|back matter)[.\s]*", title):
        return "obvious_front_matter_title"
    if re.match(r"^(erratum|corrigendum|correction|retraction)(\s+to\b|\s*[:：])", title):
        return "correction_or_retraction_title"
    return None


def summary(item: dict, method: str, evidence_file: str) -> dict:
    published = item.get("published", {}).get("date-parts", [[]])[0]
    return {
        "method": method,
        "doi": item["DOI"].strip().lower(),
        "title": " / ".join(item.get("title", [])),
        "container_title": item.get("container-title", []),
        "issn": item.get("ISSN", []),
        "type": item.get("type"),
        "published": published,
        "subject_field_state": subject_state(item),
        "crossref_subject": item.get("subject"),
        "has_abstract": bool(item.get("abstract")),
        "evidence_file": evidence_file,
        "classification_status": "not_classified",  # Never invent a Crossref subject.
    }


def cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def render_report(manifest: dict, records: list[dict]) -> str:
    lines = [
        "# Crossref 学科定向采集：实际请求记录", "",
        f"- 请求完成时间（UTC）：{manifest['completed_at_utc']}",
        f"- 关键词：`{manifest['query']}`；限定期刊 ISSN：`{manifest['issn']}`。",
        f"- 关键词请求字段：`query.{manifest['query_field']}`；明显非论文记录排除数：{manifest['excluded_count']}。",
        f"- 出版日期范围：{manifest['from_date']} 至 {manifest['until_date']}。",
        f"- 保存 {len(records)} 条不同 DOI 的期刊文章元数据，未下载论文全文。", "",
        "## 1. 学科过滤参数探测", "",
        "以下请求使用 rows=0，只检查过滤器响应，不额外采集文章。400 表示参数无效，不能解释为该学科没有论文；旧分类过滤返回 0 也不能推断该领域无论文。", "",
        "| 参数 | HTTP | total-results | 响应文件 |", "|---|---:|---:|---|",
    ]
    for probe in manifest["filter_probes"]:
        lines.append(f"| `{probe['filter']}` | {probe['http_status']} | {probe['total_results']} | [{probe['file']}]({probe['file']}) |")
    lines += ["", "## 2. 定向采集比较", "",
              "| 方法 | 条数 | subject 非空 | subject 空值 | subject 缺失 | 不同期刊数 |",
              "|---|---:|---:|---:|---:|---:|"]
    for method in ("keyword", "journal_issn"):
        rows = [r for r in records if r["method"] == method]
        states = Counter(r["subject_field_state"] for r in rows)
        venues = {tuple(r["container_title"]) for r in rows}
        lines.append(f"| {method} | {len(rows)} | {states['present']} | {states['empty']} | {states['missing']} | {len(venues)} |")
    lines += ["", "## 3. 采集到的文章", "",
              "| 方法 | 标题 | 期刊 | DOI | subject 状态 |", "|---|---|---|---|---|"]
    for record in records:
        doi = record["doi"]
        lines.append(f"| {record['method']} | {cell(record['title'])} | {cell('; '.join(record['container_title']))} | [{doi}](https://doi.org/{doi}) | {record['subject_field_state']} |")
    lines += ["", "## 4. 解释边界", "",
              f"- keyword 使用 query.{manifest['query_field']} 按相关度检索；命中关键词并不等于获得文章级学科分类。",
              "- 按标题规则排除明显的编委会、目录和更正记录，排除过程见 excluded.json；规则不保证识别全部非研究论文。",
              "- journal_issn 按确定的期刊 ISSN 限定来源，并核验每条结果的 ISSN；期刊范围只适合作为学科范围的近似。",
              "- 不同期刊不代表一定属于不同学科；本实验不据此计算学科分类准确率或召回率。",
              "- 没有提供全库随机对照，也没有建立人工标注真值；10 条样本仅验证请求及返回字段。",
              "- Crossref 官方已宣布移除原 subject 分类值。参数探测和样本字段需结合官方说明解释，不能仅凭样本推断全库。",
              "- 若需要论文级学科，后续可按 DOI 补充其他来源的主题分类，或建立人工审核／文本分类；须单独记录分类来源。", "",
              "## 5. 依据", ""]
    lines.extend(f"- [{key}]({url})" for key, url in SOURCES.items())
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", default="software engineering")
    parser.add_argument("--query-field", choices=("title", "bibliographic"), default="title")
    parser.add_argument("--issn", default="0098-5589", help="Default: IEEE Transactions on Software Engineering")
    parser.add_argument("--count", type=int, default=10, help="Total unique records across both methods (2-100)")
    parser.add_argument("--from-date", default="2024-01-01")
    parser.add_argument("--until-date", default=datetime.now(timezone(timedelta(hours=8))).date().isoformat())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not args.query.strip():
        parser.error("--query must not be empty")
    if not 2 <= args.count <= 100:
        parser.error("--count must be between 2 and 100")
    if not re.fullmatch(r"\d{4}-\d{3}[\dXx]", args.issn):
        parser.error("--issn must look like 0098-5589")
    try:
        if date.fromisoformat(args.from_date) > date.fromisoformat(args.until_date):
            parser.error("--from-date must not be after --until-date")
    except ValueError:
        parser.error("Dates must be valid YYYY-MM-DD dates")
    output = args.output or ROOT / "data" / ("crossref_probe_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    output.mkdir(parents=True, exist_ok=False)  # Preserve earlier experimental evidence.
    print(f"Output: {output.resolve()}", flush=True)
    probes = []
    for label, filter_value in (("01_subject_filter", "subject:Software"),
                                ("02_category_filter", "category-name:Software")):
        response = get_json("/works", {"filter": filter_value, "rows": 0}, output, label)
        message = response["response"].get("message")
        probes.append({"filter": filter_value, "http_status": response["http_status"],
                       "total_results": message.get("total-results") if isinstance(message, dict) else None,
                       "file": f"{label}.json"})
        time.sleep(1)

    filters = f"type:journal-article,from-pub-date:{args.from_date},until-pub-date:{args.until_date}"
    batches = [
        ("keyword", "/works", {"filter": filters, f"query.{args.query_field}": args.query,
                                "sort": "score", "order": "desc"}, args.count // 2),
        ("journal_issn", f"/journals/{args.issn}/works", {"filter": filters,
                                                        "sort": "published", "order": "desc"},
         args.count - args.count // 2),
    ]
    records, seen, excluded = [], set(), []
    for method, endpoint, params, count in batches:
        collected, offset = 0, 0
        while collected < count and offset < args.count * 5:
            label = f"{method}_{offset:03d}"
            response = get_json(endpoint, {**params, "rows": count - collected, "offset": offset}, output, label)
            if response["http_status"] != 200 or response["response"].get("status") != "ok":
                raise RuntimeError(f"Collection failed; see {output / (label + '.json')}")
            items = response["response"]["message"]["items"]
            if not items:
                break
            for item in items:
                doi = item.get("DOI", "").strip().lower()
                if not doi or item.get("type") != "journal-article":
                    raise RuntimeError("Missing DOI or wrong work type in response")
                if method == "journal_issn" and args.issn.upper() not in [x.upper() for x in item.get("ISSN", [])]:
                    raise RuntimeError(f"ISSN mismatch for {doi}")
                reason = exclusion_reason(item)
                if reason or doi in seen:
                    excluded.append({"doi": doi, "title": item.get("title", []), "method": method,
                                     "reason": reason or "duplicate_doi", "evidence_file": label + ".json"})
                    write_json(output / "excluded.json", excluded)
                    continue
                if doi not in seen:
                    seen.add(doi)
                    records.append(summary(item, method, label + ".json"))
                    collected += 1
            offset += len(items)
            time.sleep(1)
        if collected != count:
            raise RuntimeError(f"Only collected {collected}/{count} unique records for {method}")
    manifest = {
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "query": args.query, "query_field": args.query_field,
        "issn": args.issn, "from_date": args.from_date,
        "until_date": args.until_date, "count": len(records), "filter_probes": probes,
        "excluded_count": len(excluded),
        "subject_states": dict(Counter(r["subject_field_state"] for r in records)),
        "sources": SOURCES,
    }
    write_json(output / "manifest.json", manifest)
    write_json(output / "papers.json", records)
    write_json(output / "excluded.json", excluded)
    (output / "report.md").write_text(render_report(manifest, records), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2), flush=True)
    print(f"Report: {output.resolve() / 'report.md'}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, KeyError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
