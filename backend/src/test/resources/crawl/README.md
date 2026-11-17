# Registered-source parser fixtures

These are frozen public official-source documents downloaded once on **2026-11-17** for offline parser correctness tests. Tests do not contact their publishers or run load tests. HTML files are stored as UTF-8 without BOM; the PDF is the original response bytes. Original pages and checksums can be independently checked. A complete document is retained because table headings, nested layout tables, award grades and PDF page boundaries are part of the parsing contract.

| Fixture | Official source | Expected source rows | SHA-256 |
|---|---|---:|---|
| `lynu-2025.html` | [洛阳师范学院：2025年获得授权的专利清单](https://sites.lynu.edu.cn/kycx/info/1221/5141.htm) | 28 | `C2AAA105BAB480F1D31A862FE0FD76FBF82F85A39B9188F57B25F8354F16560E` |
| `nsfc-2019.html` | [国家自然科学基金委员会：2019年生命科学部重点项目资助清单](https://www.nsfc.gov.cn/p1/2853/3102/72645.html) | 115 | `FC657B7EB9DF2E9A6DC3C98F7BA8ECFF06742DF935D2D29D5C2928D4A95DE337` |
| `most-2023.html` | [科技部：2023年度国家自然科学奖获奖项目目录](https://www.most.gov.cn/cxfw/kjjlcx/kjjl2023/202406/t20240624_191176.html) | 49 (1 first-prize + 48 second-prize) | `31381F40170382D9982A833E34A5A35F4D0FDFF211B7B6F91AC21825450567B5` |
| `cnipa-25-gold.pdf` | [国家知识产权局：第二十五届中国专利金奖项目名单](https://www.cnipa.gov.cn/module/download/downfile.jsp?classid=0&showname=%E7%AC%AC%E4%BA%8C%E5%8D%81%E4%BA%94%E5%B1%8A%E4%B8%AD%E5%9B%BD%E4%B8%93%E5%88%A9%E9%87%91%E5%A5%96%E9%A1%B9%E7%9B%AE%E5%90%8D%E5%8D%95.pdf&filename=b712cad8dee344bc8322b4b45291fdf0.pdf) | 30 across 4 pages | `465DF4B59B7CD19A9938DE94679DD0EF8364A67C650D470EE985D4CA7DB3FF74` |

Business semantics asserted by tests:

- LYNU application and grant dates differ from its page publication date. No rights holder or inventor institution is asserted by the source table.
- NSFC “科学部编号” is retained as a department number, not relabeled as an approval number. Direct funding is in 10,000 CNY units; the project year is 2019, not the 2020 publication year.
- MOST principal awardees, their stated institutions, grade and nominator are separate fields. Nominators never become awardees.
- CNIPA uses the `ZL` patent number prefix in its list. Canonical application identifiers use `CN` while raw numbers remain available. The attachment has no application/grant dates or current legal-status determination; those values remain unknown.
- Publisher text supplies no account identity verification. Person and institution IDs remain unassigned, and source publication dates are not treated as record update timestamps.

Generated malformed cases in Java tests alter the frozen HTML in memory or construct small local PDFs; they are test cases, not additional source data.
