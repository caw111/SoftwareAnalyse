# 个人空间接口（0.2）

## 个人资料

`GET /api/auth/me` 与 `POST /api/auth/login` 返回的 `user` 含以下附加字段：

- `orcid`：标准连字符格式；未填为空字符串。
- `websites`：`[{"label":"GitHub","url":"https://github.com/example"}]`，最多 8 项。
- `aboutMe`：个人简介、成就等，最多 4000 字符。
- `profileVersion`：个人资料版本，初始为 0。
- `scholarId`、`scholarName`、`institutionId`、`institutionName`：审核绑定门户后的资料；未绑定为 `null`。

`POST /api/me/profile` 需要 Bearer 会话，且只能更新当前账号。请求示例：

```json
{
  "displayName": "研究者姓名",
  "orcid": "0000-0002-1825-0097",
  "websites": [{"label": "GitHub", "url": "https://github.com/example"}],
  "aboutMe": "研究方向与公开成果介绍",
  "version": 0
}
```

成功返回完整个人资料，`profileVersion` 加 1；过期版本返回 HTTP 409，不覆盖新值。客户端收到冲突时需刷新并保留用户未保存内容供重新编辑。字段采用显式白名单，不能写入账号角色或门户绑定。网站只接受带有效主机、不含用户名密码的 HTTP/HTTPS URL；不主动访问远程网站。ORCID 接受标准编号或 `https://orcid.org/` 地址，并检查校验位；留空即可删除。

V2 Flyway 迁移为已有账号添加空资料与初始版本，V1 保持原样。提交与审计在同一数据库事务内；单条带版本条件的更新防止跨服务实例丢失编辑。

## 我的申请与审核列表

- `GET /api/claims?page=0&size=30`：仅当前账号自己的申请。
- `GET /api/claims?review=true&page=0&size=30`：管理员审核队列。

响应为 `{ "items": [], "total": 0, "page": 0, "size": 30 }`。页码从 0 开始，每页 1–100 条，按更新时间降序、申请 ID 排序。翻页过程中若出现新申请或状态更新，刷新列表会反映最新数据；此列表不是目录发布版本快照。未传 `page` 时保留旧数组接口以兼容旧客户端（旧接口仍最多 200 条，新界面应使用分页）。

界面可把 `IDENTITY` 与 `PORTAL` 统称“门户认证申请”，但须标明审核阶段。注册账号仍为 `USER`；身份审核通过成为 `RESEARCHER` 后，才可提出指定学者门户绑定申请。机构名称和身份说明可作为申请材料提交，不能直接赋权。成果申领仍须已有门户绑定，所有批准操作沿用版本、审核占用和数据库唯一约束。

TODO：机构目录增加审核登记的机构登录 URL 与认证协议配置后，再接入机构外部登录跳转和可信回调验证；当前机构下拉选项只用于人工审核材料，不代表已接入机构单点登录。

## 管理员统计

`GET /api/admin/statistics` 仅管理员可访问，返回：

- `catalogTotal`、`realCatalogTotal`、`demoCatalogTotal`、`catalogRevision`。
- `users`、`researchers`、`imports`。
- `pendingApplications`、`reviewingApplications`、`approvedApplications`。
- `byType: [{type,count}]`、`byState: [{state,count}]`。

本接口的目录总数和类型分布包含真实与模拟数据；界面应显示分类计数或明确统计口径。公共统计仍使用原有按数据集和筛选条件隔离的 `/api/statistics`。

## 验证范围

新增 HTTP 功能测试覆盖资料持久化、用户隔离、客户端伪造角色无效、匿名拒绝、危险链接与错误 ORCID 拒绝、过期版本冲突、申请分页归属及管理员统计权限。测试仅为功能验证，未运行本地压测；服务器 p95 仍需后续服务器环境测量。
