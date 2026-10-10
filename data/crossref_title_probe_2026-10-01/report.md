# Crossref 学科定向采集：实际请求记录

- 请求完成时间（UTC）：2026-10-01T12:58:57.610957+00:00
- 关键词：`software engineering`；限定期刊 ISSN：`0098-5589`。
- 关键词请求字段：`query.title`；明显非论文记录排除数：0。
- 出版日期范围：2024-01-01 至 2026-10-01。
- 保存 10 条不同 DOI 的期刊文章元数据，未下载论文全文。

## 1. 学科过滤参数探测

以下请求使用 rows=0，只检查过滤器响应，不额外采集文章。400 表示参数无效，不能解释为该学科没有论文；旧分类过滤返回 0 也不能推断该领域无论文。

| 参数 | HTTP | total-results | 响应文件 |
|---|---:|---:|---|
| `subject:Software` | 400 | None | [01_subject_filter.json](01_subject_filter.json) |
| `category-name:Software` | 200 | 0 | [02_category_filter.json](02_category_filter.json) |

## 2. 定向采集比较

| 方法 | 条数 | subject 非空 | subject 空值 | subject 缺失 | 不同期刊数 |
|---|---:|---:|---:|---:|---:|
| keyword | 5 | 0 | 0 | 5 | 5 |
| journal_issn | 5 | 0 | 0 | 5 | 1 |

## 3. 采集到的文章

| 方法 | 标题 | 期刊 | DOI | subject 状态 |
|---|---|---|---|---|
| keyword | Research Software Engineering | Forschung &amp; Lehre | [10.37307/j.0945-5604.2024.03.12](https://doi.org/10.37307/j.0945-5604.2024.03.12) | missing |
| keyword | Practical software engineering for software-writing scientists | The Journal of Chemical Physics | [10.1063/5.0293841](https://doi.org/10.1063/5.0293841) | missing |
| keyword | Software Product Line Engineering via Software Transplantation | ACM Transactions on Software Engineering and Methodology | [10.1145/3695987](https://doi.org/10.1145/3695987) | missing |
| keyword | Automated quantum software engineering | Automated Software Engineering | [10.1007/s10515-024-00436-x](https://doi.org/10.1007/s10515-024-00436-x) | missing |
| keyword | Women and Software Engineering | ACM SIGSOFT Software Engineering Notes | [10.1145/3650142.3650147](https://doi.org/10.1145/3650142.3650147) | missing |
| journal_issn | Characterizing Tests in IoT Software: Practices, Challenges and Opportunities | IEEE Transactions on Software Engineering | [10.1109/tse.2026.3700841](https://doi.org/10.1109/tse.2026.3700841) | missing |
| journal_issn | LongTest: Test Prioritization for Long Text Files | IEEE Transactions on Software Engineering | [10.1109/tse.2026.3703637](https://doi.org/10.1109/tse.2026.3703637) | missing |
| journal_issn | MORTAR: Multi-Turn Metamorphic Testing for LLM-Based Dialogue Systems | IEEE Transactions on Software Engineering | [10.1109/tse.2026.3701230](https://doi.org/10.1109/tse.2026.3701230) | missing |
| journal_issn | Boosting High-Review-Value Warning Line Identification With Unsupervised Line-Level Defect Prediction | IEEE Transactions on Software Engineering | [10.1109/tse.2026.3704180](https://doi.org/10.1109/tse.2026.3704180) | missing |
| journal_issn | No Resource, No Benchmarks, No Problem? Evaluating and Improving LLMs for Code Generation in No-Resource Languages | IEEE Transactions on Software Engineering | [10.1109/tse.2026.3703553](https://doi.org/10.1109/tse.2026.3703553) | missing |

## 4. 解释边界

- keyword 使用 query.title 按相关度检索；命中关键词并不等于获得文章级学科分类。
- 按标题规则排除明显的编委会、目录和更正记录，排除过程见 excluded.json；规则不保证识别全部非研究论文。
- journal_issn 按确定的期刊 ISSN 限定来源，并核验每条结果的 ISSN；期刊范围只适合作为学科范围的近似。
- 不同期刊不代表一定属于不同学科；本实验不据此计算学科分类准确率或召回率。
- 没有提供全库随机对照，也没有建立人工标注真值；10 条样本仅验证请求及返回字段。
- Crossref 官方已宣布移除原 subject 分类值。参数探测和样本字段需结合官方说明解释，不能仅凭样本推断全库。
- 若需要论文级学科，后续可按 DOI 补充其他来源的主题分类，或建立人工审核／文本分类；须单独记录分类来源。

## 5. 依据

- [subject_deprecation](https://www.crossref.org/blog/subject-codes-incomplete-and-unreliable-have-got-to-go/)
- [deprecation_confirmation](https://community.crossref.org/t/get-works-by-category-name/5799)
- [filters](https://www.crossref.org/documentation/retrieve-metadata/rest-api/rest-api-filters/)
- [queries](https://api.crossref.org/)
