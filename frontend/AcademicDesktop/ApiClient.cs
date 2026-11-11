using System.Diagnostics;
using System.Net;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace AcademicDesktop;

public sealed class ApiClient : IDisposable
{
    private readonly HttpClient http;
    public string? Token { get; set; }
    public long LastMilliseconds { get; private set; }
    public ApiClient(string address)
    {
        if (!Uri.TryCreate(address.TrimEnd('/') + "/", UriKind.Absolute, out var uri) ||
            !(uri.Scheme == "https" || (uri.Scheme == "http" && uri.IsLoopback)) || !string.IsNullOrEmpty(uri.UserInfo))
            throw new InvalidOperationException("远程服务器必须使用 HTTPS；本机调试可使用 http://127.0.0.1:8080。");
        http = new HttpClient(new SocketsHttpHandler { PooledConnectionLifetime = TimeSpan.FromMinutes(5), MaxConnectionsPerServer = 8, AllowAutoRedirect = false })
        { BaseAddress = uri, Timeout = TimeSpan.FromSeconds(15) };
    }
    public Task<JsonNode> Get(string path, CancellationToken cancellation = default) => Send(HttpMethod.Get, path, null, cancellation);
    public Task<JsonNode> Post(string path, object body) => Send(HttpMethod.Post, path, JsonSerializer.Serialize(body), default);
    public Task<JsonNode> PostJson(string path, string json) => Send(HttpMethod.Post, path, json, default);
    private async Task<JsonNode> Send(HttpMethod method, string path, string? body, CancellationToken cancellation)
    {
        using var request = new HttpRequestMessage(method, path);
        if (Token != null) request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", Token);
        if (body != null) request.Content = new StringContent(body, Encoding.UTF8, "application/json");
        var timer = Stopwatch.StartNew();
        try
        {
            using var response = await http.SendAsync(request, cancellation);
            string text = await response.Content.ReadAsStringAsync(cancellation);
            LastMilliseconds = timer.ElapsedMilliseconds;
            JsonNode? value;
            try { value = JsonNode.Parse(text); }
            catch (JsonException) { throw new InvalidOperationException($"服务返回了非 JSON 响应（HTTP {(int)response.StatusCode}）。请检查 API 地址。"); }
            if (!response.IsSuccessStatusCode)
            {
                if (response.StatusCode == HttpStatusCode.Unauthorized) Token = null;
                throw new ApiFailure((int)response.StatusCode, value?.Text("message") ?? "请求失败，请稍后重试");
            }
            return value ?? new JsonObject();
        }
        catch (TaskCanceledException) when (!cancellation.IsCancellationRequested)
        { throw new InvalidOperationException(method == HttpMethod.Get ? "服务响应超时，筛选条件已保留。" : "请求超时，结果可能已提交；请先刷新状态，再决定是否重试。"); }
        catch (HttpRequestException) { throw new InvalidOperationException("无法连接 API，请检查服务器地址和后端运行状态。"); }
    }
    public void Dispose() => http.Dispose();
}
public sealed class ApiFailure(int status, string message) : Exception(message) { public int Status { get; } = status; }
public static class JsonValues
{
    public static string Text(this JsonNode node, string key, string fallback = "") => node[key]?.ToString() ?? fallback;
    public static long Number(this JsonNode node, string key) => long.TryParse(node[key]?.ToString(), out var n) ? n : 0;
    public static bool Flag(this JsonNode node, string key) => node[key]?.ToString().Equals("true", StringComparison.OrdinalIgnoreCase) == true;
    public static IEnumerable<JsonNode> Items(this JsonNode node) => node.AsArray().Where(x => x != null).Select(x => x!);
}
public record ReferenceItem(string Id, string Name);
public sealed class ScholarVm(JsonNode data)
{
    public JsonNode Data { get; } = data;
    public string Id => Data.Text("id"); public string Name => Data.Text("name");
    public string InstitutionName => Data.Text("institutionName", "机构未知");
    public string Label => Id == "" ? Name : $"{Name} · {Id} · {InstitutionName}";
    public string ClaimLabel => Data.Flag("claimed") ? "已认领" : "待认领";
}
public sealed class WorkVm(JsonNode data)
{
    public JsonNode Data { get; } = data;
    public string Id => Data.Text("id"); public string Title => Data.Text("title"); public string Type => Data.Text("type");
    public string TypeLabel => Labels.Type(Type);
    public string DateLabel => Data.Text("dateValue", Data.Text("year", "年份未知"));
    public string People => Data["contributors"] is JsonArray people && people.Count > 0 ? string.Join("  ·  ", people.Items().Select(p => p.Text("name"))) : "未公开个人贡献名单";
    public string Footer => Data.Text("venue") + (Type == "PAPER" ? "   ·   " + (Data["citationCount"] == null ? "引用未知" : "引用 " + Data.Text("citationCount")) : "") + (Data.Flag("simulated") ? "   ·   模拟" : "");
    public string ConfirmedRole => Labels.Role(Data.Text("contributionRole", ContributionRole));
    public string ContributionRole => Type switch { "PAPER" => "AUTHOR", "PATENT" => "INVENTOR", "PROJECT" => "PI", _ => "AWARDEE" };
}
public sealed class ClaimVm(JsonNode data)
{
    public JsonNode Data { get; } = data;
    public string Id => Data.Text("id"); public int Version => (int)Data.Number("version");
    public string KindLabel => Labels.Kind(Data.Text("kind")); public string StateLabel => Labels.State(Data.Text("state"));
    public string StageLabel => Data.Text("kind") switch { "IDENTITY" => "科研身份核验", "PORTAL" => "学者门户认领", "REVOKE" => "撤销关联", _ => "确认贡献" };
    public string TargetLabel => Data.Text("targetLabel"); public string ApplicantName => Data.Text("applicantName");
}
public sealed class ImportVm(JsonNode data)
{
    public string SourceName => data.Text("sourceName"); public string State => data.Text("state");
    public long Received => data.Number("received"); public long Inserted => data.Number("inserted");
    public long Duplicates => data.Number("duplicates"); public long Revision => data.Number("revision");
    public long Updated => data.Number("updated"); public long Unchanged => data.Number("unchanged"); public long Conflicts => data.Number("conflicts");
}
public static class Labels
{
    public static string DateKind(string kind) => kind switch { "publication_date" => "出版时间", "grant_date" => "授权时间", "funding_year" => "资助年度", "award_year" => "奖励年度", _ => kind };
    public static string Precision(string precision) => precision switch { "year" => "年精度", "month" => "月精度", "day" => "日精度", _ => "精度未知" };
    public static string Identifier(string type) => type switch { "application_number" => "申请号", "approval_number" => "批准号", "award_project_number" => "奖励项目编号", _ => type };
    public static string Field(string field) => field switch { "grantEvidence" => "授权依据", "jurisdiction" => "司法辖区", "notice" => "资料说明", _ => field };
    public static string Type(string type) => type switch { "PAPER" => "论文", "PATENT" => "授权专利", "PROJECT" => "科研项目", "AWARD" => "获奖", _ => type };
    public static string Kind(string kind) => kind switch { "IDENTITY" => "门户认证申请", "PORTAL" => "门户认证申请", "OUTCOME" => "成果申领", "REVOKE" => "成果申领", _ => kind };
    public static string State(string state) => state switch
    {
        "DRAFT" => "草稿", "PENDING_VERIFICATION" => "待验证", "VERIFYING" => "验证中", "PENDING_REVIEW" => "待审核",
        "UNDER_REVIEW" => "审核中", "NEED_MORE_INFO" => "待补充材料", "APPROVED" => "已通过", "REJECTED" => "已驳回", "WITHDRAWN" => "已撤回", _ => state
    };
    public static string Role(string role) => role switch { "USER" => "普通用户", "RESEARCHER" => "科研人员", "ADMIN" => "管理员", "AUTHOR" => "作者", "INVENTOR" => "发明人", "PI" => "负责人", "AWARDEE" => "完成人", _ => role };
}

