# Crossref 指定学科论文采集实验

本仓库还完成了[专利、科研项目及获奖数据源实测](docs/非论文成果数据源实测.md)，包含原指定来源各 10 条、补充专利 10 条，以及可统一展示的 [30 条数据](data/public_outcomes_probe_2026-10-01/unified_outcomes.json)。

实验日期：2026-10-01；工作分支：`investigation`。本实验调用 Crossref 官方 REST API，获取文章元数据，没有下载论文 PDF。

## 结论

**可以围绕指定领域定向采集，结果不必全学科混杂；但不能依赖 Crossref 原生学科标签，直接精确筛出某学科的全部论文。**

Crossref 已停用原有 `subject` 分类数据。该数据原先来自期刊／会议录层面的 ASJC 分类，并不是逐篇论文的学科判定；官方说明其覆盖、准确性和更新都有问题，因此移除了分类值。[停用公告](https://www.crossref.org/blog/subject-codes-incomplete-and-unreliable-have-got-to-go/)。Crossref 工作人员进一步确认停用日期为 **2024-04-23**。[官方论坛答复](https://community.crossref.org/t/get-works-by-category-name/5799)

对这个平台，有两种不同的目标：

| 目标 | 可行做法 | 不能据此保证的事 |
|---|---|---|
| 收集软件工程领域的一批候选论文 | 选定相关期刊的 ISSN，逐刊调用 `/journals/{issn}/works`；本次已验证 | 覆盖整个学科；每篇文章的唯一学科归属 |
| 搜索涉及某研究主题的文章 | 用标题关键词检索，再审查候选结果；本次已验证 | 关键词命中就是学科分类；结果全是研究论文 |
| 给平台每篇成果提供可靠学科标签 | 建立平台分类体系，由人工审核或另外的分类来源提供标签，并记录依据 | Crossref 会直接提供可用的 `subject` |

按 ISSN 限定刊物是 API 支持的准确来源筛选方式。[Crossref 过滤器说明](https://www.crossref.org/documentation/retrieve-metadata/rest-api/rest-api-filters/)。把该刊物映射为“软件工程领域候选来源”，则是平台自己的采集规则，应与论文的正式学科标签分开。

## 实际请求与结果

共同限制：`type:journal-article`，出版日期 `2024-01-01` 至 `2026-10-01`。未使用 `select` 裁剪返回字段，因此这里的 `subject` 缺失并非由选择字段造成。

### 第一次：验证宽泛检索的噪声

用 `query.bibliographic=software engineering` 取相关度最高的 5 条，再按 ISSN 取 5 条。[第一轮记录](data/crossref_probe_2026-10-01/report.md)

关键词组的 5 条都来自 *Advances in Engineering Software*，其中 **4 条标题是 Editorial Board**，上游仍将它们标成 `journal-article`。这一轮保留为原始反例，不把这些编委会条目当成研究论文。它说明：

- 书目关键词检索可能因为期刊名称相关而命中记录。
- `type:journal-article` 不能单独保证结果是研究论文。
- 本轮并未出现“关键词结果来自不同期刊”的现象，不能这样解读本轮数据。

### 第二次：标题检索与精确期刊范围对比

将关键词字段改为 `query.title`，并在脚本中增加明显非论文标题排除规则。实际得到 **10 条不同 DOI 的期刊文章元数据**，此次没有触发排除规则。[第二轮完整记录及 10 条清单](data/crossref_title_probe_2026-10-01/report.md)

| 检查项 | 实际结果 | 含义 |
|---|---|---|
| `filter=subject:Software&rows=0` | HTTP 400，`filter-not-available` | 该筛选参数无效，不是“软件领域没有论文” |
| `filter=category-name:Software&rows=0` | HTTP 200，`total-results=0` | 旧分类过滤无可用结果；结合官方停用说明解释 |
| 标题关键词 `software engineering` | 5 条，来自 5 种刊物 | 可以定向找主题，但范围跨刊物 |
| 期刊 ISSN `0098-5589` | 5 条，全部来自 *IEEE Transactions on Software Engineering* | 可以准确控制来源范围 |
| 10 条记录的 `subject` | 10 条均缺失字段 | 本批数据无法直接提取 Crossref 学科标签 |
| 10 条记录的摘要 | 4 条有摘要，6 条无摘要 | 后续分类不能假设每条都有摘要 |

标题检索的样本中，*Practical software engineering for software-writing scientists* 刊于 *The Journal of Chemical Physics*。标题与软件工程相关，刊物却面向化学物理，说明“主题相关”与“刊物所属领域”可以交叉，不能仅因跨刊就认定检索错误。

限定期刊的样本包括：

- *Characterizing Tests in IoT Software: Practices, Challenges and Opportunities*，DOI `10.1109/tse.2026.3700841`。
- *LongTest: Test Prioritization for Long Text Files*，DOI `10.1109/tse.2026.3703637`。
- *MORTAR: Multi-Turn Metamorphic Testing for LLM-Based Dialogue Systems*，DOI `10.1109/tse.2026.3701230`。

这些结果验证了定向采集路径，不构成学科分类准确率评估。样本未逐篇核验全文及文献体裁，不能声称全部都是原创研究论文；两轮里的期刊组相同，不能把两轮 20 条输出称为 20 篇不同论文。第二轮包含 10 个不同 DOI，跨两轮共 15 个不同 DOI。

## 运行脚本

使用 Python 3.10 或以上版本，仅依赖标准库。在本仓库目录运行：

```powershell
python .\scripts\crossref_discipline_probe.py --count 10
```

默认参数：标题关键词 `software engineering`；期刊 ISSN `0098-5589`；起始日期 `2024-01-01`；结束日期为运行当天（北京时间）。`--count 10` 表示两组总计 10 条，默认各 5 条。

复跑本次时间范围：

```powershell
python .\scripts\crossref_discipline_probe.py --query-field title --query "software engineering" --issn 0098-5589 --count 10 --from-date 2024-01-01 --until-date 2026-10-01
```

也可以用 `--query-field bibliographic` 比较书目检索，但当前版本会排除明显的编委会等记录，不会原样复现第一轮的未清洗输出。服务数据与相关度排序会变化，即使参数相同，也不保证以后返回同一批 DOI。

`--query` 和 `--issn` 独立配置；换研究领域时应同时更改关键词及相应刊物 ISSN。脚本不会从中文学科名称自动推断 ISSN，也不会自动建立学科分类。

输出默认写入 `data/` 下的新时间戳目录，也可用 `--output` 指定**尚不存在**的目录：

| 文件 | 内容 |
|---|---|
| `01_subject_filter.json`、`02_category_filter.json` | 学科筛选探测请求、HTTP 状态、原始响应 |
| `keyword_*.json`、`journal_issn_*.json` | 每批请求参数、抓取时间、HTTP 状态及完整 JSON 响应 |
| `papers.json` | 选中记录的 DOI、标题、刊物、ISSN、日期、摘要存在情况、subject 状态及证据文件 |
| `excluded.json` | 被跳过的明显非论文记录或重复 DOI，以及原因；第二轮为空列表 |
| `manifest.json` | 参数、完成时间、统计及官方说明链接 |
| `report.md` | 可阅读的结果表和解释边界 |

脚本串行请求，正常请求间隔 1 秒，单次超时 25 秒；对网络异常及部分临时错误最多尝试 3 次。小样本补抓设有上限，不会无限翻页。可通过环境变量 `CROSSREF_MAILTO` 提供自己的联系邮箱；未配置时使用公共访问池，本次未提供邮箱。公共 API 无需注册，联系信息用于 polite pool。[访问说明](https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication/)

这是小样本探测工具，不是全量同步任务。正式批量采集应使用 cursor 分页，并另做断点恢复和增量同步。[Crossref 采集建议](https://www.crossref.org/documentation/retrieve-metadata/rest-api/tips-for-using-the-crossref-rest-api/)

## 对平台需求的影响

建议课程项目先采用“领域相关期刊清单 → Crossref 题录 → DOI 去重 → 候选学科 → 人工确认”的范围受控流程。期刊清单需要明确名称、ISSN、候选领域和选择依据；本实验只验证了 1 种期刊，不代表已完成整个学科的来源清单。

既有需求中的 `subject/标签`、学科筛选、学科统计可以保留，但必须明确字段来源：**不能再把 Crossref `subject` 视作‘有时缺失、其余可直接用于学科统计’的正常输入。** 本结论修正此前调研中对该字段的可用性预期。

建议将采集范围与正式分类分开保存：

- `collection_scope`：本次属于哪个期刊或主题采集任务。
- `discipline_labels`：平台已确认的学科标签；没有依据时为空。
- `classification_source`、`classification_version`：标签的来源和版本。
- `classification_status`：未分类、候选或已确认；本实验统一保留 `not_classified`。

统计时区分“按来源清单采集的文章”与“已确认属于某学科的文章”，同时展示未分类数量。这样既能获得方向集中的数据，也能避免给所有采集结果强行贴上同一个学科标签。
