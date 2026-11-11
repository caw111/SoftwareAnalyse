using System.Globalization;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;

namespace AcademicDesktop;

public partial class MainWindow
{
    private DispatcherTimer? crawlRefreshTimer;
    private int crawlPage, qualityPage;
    private long crawlSettingsVersion;
    private bool crawlSettingsLoaded;
    private string? crawlParentTaskId;
    private JsonNode? crawlSelectedDetail;
    private JsonNode? hotspotData;

    private void EnsureCrawlUi()
    {
        if (crawlRefreshTimer != null) return;
        CrawlUntilDate.SelectedDate = DateTime.UtcNow.Date;
        CrawlFromDate.SelectedDate = DateTime.UtcNow.Date.AddDays(-6);
        crawlRefreshTimer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(5) };
        crawlRefreshTimer.Tick += async (_, _) =>
        {
            if (!ready || busy || !IsAdmin || !IsVisible || WindowState == WindowState.Minimized || Pages.SelectedIndex != 7 || AdminCatalogTabs.SelectedIndex != 0 || CrawlAutoRefresh.IsChecked != true) return;
            await Run(LoadCrawlTasks);
        };
        Closed += (_, _) => crawlRefreshTimer.Stop();
        crawlRefreshTimer.Start();
    }

    private async void AdminCatalogTabChanged(object sender, SelectionChangedEventArgs e)
    {
        if (!ready || !IsAdmin || e.Source != AdminCatalogTabs || Pages.SelectedIndex != 7) return;
        HighlightNavigation(7);
        if (busy) return;
        await Run(async () =>
        {
            if (AdminCatalogTabs.SelectedIndex == 0) await LoadCrawlOverview();
            else if (AdminCatalogTabs.SelectedIndex == 3) await LoadQuality();
            else await LoadAdminCatalog();
        });
    }

    private async Task LoadCrawlOverview()
    {
        RequireAccount("ADMIN"); EnsureCrawlUi();
        await LoadCrawlSources(false);
        await LoadCrawlTasks();
    }

    private async Task LoadCrawlSources(bool overwriteSettings)
    {
        RequireAccount("ADMIN");
        var sources = await api.Get("api/admin/crawl/sources");
        var source = sources.Items().FirstOrDefault(item => item.Text("id") == "crossref")
            ?? throw new InvalidOperationException("服务器尚未配置 Crossref 来源。");
        CrawlSourceSummary.Text = $"{(source.Flag("enabled") ? "来源已启用" : "来源已停用，请在来源设置中启用")} · 最短请求间隔 {source.Number("minIntervalMs")} ms · " +
            (source.Flag("contactConfigured") ? "访问联系信息已配置" : "访问联系信息未配置，请联系服务器管理员") + "\n" + source.Text("endpoint");
        if (overwriteSettings || !crawlSettingsLoaded)
        {
            crawlSettingsVersion = source.Number("configVersion");
            CrawlSourceEnabled.IsChecked = source.Flag("enabled");
            CrawlMinInterval.Text = source.Number("minIntervalMs").ToString();
            CrawlScheduleEnabled.IsChecked = source.Flag("scheduleEnabled");
            CrawlScheduleEvery.Text = source.Number("scheduleEveryMinutes").ToString();
            CrawlScheduleIssn.Text = source.Text("scheduleIssn");
            CrawlSchedulePageSize.Text = source.Number("schedulePageSize").ToString();
            CrawlScheduleMaxPages.Text = source.Number("scheduleMaxPages").ToString();
            CrawlScheduleLookback.Text = source.Number("scheduleLookbackDays").ToString();
            crawlSettingsLoaded = true;
        }
        CrawlScheduleSummary.Text = source.Flag("scheduleEnabled")
            ? $"服务器计划已启用 · 下次执行 {CrawlDisplay.Time(source, "nextScheduleAt")}；客户端无需保持开启。"
            : "定时计划未启用。启用后由服务器按指定 ISSN 和成功水位创建增量任务。";
    }

    private async Task LoadCrawlTasks()
    {
        RequireAccount("ADMIN");
        string? selectedId = (CrawlTasks.SelectedItem as CrawlTaskVm)?.Id;
        var response = await api.Get($"api/admin/crawl/tasks?page={crawlPage}&size=20");
        var tasks = response["items"]!.Items().Select(item => new CrawlTaskVm(item)).ToList();
        CrawlTasks.ItemsSource = tasks;
        UpdatePager(response, CrawlPageInfo, CrawlPrevious, CrawlNext);
        CrawlTasks.SelectedItem = tasks.FirstOrDefault(task => task.Id == selectedId) ?? tasks.FirstOrDefault();
        if (CrawlTasks.SelectedItem is CrawlTaskVm task) await LoadCrawlDetail(task.Id);
        else ClearCrawlSelection("暂无任务。填写范围并创建后，再选择启动。");
        var checkpoints = await api.Get("api/admin/crawl/checkpoints");
        var rows = checkpoints.Items().ToList();
        CrawlCheckpointSummary.Text = rows.Count == 0 ? "尚无完整扫描成功的增量窗口；限量采集和单篇 DOI 不推进水位。"
            : string.Join("\n", rows.Select(row => $"{row.Text("sourceId")} · 范围 {ShortId(row.Text("scopeKey"))} · 已完成至 {row.Text("successfulUntil")} · 更新 {CrawlDisplay.Time(row, "updatedAt")}"));
    }

    private async Task LoadCrawlDetail(string id)
    {
        RequireAccount("ADMIN");
        bool changed = crawlSelectedDetail?.Text("id") != id;
        if (changed) ClearCrawlSelection("正在读取所选任务…");
        var data = await api.Get("api/admin/crawl/tasks/" + Uri.EscapeDataString(id));
        crawlSelectedDetail = data;
        var task = new CrawlTaskVm(data);
        CrawlTaskSummary.Text = $"{task.StateLabel} · {task.ModeLabel} · 任务 {task.Id}\n{task.ScopeLabel}\n" +
            $"源更新时间 {data.Text("fromDate")} 至 {data.Text("untilDate")} · 已提交 {task.Pages} 页 · 公开版本 {data.Number("publicationRevision")}\n" +
            $"接收 {task.Received} / 最多 {data.Number("maxRecords")} · 新增 {task.Inserted} · 更新 {task.Updated} · 未变 {task.Unchanged} · 冲突 {task.Conflicts} · 隔离 {task.Excluded}\n" +
            $"执行尝试 {data.Number("attempt")} · 重试 {data.Number("retryCount")} · {CrawlDisplay.Completion(data.Text("completionReason"))}" +
            (data.Text("errorCode") == "" ? "" : $"\n错误 {data.Text("errorCode")}：{data.Text("errorMessage")}") +
            (data.Flag("stopRequested") && data.Text("state") == "RUNNING" ? "\n停止请求已记录，正在等待服务器在安全边界确认；当前尚未停止。" : "");
        CrawlTaskLogs.Text = data["logs"] is JsonArray logs
            ? string.Join("\n", logs.Items().Select(log => $"{CrawlDisplay.Time(log, "createdAt")} · {log.Text("action")} · {CrawlDisplay.State(log.Text("beforeState"))} → {CrawlDisplay.State(log.Text("afterState"))}\n{log.Text("message")}"))
            : "暂无执行记录。";
        CrawlRawPages.ItemsSource = data["pages"] is JsonArray pages ? pages.Items().Select(page => new CrawlPageVm(page)).ToList() : [];
        CrawlRawPages.SelectedIndex = CrawlRawPages.Items.Count > 0 ? 0 : -1;
        if (changed) { CrawlRawPreview.Clear(); CrawlRawPreview.Visibility = Visibility.Collapsed; }
        SetCrawlActionState();
    }

    private void ClearCrawlSelection(string message)
    {
        crawlSelectedDetail = null; CrawlTaskSummary.Text = message; CrawlTaskLogs.Clear(); CrawlRawPages.ItemsSource = null;
        CrawlRawPreview.Clear(); CrawlRawPreview.Visibility = Visibility.Collapsed; SetCrawlActionState();
    }
    private bool HasSelectedCrawlDetail => crawlSelectedDetail != null && CrawlTasks.SelectedItem is CrawlTaskVm selected && selected.Id == crawlSelectedDetail.Text("id");
    private void SetCrawlActionState()
    {
        string state = HasSelectedCrawlDetail ? crawlSelectedDetail!.Text("state") : "";
        bool stopped = crawlSelectedDetail?.Flag("stopRequested") == true;
        CrawlStart.IsEnabled = state == "PENDING" && !stopped && crawlSelectedDetail?.Flag("runnable") != true;
        CrawlStop.IsEnabled = (state is "PENDING" or "RUNNING" or "RETRYING" or "FAILED") && !stopped;
        string code = crawlSelectedDetail?.Text("errorCode") ?? "";
        CrawlRetry.IsEnabled = state == "FAILED" && !stopped && crawlSelectedDetail!.Number("retryCount") < 3 &&
            !new[] { "PAGE_LIMIT", "LIMIT_REACHED", "ACCESS_RESTRICTED", "ACCESS_CHALLENGE", "ROBOTS_DENIED", "NON_JSON", "INVALID_RESPONSE", "RESPONSE_TOO_LARGE" }.Contains(code);
        CrawlFollowup.IsEnabled = state is "SUCCESS" or "STOPPED" or "FAILED";
        CrawlOpenCatalog.IsEnabled = HasSelectedCrawlDetail && crawlSelectedDetail!.Number("publicationRevision") > 0;
    }

    private async void ShowCrawlCatalog(object sender, RoutedEventArgs e) => await Run(async () =>
    {
        RequireAccount("ADMIN");
        var detail = crawlSelectedDetail;
        if (!HasSelectedCrawlDetail || detail == null || detail.Number("publicationRevision") <= 0) throw new InvalidOperationException("当前任务尚无已发布成果。");
        string doi = detail.Text("doi");
        AdminSearch.Text = doi.Length > 0 ? doi : detail.Text("queryText");
        AdminType.SelectedIndex = 0; adminPage = 0; adminRevision = null;
        Dataset.SelectedIndex = 1; AdminCatalogTabs.SelectedIndex = 1;
        await LoadAdminCatalog();
        ShowMessage("已切换到真实成果目录，并按该任务的 DOI 或关键词检索。");
    });

    private async void RefreshCrawl(object sender, RoutedEventArgs e) => await Run(LoadCrawlOverview);
    private async void CrawlTaskSelected(object sender, SelectionChangedEventArgs e)
    {
        if (!ready || busy) return;
        if (CrawlTasks.SelectedItem is CrawlTaskVm task) await Run(() => LoadCrawlDetail(task.Id));
        else ClearCrawlSelection("选择任务查看状态、错误和断点。");
    }
    private async void CrawlPageChanged(object sender, RoutedEventArgs e) => await Run(async () =>
    {
        crawlPage = Math.Max(0, crawlPage + int.Parse(((Button)sender).Tag.ToString()!)); await LoadCrawlTasks();
    });

    private async void CreateCrawlTask(object sender, RoutedEventArgs e) => await Run(async () =>
    {
        RequireAccount("ADMIN");
        string doi = CrawlDoi.Text.Trim(), issn = CrawlIssn.Text.Trim().ToUpperInvariant(), query = CrawlQuery.Text.Trim();
        if (doi != "" && (issn != "" || query != "")) throw new InvalidOperationException("单篇 DOI 不能与 ISSN 或关键词同时填写。");
        if (doi == "" && issn == "" && query == "") throw new InvalidOperationException("请填写单篇 DOI，或者使用 ISSN / 关键词限定采集范围。");
        if (issn != "" && !Regex.IsMatch(issn, @"\A[0-9]{4}-[0-9]{3}[0-9X]\z")) throw new InvalidOperationException("ISSN 请使用 1234-567X 格式。");
        string? from = CrawlFromDate.SelectedDate?.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
        string? until = CrawlUntilDate.SelectedDate?.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
        if (doi == "")
        {
            if (from == null || until == null) throw new InvalidOperationException("请填写来源更新时间的开始与截止日期。");
            var start = CrawlFromDate.SelectedDate!.Value.Date; var end = CrawlUntilDate.SelectedDate!.Value.Date;
            if (start > end || (end - start).TotalDays > 30 || end > DateTime.UtcNow.Date) throw new InvalidOperationException("来源更新窗口须为过去或当前 UTC 日期内的 1–31 天。");
        }
        int maxRecords = CrawlInteger(CrawlMaxRecords, 1, 10000, "最多接收条数");
        int pageSize = CrawlInteger(CrawlPageSize, 1, 100, "每页条数"), maxPages = CrawlInteger(CrawlMaxPages, 1, 100, "页预算");
        int? fromYear = CrawlOptionalYear(CrawlPublicationFrom), toYear = CrawlOptionalYear(CrawlPublicationTo);
        if (fromYear > toYear) throw new InvalidOperationException("发表起始年不能晚于截止年。");
        var created = await api.Post("api/admin/crawl/tasks", new { sourceId = "crossref", doi, issn, query, fromDate = from, untilDate = until,
            pageSize, maxPages, parentTaskId = crawlParentTaskId, mode = SelectedTag(CrawlMode), maxRecords, fromPublicationYear = fromYear, toPublicationYear = toYear });
        crawlParentTaskId = null; CrawlParentInfo.Text = "新任务 · 创建后等待启动"; crawlPage = 0;
        await LoadCrawlTasks();
        var vm = CrawlTasks.Items.OfType<CrawlTaskVm>().FirstOrDefault(item => item.Id == created.Text("id"));
        if (vm != null) { CrawlTasks.SelectedItem = vm; await LoadCrawlDetail(vm.Id); }
        ShowMessage("采集任务已创建。核对范围后，选择任务并点击“启动”。");
    });

    private async void CrawlAction(object sender, RoutedEventArgs e) => await Run(async () =>
    {
        RequireAccount("ADMIN");
        if (crawlSelectedDetail == null || CrawlTasks.SelectedItem is not CrawlTaskVm selected || selected.Id != crawlSelectedDetail.Text("id"))
            throw new InvalidOperationException("请先选择采集任务。");
        string action = ((Button)sender).Tag.ToString()!;
        await api.Post($"api/admin/crawl/tasks/{selected.Id}/actions", new { version = crawlSelectedDetail.Number("version"), action });
        await LoadCrawlTasks();
        ShowMessage(action == "STOP" ? "停止请求已提交，请以刷新后的任务状态为准；运行中的任务需要服务器确认停止。" : action == "START" ? "启动请求已提交，服务器会按来源频率执行。" : "重试请求已提交，将从已提交的断点继续。");
    });

    private void CrawlCreateFollowup(object sender, RoutedEventArgs e)
    {
        if (busy || !IsAdmin || !HasSelectedCrawlDetail || !CrawlFollowup.IsEnabled) return;
        var data = crawlSelectedDetail!; crawlParentTaskId = data.Text("id");
        CrawlDoi.Text = data.Text("doi"); CrawlIssn.Text = data.Text("issn"); CrawlQuery.Text = data.Text("queryText");
        if (DateTime.TryParseExact(data.Text("fromDate"), "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out var from)) CrawlFromDate.SelectedDate = from;
        if (DateTime.TryParseExact(data.Text("untilDate"), "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out var until)) CrawlUntilDate.SelectedDate = until;
        CrawlMode.SelectedIndex = data.Text("mode") == "INCREMENTAL" ? 1 : 0;
        CrawlMaxRecords.Text = data.Text("maxRecords", "100"); CrawlPageSize.Text = data.Text("pageSize", "20"); CrawlMaxPages.Text = data.Text("maxPages", "10");
        CrawlPublicationFrom.Text = data.Text("fromPublicationYear"); CrawlPublicationTo.Text = data.Text("toPublicationYear");
        CrawlParentInfo.Text = "关联前序任务 " + ShortId(crawlParentTaskId) + " · 调整范围后创建，不修改原任务";
        CrawlTaskFormExpander.IsExpanded = true; CrawlMode.BringIntoView();
    }

    private async void ViewCrawlRawPage(object sender, RoutedEventArgs e) => await Run(async () =>
    {
        RequireAccount("ADMIN");
        if (!HasSelectedCrawlDetail || CrawlRawPages.SelectedItem is not CrawlPageVm page || page.Data.Text("taskId") != crawlSelectedDetail!.Text("id")) throw new InvalidOperationException("请选择一页已提交的原始响应。");
        var raw = await api.Get($"api/admin/crawl/tasks/{crawlSelectedDetail!.Text("id")}/pages/{page.Number}");
        string content = raw.Text("rawJson");
        CrawlRawPreview.Text = $"请求：{raw.Text("requestUrl")}\nSHA-256：{raw.Text("responseChecksum")}\n排除记录：{raw.Text("exclusionsJson")}\n\n" +
            (content.Length <= 128000 ? content : content[..128000] + "\n\n界面仅预览前 128,000 个字符；服务器保留完整原文。");
        CrawlRawPreview.Visibility = Visibility.Visible;
    });

    private async void ReloadCrawlSettings(object sender, RoutedEventArgs e) => await Run(() => LoadCrawlSources(true));
    private async void SaveCrawlSettings(object sender, RoutedEventArgs e) => await Run(async () =>
    {
        RequireAccount("ADMIN");
        if (!crawlSettingsLoaded) throw new InvalidOperationException("请先读取来源设置。");
        string issn = CrawlScheduleIssn.Text.Trim().ToUpperInvariant();
        bool enabled = CrawlSourceEnabled.IsChecked == true, scheduleEnabled = CrawlScheduleEnabled.IsChecked == true;
        if (scheduleEnabled && (!enabled || !Regex.IsMatch(issn, @"\A[0-9]{4}-[0-9]{3}[0-9X]\z")))
            throw new InvalidOperationException("启用定时计划需要先启用来源，并填写有效的期刊 ISSN。");
        await api.Post("api/admin/crawl/sources/crossref/settings", new
        {
            version = crawlSettingsVersion, enabled, minIntervalMs = CrawlInteger(CrawlMinInterval, 1000, 60000, "请求间隔"), scheduleEnabled,
            scheduleEveryMinutes = CrawlInteger(CrawlScheduleEvery, 60, 10080, "计划间隔"), scheduleIssn = issn,
            schedulePageSize = CrawlInteger(CrawlSchedulePageSize, 1, 100, "计划每页条数"),
            scheduleMaxPages = CrawlInteger(CrawlScheduleMaxPages, 1, 100, "计划页预算"),
            scheduleLookbackDays = CrawlInteger(CrawlScheduleLookback, 1, 31, "初次回溯天数")
        });
        await LoadCrawlSources(true); await LoadCrawlTasks(); ShowMessage("来源与服务器计划设置已保存。");
    });

    private static int CrawlInteger(TextBox input, int min, int max, string label)
    {
        if (!int.TryParse(input.Text.Trim(), out int value) || value < min || value > max) throw new InvalidOperationException($"{label}须为 {min}–{max} 的整数。");
        return value;
    }
    private static int? CrawlOptionalYear(TextBox input) => string.IsNullOrWhiteSpace(input.Text) ? null : CrawlInteger(input, 1000, 2200, "发表年份");
    private static string ShortId(string value) => value.Length > 12 ? value[..12] + "…" : value;

    private async Task LoadQuality()
    {
        RequireAccount("ADMIN");
        var data = await api.Get($"api/admin/quality?page={qualityPage}&size=20");
        QualitySummary.Text = $"待复核 {data.Number("openConflicts")} 项 · 规范成果 {data.Number("catalogTotal")} 项 · 有来源 {data.Number("withSource")} 项\n" +
            $"未分类 {data.Number("unclassified")} 项 · 机构未匹配 {data.Number("institutionUnmatched")} 项 · 失败采集任务 {data.Number("failedCrawls")} 项";
        QualityConflicts.ItemsSource = data["conflicts"]!.Items().Select(item => new MetadataConflictVm(item)).ToList();
        UpdatePager(data, QualityPageInfo, QualityPrevious, QualityNext);
        QualityDetail.Text = "选择冲突查看来源与版本。本页只读，冲突资料不会覆盖当前公开成果。";
    }
    private async void RefreshQuality(object sender, RoutedEventArgs e) => await Run(LoadQuality);
    private async void QualityPageChanged(object sender, RoutedEventArgs e) => await Run(async () => { qualityPage = Math.Max(0, qualityPage + int.Parse(((Button)sender).Tag.ToString()!)); await LoadQuality(); });
    private void QualityConflictSelected(object sender, SelectionChangedEventArgs e)
    {
        if (QualityConflicts.SelectedItem is not MetadataConflictVm conflict) return;
        var data = conflict.Data;
        QualityDetail.Text = $"{conflict.Title}\n{conflict.ReasonLabel} · {conflict.StateLabel}\n成果：{data.Text("workId")}\n来源：{conflict.SourceName} · {data.Text("sourceKey")}\n冲突编号：{data.Text("id")}\n基于公开版本：{data.Number("baseRevision")}\n记录时间：{CrawlDisplay.Time(data, "createdAt")}\n原始来源证据与当前主值均保留，需人工核查后再制定修订。";
    }

    private void DrawHotspotStatistics(JsonNode data)
    {
        hotspotData = data;
        var terms = data["hotspots"] is JsonArray hotspots ? hotspots.Items().ToList() : [];
        DrawBars(HotspotChart, terms.Select(term => ($"{term.Text("term")} · {ShareLabel(term["share"])}", term.Number("count"))));
        HotspotSummary.Text = $"基于题名与摘要的词项频次；每项成果对同一词项只计一次。有效语料 {data.Number("hotspotDenominator")} 项，不表示研究质量或未来趋势。";
        HotspotTerm.ItemsSource = terms.Select(term => term.Text("term")).ToList(); HotspotTerm.SelectedIndex = terms.Count > 0 ? 0 : -1;
        DrawHotspotTrend();
        var coverage = data["coverage"];
        CoverageNotes.Text = coverage == null ? "暂无覆盖信息。"
            : $"当前范围 {coverage.Number("total")} 项 · 未分类 {coverage.Number("unclassified")} 项 · 机构未匹配 {coverage.Number("institutionUnmatched")} 项 · 提供摘要 {coverage.Number("abstractAvailable")} 项。\n缺失的分类、机构及摘要保持缺失，不用其他来源的覆盖率替代。";
    }
    private void HotspotTermChanged(object sender, SelectionChangedEventArgs e) => DrawHotspotTrend();
    private void DrawHotspotTrend()
    {
        if (hotspotData == null || HotspotTerm.SelectedItem is not string term) { HotspotTrendChart.Children.Clear(); return; }
        var counts = hotspotData["hotspotTrend"] is JsonArray trend ? trend.Items().Where(row => row.Text("term") == term).ToDictionary(row => row.Text("year", "年份未知"), row => row.Number("count")) : new Dictionary<string, long>();
        var buckets = hotspotData["hotspotBuckets"] is JsonArray values ? values.Items().ToList() : [];
        DrawBars(HotspotTrendChart, buckets.Select(bucket =>
        {
            string year = bucket.Text("year", "年份未知"); long count = counts.GetValueOrDefault(year), denominator = bucket.Number("denominator");
            return ($"{year} · {count}/{denominator} · {(denominator == 0 ? "不适用" : ((double)count / denominator).ToString("P1"))}", count);
        }));
    }
    private static string ShareLabel(JsonNode? value) => value != null && double.TryParse(value.ToString(), NumberStyles.Float, CultureInfo.InvariantCulture, out double number) ? number.ToString("P1") : "不适用";

    private void ClearCrawlViews()
    {
        crawlSelectedDetail = null; crawlSettingsLoaded = false; crawlParentTaskId = null; crawlPage = qualityPage = 0;
        CrawlAutoRefresh.IsChecked = false; CrawlTasks.ItemsSource = null; CrawlRawPages.ItemsSource = null; CrawlTaskLogs.Clear(); CrawlRawPreview.Clear();
        CrawlRawPreview.Visibility = Visibility.Collapsed; QualityConflicts.ItemsSource = null; QualityDetail.Clear();
        SetCrawlActionState();
    }
}