public sealed class CrawlTaskVm(JsonNode data)
{
    public JsonNode Data { get; } = data;
    public string Id => Data.Text("id");
    public string StateLabel => Data.Flag("stopRequested") && Data.Text("state") == "RUNNING" ? "等待停止确认" : Data.Text("state") == "PENDING" && Data.Flag("runnable") ? "等待执行" : CrawlDisplay.State(Data.Text("state"));
    public string ModeLabel => Data.Text("mode") == "INCREMENTAL" ? "窗口增量" : "限量采集";
    public string ScopeLabel => Data.Text("doi") is { Length: > 0 } doi ? "DOI " + doi
        : string.Join(" · ", new[] { Data.Text("issn"), Data.Text("queryText"), Data.Text("fromDate") + " → " + Data.Text("untilDate") }.Where(value => value.Length > 0));
    public long Received => Data.Number("received"); public long Inserted => Data.Number("inserted"); public long Updated => Data.Number("updated");
    public long Unchanged => Data.Number("unchanged"); public long Conflicts => Data.Number("conflicts"); public long Excluded => Data.Number("excluded");
    public long Pages => Data.Number("committedPages");
}
public sealed class CrawlPageVm(JsonNode data)
{
    public JsonNode Data { get; } = data;
    public long Number => Data.Number("pageNo");
    public string Label => $"第 {Number} 页 · HTTP {Data.Number("httpStatus")} · 接收 {Data.Number("received")} · 可处理 {Data.Number("accepted")} · 隔离 {Data.Number("excluded")} · 版本 {Data.Number("revision")}";
}
public sealed class MetadataConflictVm(JsonNode data)
{
    public JsonNode Data { get; } = data;
    public string Title => Data.Text("title", Data.Text("workId"));
    public string SourceName => Data.Text("sourceName");
    public string StateLabel => Data.Text("state") == "OPEN" ? "待复核" : Data.Text("state");
    public string ReasonLabel => Data.Text("reason") switch
    {
        "SOURCE_IDENTITY_CONFLICT" => "来源强标识冲突", "CROSS_SOURCE_FIELD_CONFLICT" => "不同来源字段冲突",
        "MANUALLY_LOCKED_METADATA" => "主值已人工锁定", "MISSING_SOURCE_UPDATE_TIME" => "缺少来源更新时间",
        "STALE_SOURCE_OBSERVATION" => "较旧来源观测", "SAME_TIME_DIFFERENT_CONTENT" => "同一时间内容不同",
        "PARSER_RULE_CHANGED" => "解析规则变化需复核", _ => Data.Text("reason")
    };
}
public static class CrawlDisplay
{
    public static string State(string state) => state switch
    {
        "PENDING" => "待启动", "RUNNING" => "运行中", "RETRYING" => "等待重试", "SUCCESS" => "已完成", "FAILED" => "失败", "STOPPED" => "已停止", "" => "—", _ => state
    };
    public static string Completion(string reason) => reason switch
    {
        "LIMIT_REACHED" => "达到设定条数，限量任务结束", "SOURCE_EXHAUSTED" => "来源范围已扫描完成", "DOI_COMPLETED" => "单篇 DOI 已完成",
        "" => "尚未结束", _ => reason
    };
    public static string Time(JsonNode node, string key)
    {
        long value = node.Number(key);
        if (value <= 0) return "—";
        try { return DateTimeOffset.FromUnixTimeMilliseconds(value).ToLocalTime().ToString("yyyy-MM-dd HH:mm:ss"); }
        catch (ArgumentOutOfRangeException) { return "—"; }
    }
}
