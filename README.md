# 学术成果检索与分享平台

《软件系统分析与设计》课程项目。Group2 为实现与协作分支。第一版：**WPF 原生 Windows 桌面客户端 + Java 21 / Spring Boot 服务**。

## 运行第一版

在仓库根目录用 PowerShell 执行：

```powershell
.\scripts\start-local.ps1
```

默认使用 `D:\tool\java21`、`D:\tool\gradle\gradle-9.8.0` 和本机 .NET 9 SDK；首次构建需要下载依赖。脚本构建并启动本地 API，再打开 Windows 应用。**没有网页前端，也不使用 WebView。** 已构建后可运行 `./scripts/start-local.ps1 -NoBuild`。

本地默认 H2 文件库保存在 `backend/data/`，首启生成 64 条明确标注的模拟成果。已有数据库不重复初始化。API 默认为 `http://127.0.0.1:8080`，管理端口为 `127.0.0.1:8081`。切换服务器可在桌面右上角输入 HTTPS 地址，或设置环境变量 `ACADEMIC_API_URL`。登录令牌仅驻留内存。

| 演示账号 | 密码 | 能力 |
| --- | --- | --- |
| `researcher` | `DemoPass2026!` | 已认证科研人员，可申请门户、认领/撤销本人贡献 |
| `reader` | `DemoPass2026!` | 普通用户，可申请科研身份 |
| `admin` | `DemoPass2026!` | 审核、导入与审计 |

这些账号仅由 `APP_DEMO=true` 的空库初始化创建。生产使用**新的 PostgreSQL 数据库**、`APP_DEMO=false` 和至少 16 字符的 `ADMIN_PASSWORD`，只创建管理员。不要将含演示账号的数据库直接切到公网；关闭 demo 标志不会更改既有密码。

## 可以演示的流程

1. 访客检索四类成果，按类型/年份/人物 ID/历史署名机构/领域筛选，查看详情、来源和同版统计。
2. `researcher` 登录 → 学者门户 → 选择某位学者并填写证据 → 申请门户。
3. `admin` 登录 → 管理与审核 → 选择申请 → 领取审核 → 填写意见 → 通过、驳回或要求补充。
4. 科研人员重新登录/刷新工作台 → 在成果详情申请确认本人贡献。门户通过不会自动认领全部成果。
5. 两位真实贡献者可分别关联同一成果；撤销本人关联不会删除公共成果。
6. 管理员导入 `scripts/samples/import-demo.json`，再次导入同一批次不重复入库；重新检索查看新版本。
7. 共著路径选择两位已识别学者，查看最短路径和每条边的论文证据。

## 工程入口

| 路径 | 内容 |
| --- | --- |
| `frontend/AcademicDesktop/` | WPF 桌面程序、异步 API 客户端 |
| `backend/` | Gradle Java 21 工程、Flyway 迁移、后端 Dockerfile、自动化测试 |
| `scripts/build.ps1` | 构建后端和桌面端，默认跑功能测试 |
| `scripts/publish-desktop.ps1` | 打包自带运行时的 Windows x64 单文件 EXE |
| `scripts/stop-local.ps1` | 仅停止启动脚本记录且校验过的本项目 API |
| [架构决策](docs/architecture.md) | 一致性、技术选择、资源预算和实现边界 |
| [API 契约](docs/api.md) | 接口、授权、状态和版本语义 |
| [部署说明](docs/deployment.md) | Docker Compose / k3s / HPA / 备份 |
| [验证记录](docs/verification/first-version.md) | 本次真实构建、测试与未验证项 |
| [验收映射](docs/acceptance.md) | 已完成、部分完成和后续需求 |
| [服务器压测说明](scripts/performance/README.md) | 待服务器执行的 k6 脚本，默认 20 并发 / 5 分钟 |

运行 `./scripts/publish-desktop.ps1` 后，成品位于 `artifacts/windows-x64/AcademicDesktop.exe`。API JAR 位于 `backend/build/libs/academic-platform-api.jar`。构建产物不提交 Git。

**按用户要求，本机没有运行压测，也没有 P95 达标声明。** 本地仅运行功能测试和两个请求的竞争正确性检查；10,000 条模拟数据的存在不代表真实性验收或性能达标。真实联网采集、恢复式采集任务、纠错/归并治理、BM25 排序、P1 推荐与专题库见后续清单。

## 文档入口

| 目录 | 内容 |
| --- | --- |
| [需求调研和建模](前期成果/需求调研和建模/README.md) | 原仓库 SRS、SPEC、调研报告及可复用参考模型 |
| [需求分析](前期成果/需求分析/README.md) | 完整 Word 与 Markdown 报告、核心业务类图、三个关键用例时序图及验收场景 |
| [PPT 制作工作流](前期成果/需求分析/docs/PPT制作工作流.md) | 交给后续制作者的逐页安排、素材与任务文本 |

2026 年 10 月 26 日完成前期材料精简及需求分析。重复交付包、旧 PPT 和构建缓存已移除，整理前材料可从 Git 历史或仓库外历史版本备份恢复。需求分析模型与交付文档在前期成果下独立维护。
