"""Check the report structure and worked examples, not the unimplemented system."""
import json
import math
import re
from collections import Counter
from pathlib import Path

report = Path(__file__).resolve().parents[1] / "汇报成果" / "学术成果分享平台_详细设计与实现方案汇报.md"
body = report.read_text(encoding="utf-8")
assert body.count("```") % 2 == 0, "Unclosed fenced block"
for sample in re.findall(r"```json\n(.*?)\n```", body, re.S):
    json.loads(sample)
assert re.findall(r"^## (\d+)\.", body, re.M) == [str(n) for n in range(1, 22)]
minutes = re.findall(r"^### 第\d+段：.*?（(\d+)分钟", body, re.M)
assert len(minutes) == 8 and sum(map(int, minutes)) == 15

table_sizes = []
for line in body.splitlines():
    if line.startswith("|"):
        size = len(re.split(r"(?<!\\)\|", line))
        if table_sizes:
            assert size == table_sizes[-1], f"Broken table: {line}"
        table_sizes.append(size)
    else:
        table_sizes.clear()

papers = {
    "R01": {"A01": {"I01"}, "A03": {"I01"}},
    "R02": {"A02": {"I02"}},
    "R03": {"A01": {"I03"}, "A04": {"I03"}},
    "R04": {"A01": {"I01"}, "A03": {"I01"}},
    "R05": {"A03": {"I01"}},
    "R06": {"A01": {"I03"}, "A03": {"I01"}},
    "R07": {"A01": {"I01"}},
    "R08": {"A04": {"I03"}},
}
same_author_org = {key for key, people in papers.items() if "I01" in people.get("A01", set())}
any_author_org = {key for key, people in papers.items() if "A01" in people and any("I01" in orgs for orgs in people.values())}
assert same_author_org == {"R01", "R04", "R07"}
assert any_author_org == {"R01", "R04", "R06", "R07"}
assert {key for key, people in papers.items() if {"A01", "A03"} <= people.keys()} == {"R01", "R04", "R06"}
counts = Counter(org for people in papers.values() for org in set().union(*people.values()))
assert counts == {"I01": 5, "I02": 1, "I03": 3}
assert len(papers) == 8 and sum(counts.values()) == 9
assert 8 + 1 + 2 + 2 == 13
assert math.isclose(.55 * .98 + .2 + .1 + .1, .939)
r_text = .45 * .9 + .20 * .6 + .15 * .8 + .10 * .2 + .05 * 0 + .05 * .4
assert math.isclose(r_text, .685)
assert math.isclose(.8 * r_text + .1 * .7 + .05 * .78 + .05 * .75, .6945)
assert math.isclose(.3 + .15 * .1 + .05, .365)
assert "不代表系统已经编码" in body
print(f"PASS: 21 sections, 8 segments/15 minutes, JSON and tables, worked scores and sample counts; {len(body):,} characters")
