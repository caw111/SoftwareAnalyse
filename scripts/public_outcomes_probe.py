"""Fetch and inspect official Chinese patent, project and award samples.

Requires Python >= 3.10 and pypdf. Public pages only; no login automation.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "patent_notice": "https://www.cnipa.gov.cn/art/2025/6/5/art_552_199973.html",
    "project_list": "https://www.nsfc.gov.cn/p1/2853/3102/72645.html",
    "award_list": "https://www.most.gov.cn/cxfw/kjjlcx/kjjl2023/202406/t20240624_191176.html",
    "patent_search": "https://pss-system.cponline.cnipa.gov.cn/conventionalSearch",
    "project_search": "https://kd.nsfc.cn/",
    "patent_supplement": "https://sites.lynu.edu.cn/kycx/info/1221/5141.htm",
}


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class Node:
    def __init__(self, tag="root", attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []

    def text(self):
        return "".join(c if isinstance(c, str) else c.text() for c in self.children)

    def find_all(self, tag):
        result = []
        for child in self.children:
            if isinstance(child, Node):
                if child.tag == tag:
                    result.append(child)
                result.extend(child.find_all(tag))
        return result


class Document(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag == "br":
            node.children.append("\n")
        if tag not in {"meta", "link", "img", "input", "br", "hr", "source", "wbr", "area", "base", "embed", "param", "col"}:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                if tag in {"p", "div", "tr", "h1", "h2"}:
                    self.stack[index].children.append("\n")
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def fetch(url: str, output: Path, label: str, suffix="html") -> dict:
    raw_dir = output / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    evidence = raw_dir / f"{label}.request.json"
    if evidence.exists():
        saved = json.loads(evidence.read_text(encoding="utf-8"))
        if saved.get("file"):
            actual = hashlib.sha256((output / saved["file"]).read_bytes()).hexdigest()
            if actual != saved["sha256"] or saved["url"] != url:
                raise RuntimeError(f"Cached evidence mismatch: {label}")
        print(f"CACHE {label}: HTTP {saved['http_status']}", flush=True)
        return saved
    info = {"url": url, "fetched_at_utc": datetime.now(timezone.utc).isoformat()}
    print(f"GET {label}: {url}", flush=True)
    try:
        request = Request(url, headers={"User-Agent": "AcademicPlatform-PublicOutcomesProbe/0.1"})
        try:
            with urlopen(request, timeout=20) as response:
                data = response.read(12 * 1024 * 1024 + 1)
                info.update(http_status=response.status, final_url=response.url,
                            content_type=response.headers.get("Content-Type", ""))
        except HTTPError as error:
            data = error.read(12 * 1024 * 1024 + 1)
            info.update(http_status=error.code, final_url=error.url,
                        content_type=error.headers.get("Content-Type", ""))
        if len(data) > 12 * 1024 * 1024:
            raise RuntimeError("Response exceeds 12 MiB sample limit")
        path = raw_dir / f"{label}.{suffix}"
        path.write_bytes(data)
        info.update(file=str(path.relative_to(output)).replace("\\", "/"),
                    bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    except (URLError, OSError, RuntimeError) as error:
        info.update(http_status=None, error=str(error))
    write_json(raw_dir / f"{label}.request.json", info)
    print(f"{label}: HTTP {info['http_status']}, bytes={info.get('bytes', 0)}", flush=True)
    time.sleep(1)
    return info


def read_html(output: Path, label: str) -> Document:
    data = (output / "raw" / f"{label}.html").read_bytes()
    match = re.search(rb"charset\s*=\s*['\"]?([\w-]+)", data[:6000], re.I)
    encoding = match.group(1).decode("ascii") if match else "utf-8"
    return Document(data.decode(encoding))


def fetch_sources(output: Path, resume=False) -> None:
    output.mkdir(parents=True, exist_ok=resume)
    for label in ("award_list", "project_list", "patent_notice"):
        info = fetch(SOURCES[label], output, label)
        if info["http_status"] != 200:
            raise RuntimeError(f"Cannot fetch {label}; evidence retained")
    document = read_html(output, "patent_notice")
    links = [node.attrs["href"] for node in document.root.find_all("a")
             if "第二十五届中国专利金奖项目名单" in node.text() and "href" in node.attrs]
    if len(links) != 1:
        raise RuntimeError("Cannot identify the patent attachment unambiguously")
    info = fetch(urljoin(SOURCES["patent_notice"], links[0]), output, "patent_list", "pdf")
    if info["http_status"] != 200:
        raise RuntimeError("Cannot fetch patent attachment; evidence retained")
    for label in ("patent_search", "project_search"):
        fetch(SOURCES[label], output, label)
    info = fetch(SOURCES["patent_supplement"], output, "patent_supplement")
    if info["http_status"] != 200:
        raise RuntimeError("Cannot fetch the supplementary patent list")


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def table_rows(document: Document):
    for row in document.root.find_all("tr"):
        cells = [child for child in row.children if isinstance(child, Node) and child.tag in {"td", "th"}]
        yield [clean(cell.text()) for cell in cells]


def publication_date(document: Document) -> str:
    for node in document.root.find_all("meta"):
        if node.attrs.get("name", "").lower() == "pubdate":
            return datetime.strptime(node.attrs["content"][:10], "%Y-%m-%d").date().isoformat()
    match = re.search(r"(?:日期[：:]?\s*)?(20\d{2}-\d{2}-\d{2})", document.root.text())
    if not match:
        raise ValueError("Missing source publication date")
    return datetime.strptime(match[1], "%Y-%m-%d").date().isoformat()


def base_record(output, kind, identifier, title, contributors, date_value, date_kind,
                date_precision, label, source_name, source_date, locator, raw_cells):
    request = json.loads((output / "raw" / f"{label}.request.json").read_text(encoding="utf-8"))
    return {
        "id": f"{kind}:{identifier}", "type": kind, "title": title,
        "authors": [person["name"] for person in contributors], "contributors": contributors,
        "date": date_value, "date_kind": date_kind, "date_precision": date_precision,
        "source_record_id": identifier, "source_name": source_name, "source_url": request["url"],
        "source_published_date": source_date, "fetched_at_utc": request["fetched_at_utc"],
        "evidence": {"file": request["file"], "sha256": request["sha256"],
                     "locator": locator, "raw_cells": raw_cells},
        "missing_fields": [], "details": {},
    }


def parse_projects(output: Path, count: int) -> list:
    doc = read_html(output, "project_list")
    title = next(node.text() for node in doc.root.find_all("title"))
    year = re.search(r"(20\d{2})年生命科学部重点项目资助清单", title)[1]
    records = []
    for cells in table_rows(doc):
        if len(cells) != 6 or not re.fullmatch(r"\d{10}", cells[1]):
            continue
        sequence, code, title, person, org, money = cells
        record = base_record(output, "project", code, title,
                             [{"name": person, "role": "principal_investigator", "role_label": "项目负责人", "affiliation": org}],
                             year, "funding_year", "year", "project_list", "国家自然科学基金委员会", publication_date(doc),
                             {"table_row_number": int(sequence)}, cells)
        record["details"] = {"division_number": code, "identifier_label": "科学部编号",
                             "host_institution": org, "funding_year": int(year),
                             "direct_cost_10k_cny": float(money), "project_start_date": None,
                             "project_end_date": None, "project_status": "not_verified"}
        record["missing_fields"] = ["project_start_date", "project_end_date", "full_team", "current_project_status"]
        records.append(record)
        if len(records) == count:
            break
    return records


def parse_awards(output: Path, count: int) -> list:
    doc = read_html(output, "award_list")
    page_title = next(node.text() for node in doc.root.find_all("title"))
    year = re.search(r"(20\d{2})年度国家自然科学奖", page_title)[1]
    records = []
    for cells in table_rows(doc):
        if len(cells) != 5 or not re.fullmatch(r"Z-\d{3}-[12]-\d{2}", cells[1]):
            continue
        sequence, code, title, people, nominator = cells
        # These first ten rows have one unnested institution parenthesis per person.
        matches = list(re.finditer(r"([^（）]+)（([^（）]+)）", people))
        remainder = re.sub(r"([^（）]+)（([^（）]+)）", "", people)
        if clean(remainder) or not matches:
            raise ValueError(f"Ambiguous award contributor layout: {code}")
        contributors = [{"name": re.sub(r"\s+", "", m[1]), "role": "award_contributor",
                         "role_label": "主要完成人", "affiliation": clean(m[2])} for m in matches]
        record = base_record(output, "award", f"{year}:{code}", title, contributors,
                             year, "award_year", "year", "award_list", "中华人民共和国科学技术部", publication_date(doc),
                             {"project_code": code, "table_row_number": int(sequence)}, cells)
        record["details"] = {"award_name": "国家自然科学奖", "award_year": int(year), "project_code": code,
                             "award_grade": "一等奖" if code.split("-")[2] == "1" else "二等奖",
                             "nominator": nominator, "award_ceremony_date": None}
        record["missing_fields"] = ["award_ceremony_date"]
        records.append(record)
        if len(records) == count:
            break
    return records


def parse_cnipa_patents(output: Path, count: int) -> list:
    from pypdf import PdfReader
    doc = read_html(output, "patent_notice")
    source_date = publication_date(doc)
    reader = PdfReader(output / "raw" / "patent_list.pdf")
    records = []
    extracted_rows = []
    for page_number, page in enumerate(reader.pages, 1):
        rectangles, fragments = [], []
        def before(operator, operands, cm, tm):
            if operator == b"re":
                rectangles.append(tuple(float(value) for value in operands))
        def visitor(text, cm, tm, font, size):
            if text.strip():
                fragments.append((float(tm[4]), float(tm[5]), text))
        page.extract_text(visitor_operand_before=before, visitor_text=visitor)
        # This PDF paints/clips each cell in the same coordinates as the text.
        # Use the actual row rectangles, not whitespace or guessed row heights.
        row_bounds = sorted({(y, height) for x, y, width, height in rectangles
                             if 60 < x < 70 and 35 < width < 45 and height > 15})
        for top, height in row_bounds:
            cell_bounds = sorted({(x, width) for x, y, width, h in rectangles
                                  if abs(y - top) < .01 and abs(h - height) < .01 and 60 < x < 750})
            if len(cell_bounds) != 5:
                raise ValueError(f"Unexpected PDF columns on page {page_number}")
            cells = []
            for left, width in cell_bounds:
                parts = [(x, y, text) for x, y, text in fragments
                         if left <= x < left + width and top <= y < top + height]
                parts.sort(key=lambda part: (round(part[1], 1), part[0]))
                cells.append("".join(text.strip() for _, _, text in parts))
            if not re.fullmatch(r"ZL\d{12}\.[\dX]", cells[1]):
                continue  # Repeated table headers.
            sequence, code, title, owners, people = cells
            if not sequence.isdigit() or int(sequence) != len(records) + 1:
                raise ValueError("Patent PDF row order is inconsistent")
            contributors = [{"name": clean(name), "role": "inventor", "role_label": "发明人", "affiliation": None}
                            for name in people.split("、") if clean(name)]
            record = base_record(output, "patent", code, title, contributors, None, "grant_date", None,
                                 "patent_list", "国家知识产权局公开专利奖名单", source_date,
                                 {"page": page_number, "table_row_number": int(sequence)}, cells)
            record["details"] = {"patent_number": code, "patent_owners": owners.split("、"),
                                 "application_date": None, "grant_date": None,
                                 "current_legal_status": "not_verified", "selection_scope": "第二十五届中国专利金奖名单"}
            record["missing_fields"] = ["application_date", "grant_date", "current_legal_status"]
            record["related_notice_url"] = SOURCES["patent_notice"]
            record["date_warning"] = "目录发布日期不等于专利申请日或授权日；date 保持 null"
            records.append(record)
            extracted_rows.append({"page": page_number, "row": int(sequence), "cells": cells})
            if len(records) == count:
                write_json(output / "patent_pdf_extracted_rows.json", extracted_rows)
                return records
    return records


def parse_supplementary_patents(output: Path, count: int) -> list:
    doc = read_html(output, "patent_supplement")
    records = []
    for cells in table_rows(doc):
        if len(cells) != 7 or not re.fullmatch(r"CN\d{12}\.[\dX]", cells[1]):
            continue
        sequence, code, subtype, title, application_date, grant_date, people = cells
        application_date = datetime.strptime(application_date, "%Y%m%d").date().isoformat()
        grant_date = datetime.strptime(grant_date, "%Y%m%d").date().isoformat()
        if application_date > grant_date:
            raise ValueError(f"Invalid date order for {code}")
        contributors = [{"name": clean(name), "role": "inventor", "role_label": "发明人", "affiliation": None}
                        for name in re.split(r"[;；]", people) if clean(name)]
        record = base_record(output, "patent", code, title, contributors, grant_date, "grant_date", "day",
                             "patent_supplement", "洛阳师范学院科研处（补充来源）", publication_date(doc),
                             {"table_row_number": int(sequence)}, cells)
        record["details"] = {"application_number": code, "patent_subtype": subtype,
                             "application_date": application_date, "grant_date": grant_date,
                             "current_legal_status": "not_verified", "patent_owners": None}
        record["missing_fields"] = ["current_legal_status", "patent_owners"]
        record["supplementary_source"] = True
        records.append(record)
        if len(records) == count:
            break
    return records


def md_cell(value) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def parse_sources(output: Path, count: int) -> None:
    groups = {"patents_cnipa": parse_cnipa_patents(output, count),
              "projects": parse_projects(output, count), "awards": parse_awards(output, count),
              "patents_supplement": parse_supplementary_patents(output, count)}
    for label, records in groups.items():
        if len(records) != count or len({r["id"] for r in records}) != count:
            raise ValueError(f"Expected {count} unique {label} records; got {len(records)}")
        for record in records:
            if not record["title"] or not record["authors"] or any(not p for p in record["authors"]):
                raise ValueError(f"Required text field missing: {record['id']}")
            if label != "patents_cnipa" and not record["date"]:
                raise ValueError(f"Required outcome date missing: {record['id']}")
            evidence = output / record["evidence"]["file"]
            if hashlib.sha256(evidence.read_bytes()).hexdigest() != record["evidence"]["sha256"]:
                raise ValueError("Evidence hash mismatch")
        write_json(output / f"{label}.json", records)
    unified = groups["patents_supplement"] + groups["projects"] + groups["awards"]
    write_json(output / "unified_outcomes.json", unified)
    manifest = {"processed_at_utc": datetime.now(timezone.utc).isoformat(), "count_per_group": count,
                "sources": SOURCES, "groups": {}, "unified_count": len(unified),
                "unified_patent_source": "supplementary_university_list",
                "validation": "passed: counts, identifiers, required fields, evidence hashes"}
    manifest["search_entry_probes"] = {}
    for label in ("patent_search", "project_search"):
        info = json.loads((output / "raw" / f"{label}.request.json").read_text(encoding="utf-8"))
        manifest["search_entry_probes"][label] = {key: info.get(key) for key in ("url", "http_status", "file", "error")}
    for label, records in groups.items():
        manifest["groups"][label] = {"count": len(records), "with_title": sum(bool(r["title"]) for r in records),
                                     "with_authors": sum(bool(r["authors"]) for r in records),
                                     "with_outcome_date": sum(bool(r["date"]) for r in records),
                                     "with_source_date": sum(bool(r["source_published_date"]) for r in records)}
    write_json(output / "manifest.json", manifest)
    sampled_at = unified[0]["fetched_at_utc"][:10]
    lines = ["# 专利、科研项目、获奖：实际采集记录", "",
             f"采集日期（UTC）：{sampled_at}。各清单按原表顺序取前 {count} 条。",
             "原指定来源各保存一组；专利日期不足，另采高校补充组。所有字段来自保存的网页或附件，未手工编造记录。", "",
             "## 字段完整性", "", "| 来源组 | 条数 | 标题 | 人员 | 成果时间 | 网页发布日期 |",
             "|---|---:|---:|---:|---:|---:|"]
    for label, metrics in manifest["groups"].items():
        lines.append(f"| {label} | {metrics['count']} | {metrics['with_title']} | {metrics['with_authors']} | {metrics['with_outcome_date']} | {metrics['with_source_date']} |")
    lines += ["", f"unified_outcomes.json 使用高校专利补充组、基金委项目组和科技部获奖组，共 {len(unified)} 条。",
              "专利为授权日期；项目为资助年度；获奖为奖励年度。年度没有补成虚假的 1 月 1 日。", ""]
    for label, records in groups.items():
        lines += ["", f"## {label}", "", f"[JSON 数据]({label}.json)｜[原始来源]({records[0]['source_url']})", "",
                  "| 标题 | 人员及角色 | 成果时间 | 来源标识 |", "|---|---|---|---|"]
        for record in records:
            names = "、".join(record["authors"])
            role = record["contributors"][0]["role_label"]
            value = record["date"] or "缺失（不可用目录发布日期替代）"
            lines.append(f"| {md_cell(record['title'])} | {md_cell(role + '：' + names)} | {value} | {record['source_record_id']} |")
    lines += ["", "## 接入边界", "",
              f"- 国家知识产权局主检索 HTTP {manifest['search_entry_probes']['patent_search']['http_status']}；公开附件不含专利申请日和授权日。主检索响应见 raw/patent_search.html。",
              f"- NSFC 门户首页 HTTP {manifest['search_entry_probes']['project_search']['http_status']}；响应见 raw/project_search.html。本实验未实现或验证通用项目检索接口。",
              "- 项目样本来自 NSFC 官网上的 2019 年重点项目资助清单，不是结题报告；科学部编号按原名保留，不当作项目批准号。",
              "- 获奖样本为 2023 年度国家自然科学奖，网页发布于 2024-06-24，两种时间分别保存。",
              "- 高校专利清单是新增补充来源，不能声称这 10 条有授权日期的记录来自国家知识产权局主检索。",
              "- 发明人不等于专利权人；负责人不代表项目全体成员；主要完成人不包括提名者。",
              "- 此次验证有限公开目录的抽取能力，不证明全库、任意学科或任意年份均可抓取。", ""]
    (output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(manifest["groups"], ensure_ascii=True, indent=2), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fetch-only", action="store_true")
    parser.add_argument("--offline", action="store_true", help="Parse saved evidence without network access")
    parser.add_argument("--resume", action="store_true", help="Reuse saved evidence; fetch only missing sources")
    parser.add_argument("--count", type=int, default=10)
    args = parser.parse_args()
    if not 1 <= args.count <= 10:
        parser.error("--count must be between 1 and 10")
    if args.offline and args.fetch_only:
        parser.error("--offline cannot be combined with --fetch-only")
    if not args.offline:
        fetch_sources(args.output, args.resume)
    if not args.fetch_only:
        parse_sources(args.output, args.count)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
