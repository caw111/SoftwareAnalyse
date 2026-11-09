# 知汇应用图标

原创矢量图形：打开的书页表示学术成果，汇聚的节点表示知识与学者之间的联系。使用现有界面的深青色、薄荷绿，中心点用暖金色。

- `zhihui.svg`：手绘路径源文件，可直接编辑。
- `zhihui.png`：256 × 256，保留透明圆角外部区域，供侧栏展示。
- `zhihui.ico`：16、20、24、32、40、48、64、128、256 像素的 32 位透明图标，供 Windows EXE、标题栏及任务栏使用。

仓库根目录执行 `./scripts/build-icon.ps1`，用 WPF 按矢量路径重新生成 PNG/ICO。图标无外部字体、图库或生成式位图依赖。

## 导航图标与默认头像

所有导航图标均为原创 24 × 24 SVG，采用 1.7 单位圆角描边，不依赖字体字形。侧栏统一显示为 20 × 20，使用 currentColor 跟随选中状态的文字颜色。

| 文件 | 用途 |
| --- | --- |
| Navigation/discovery.svg | 成果发现 |
| Navigation/scholars.svg | 学者门户 |
| Navigation/statistics.svg | 数据观察、管理员数据统计 |
| Navigation/graph.svg | 共著路径 |
| Navigation/profile.svg | 个人主页 |
| Navigation/outcomes.svg | 个人成果 |
| Navigation/applications.svg | 我的申请 |
| Navigation/database.svg | 成果数据库管理 |
| Navigation/review.svg | 申请管理 |

avatar-default.svg 为 96 × 96 灰绿色默认人物头像，供访客及尚未设置头像的账号使用。

SvgIcon.cs 直接读取程序集资源中的 SVG；侧栏与头像在各 DPI 下保持矢量清晰度。解析器只支持本项目使用的 path、circle、rect、line、polyline、g 元素，禁止 DTD 和外部资源，不运行脚本。颜色、描边及路径修改后重新构建桌面客户端即可生效。
