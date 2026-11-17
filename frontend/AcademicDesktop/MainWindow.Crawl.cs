using System.Globalization;
using System.IO;
using Microsoft.Win32;
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
    private bool crawlSettingsLoaded, changingCrawlSource;
    private string? crawlSettingsSourceId, crawlFormSourceId;
    private List<CrawlSourceVm> crawlSources = [];
    private string? crawlParentTaskId, crawlParentSourceId;
    private JsonNode? crawlRawDetail;
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

    private async Task LoadCrawlSources(bool overwriteSettings, string? selectSourceId = null)
    {
        RequireAccount("ADMIN");
        string? selectedId = selectSourceId ?? (CrawlSource.SelectedItem as CrawlSourceVm)?.Id;
        var response = await api.Get("api/admin/crawl/sources");
        crawlSources = response.Items().Select(item => new CrawlSourceVm(item)).ToList();
        var selected = crawlSources.FirstOrDefault(source => source.Id == selectedId)
            ?? (selectedId == null ? crawlSources.FirstOrDefault(source => source.Id == "crossref") ?? crawlSources.FirstOrDefault() : null);
        changingCrawlSource = true;
        try { CrawlSource.ItemsSource = crawlSources; CrawlSource.SelectedItem = selected; }
        finally { changingCrawlSource = false; }
        if (selected == null)
        {
            crawlSettingsLoaded = false; crawlSettingsSourceId = null;
            CrawlCreateButton.IsEnabled = CrawlSaveSettingsButton.IsEnabled = false;
            CrawlSourceSummary.Text = "当前来源不可用，请刷新来源列表。";
            throw new InvalidOperationException(selectedId == null ? "服务器尚未登记成果来源。" : "所选来源已不可用，请重新选择来源。");
        }
        ApplyCrawlSourceForm(selected);
        var source = selected.Data;
        string access = selected.IsCrossref ? (source.Flag("contactConfigured") ? " · 访问联系信息已配置" : " · 访问联系信息未配置，请联系服务器管理员") : " · 仅访问已登记清单";
        CrawlSourceTitle.Text = selected.Label;
        CrawlSourceSummary.Text = $"{(source.Flag("enabled") ? "来源已启用" : "来源已停用，请在本来源设置中启用")} · 最短请求间隔 {source.Number("minIntervalMs")} ms" + access + "\n" + source.Text("endpoint");
        if (overwriteSettings || !crawlSettingsLoaded || crawlSettingsSourceId != selected.Id)
        {
            crawlSettingsVersion = source.Number("configVersion"); crawlSettingsSourceId = selected.Id;
            CrawlSourceEnabled.IsChecked = source.Flag("enabled");
            CrawlMinInterval.Text = source.Text("minIntervalMs", "1000");
            CrawlScheduleEnabled.IsChecked = selected.SupportsSchedule && source.Flag("scheduleEnabled");
            CrawlScheduleEvery.Text = source.Text("scheduleEveryMinutes", "1440");
            CrawlScheduleIssn.Text = source.Text("scheduleIssn");
            CrawlSchedulePageSize.Text = source.Text("schedulePageSize", "50");
            CrawlScheduleMaxPages.Text = source.Text("scheduleMaxPages", "20");
            CrawlScheduleLookback.Text = source.Text("scheduleLookbackDays", "1");
            crawlSettingsLoaded = true;
        }
        CrawlSaveSettingsButton.IsEnabled = crawlSettingsLoaded;
        CrawlScheduleSummary.Text = !selected.SupportsSchedule ? "本来源按公告 / 清单批次采集，不提供自动定时计划。可重新创建同一批次任务，由服务器依据原文哈希识别未变内容。"
            : source.Flag("scheduleEnabled") ? $"服务器计划已启用 · 下次执行 {CrawlDisplay.Time(source, "nextScheduleAt")}；客户端无需保持开启。"
            : "定时计划未启用。启用后由服务器按指定 ISSN 和成功水位创建增量任务。";
    }

    private void ApplyCrawlSourceForm(CrawlSourceVm source)
    {
        bool changed = crawlFormSourceId != source.Id;
        string? batchId = changed ? null : (CrawlBatch.SelectedItem as CrawlBatchVm)?.Id;
        if (changed)
        {
            crawlFormSourceId = source.Id; ResetCrawlParent();
            CrawlDoi.Clear(); CrawlIssn.Clear(); CrawlQuery.Clear(); CrawlPublicationFrom.Clear(); CrawlPublicationTo.Clear();
            CrawlFromDate.SelectedDate = DateTime.UtcNow.Date.AddDays(-6); CrawlUntilDate.SelectedDate = DateTime.UtcNow.Date;
            CrawlMode.SelectedIndex = 0;
        }
        CrawlCrossrefScope.Visibility = source.IsCrossref ? Visibility.Visible : Visibility.Collapsed;
        CrawlPublicationRange.Visibility = source.IsCrossref ? Visibility.Visible : Visibility.Collapsed;
        CrawlBatchScope.Visibility = source.IsBatch ? Visibility.Visible : Visibility.Collapsed;
        CrawlIncrementalMode.IsEnabled = source.SupportsIncremental;
        if (!source.SupportsIncremental) CrawlMode.SelectedIndex = 0;
        CrawlMode.IsEnabled = source.SupportsIncremental;
        CrawlBoundedMode.Content = source.IsBatch ? "清单限量 · 按登记批次处理" : "限量采集 · 达到数量即结束";
        var batches = source.Batches;
        CrawlBatch.ItemsSource = batches; CrawlBatch.SelectedItem = batches.FirstOrDefault(batch => batch.Id == batchId) ?? batches.FirstOrDefault();
        UpdateCrawlBatchSummary();
        CrawlPageSizeLabel.Text = source.IsBatch ? "每次提交条数（1–100）" : "每页条数（1–100）";
        CrawlMaxPagesLabel.Text = source.IsBatch ? "提交批次数预算（1–100）" : "页预算（1–100）";
        CrawlBudgetNote.Text = source.IsBatch
            ? "服务器下载固定清单并冻结原文，随后分批提交；以上是入库批次预算，不是网络翻页。达到条数或批次上限不代表整份清单已处理完成。"
            : "窗口增量必须扫描完整窗口才会推进水位；数量或页预算不足时请缩小范围，再创建关联任务。";
        CrawlSourceEnabled.Content = "启用 " + source.Name + " 来源";
        CrawlScheduleEnabled.IsEnabled = source.SupportsSchedule;
        CrawlScheduleFields.Visibility = source.SupportsSchedule ? Visibility.Visible : Visibility.Collapsed;
        if (!source.SupportsSchedule) CrawlScheduleEnabled.IsChecked = false;
        CrawlCreateButton.IsEnabled = source.Data.Flag("enabled") && (source.IsCrossref || source.IsBatch && batches.Count > 0);
    }

    private async void CrawlSourceChanged(object sender, SelectionChangedEventArgs e)
    {
        if (!ready || busy || changingCrawlSource || e.Source != CrawlSource || CrawlSource.SelectedItem is not CrawlSourceVm source) return;
        crawlSettingsLoaded = false; crawlSettingsSourceId = null;
        ApplyCrawlSourceForm(source);
        CrawlSourceTitle.Text = source.Label; CrawlSourceSummary.Text = "正在读取本来源设置…";
        CrawlCreateButton.IsEnabled = CrawlSaveSettingsButton.IsEnabled = false;
        await Run(() => LoadCrawlSources(true, source.Id));
    }
    private void CrawlBatchChanged(object sender, SelectionChangedEventArgs e)
    {
        if (!ready || e.Source != CrawlBatch) return;
        UpdateCrawlBatchSummary();
    }
    private void UpdateCrawlBatchSummary()
    {
        CrawlBatchSummary.Text = CrawlBatch.SelectedItem is CrawlBatchVm batch
            ? $"批次 {batch.Id} · 清单年度 {batch.Year} · {batch.ContentType}\n{batch.Url}\n清单年度用于辨认来源批次；成果日期以原文明确记载为准。"
            : "服务器尚未为本来源登记可采集批次。";
    }
    private void ResetCrawlParent()
    {
        crawlParentTaskId = crawlParentSourceId = null; CrawlParentInfo.Text = "新任务 · 创建后等待启动";
    }
    private CrawlSourceVm RequireCrawlSource()
    {
        RequireAccount("ADMIN");
        if (CrawlSource.SelectedItem is not CrawlSourceVm source || crawlFormSourceId != source.Id || (!source.IsBatch && !source.IsCrossref))
            throw new InvalidOperationException("请选择服务器支持的成果来源。");
        return source;
    }
    private CrawlSourceVm? FindCrawlSource(string id) => crawlSources.FirstOrDefault(source => source.Id == id);

    private async Task LoadCrawlTasks()
    {
        RequireAccount("ADMIN");
        string? selectedId = (CrawlTasks.SelectedItem as CrawlTaskVm)?.Id;
        var response = await api.Get($"api/admin/crawl/tasks?page={crawlPage}&size=20");
        var tasks = response["items"]!.Items().Select(item => new CrawlTaskVm(item, FindCrawlSource(item.Text("sourceId")))).ToList();
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
        var task = new CrawlTaskVm(data, FindCrawlSource(data.Text("sourceId")));
        bool batchTask = data.Text("batchId").Length > 0;
        CrawlTaskSummary.Text = $"{task.StateLabel} · {task.ModeLabel} · {task.SourceLabel} · 任务 {task.Id}\n{task.ScopeLabel}\n" +
            (batchTask ? $"登记批次 {data.Text("batchId")} · 已提交 {task.Pages} 批" : $"源更新时间 {data.Text("fromDate")} 至 {data.Text("untilDate")} · 已提交 {task.Pages} 页") + $" · 公开版本 {data.Number("publicationRevision")}\n" +
            $"接收 {task.Received} / 最多 {data.Number("maxRecords")} · 新增 {task.Inserted} · 更新 {task.Updated} · 未变 {task.Unchanged} · 冲突 {task.Conflicts} · 隔离 {task.Excluded}\n" +
            $"执行尝试 {data.Number("attempt")} · 重试 {data.Number("retryCount")} · {CrawlDisplay.Completion(data.Text("completionReason"))}" +
            (data.Text("errorCode") == "" ? "" : $"\n错误 {data.Text("errorCode")}：{data.Text("errorMessage")}") +
            (data.Flag("stopRequested") && data.Text("state") == "RUNNING" ? "\n停止请求已记录，正在等待服务器在安全边界确认；当前尚未停止。" : "");
        CrawlTaskLogs.Text = data["logs"] is JsonArray logs
            ? string.Join("\n", logs.Items().Select(log => $"{CrawlDisplay.Time(log, "createdAt")} · {log.Text("action")} · {CrawlDisplay.State(log.Text("beforeState"))} → {CrawlDisplay.State(log.Text("afterState"))}\n{log.Text("message")}"))
            : "暂无执行记录。";
        CrawlRawPages.ItemsSource = data["pages"] is JsonArray pages ? pages.Items().Select(page => new CrawlPageVm(page)).ToList() : [];
        CrawlRawPages.SelectedIndex = CrawlRawPages.Items.Count > 0 ? 0 : -1;
        if (changed) ClearCrawlRawPreview();
        SetCrawlActionState();
    }

    private void ClearCrawlSelection(string message)
    {
        crawlSelectedDetail = null; CrawlTaskSummary.Text = message; CrawlTaskLogs.Clear(); CrawlRawPages.ItemsSource = null;
        ClearCrawlRawPreview(); SetCrawlActionState();
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
            !new[] { "PAGE_LIMIT", "LIMIT_REACHED", "ACCESS_RESTRICTED", "ACCESS_CHALLENGE", "TLS_VALIDATION_FAILED", "ROBOTS_DENIED", "NON_JSON", "NON_HTML", "INVALID_RESPONSE", "DOCUMENT_CHANGED", "RESPONSE_TOO_LARGE" }.Contains(code);
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
        string outcomeType = FindCrawlSource(detail.Text("sourceId"))?.OutcomeType ?? "";
        AdminType.SelectedItem = AdminType.Items.OfType<ComboBoxItem>().FirstOrDefault(item => item.Tag?.ToString() == outcomeType) ?? AdminType.Items[0];
        adminPage = 0; adminRevision = null;
        Dataset.SelectedIndex = 1; AdminCatalogTabs.SelectedIndex = 1;
        await LoadAdminCatalog();
        ShowMessage(detail.Text("batchId").Length > 0 ? "已切换到真实成果目录并筛选成果类型；目录包含此类型的全部已收录成果，可继续按题名检索。" : "已切换到真实成果目录，并按该任务的 DOI 或关键词检索。");
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
        var source = RequireCrawlSource();
        if (!source.Data.Flag("enabled")) throw new InvalidOperationException("当前来源已停用，请先保存启用设置。");
        if (crawlParentTaskId != null && crawlParentSourceId != source.Id) throw new InvalidOperationException("关联任务的来源与当前来源不一致，请重新选择范围。");
        string? batchId = null, doi = null, issn = null, query = null, from = null, until = null;
        int? fromYear = null, toYear = null;
        string mode = "BOUNDED";
        if (source.IsBatch)
        {
            if (CrawlBatch.SelectedItem is not CrawlBatchVm batch || !source.Batches.Any(item => item.Id == batch.Id))
                throw new InvalidOperationException("请选择本来源已登记的公告 / 清单批次。");
            batchId = batch.Id;
        }
        else
        {
            doi = CrawlDoi.Text.Trim(); issn = CrawlIssn.Text.Trim().ToUpperInvariant(); query = CrawlQuery.Text.Trim();
            if (doi != "" && (issn != "" || query != "")) throw new InvalidOperationException("单篇 DOI 不能与 ISSN 或关键词同时填写。");
            if (doi == "" && issn == "" && query == "") throw new InvalidOperationException("请填写单篇 DOI，或者使用 ISSN / 关键词限定采集范围。");
            if (issn != "" && !Regex.IsMatch(issn, @"\A[0-9]{4}-[0-9]{3}[0-9X]\z")) throw new InvalidOperationException("ISSN 请使用 1234-567X 格式。");
            from = CrawlFromDate.SelectedDate?.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
            until = CrawlUntilDate.SelectedDate?.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
            if (doi == "")
            {
                if (from == null || until == null) throw new InvalidOperationException("请填写来源更新时间的开始与截止日期。");
                var start = CrawlFromDate.SelectedDate!.Value.Date; var end = CrawlUntilDate.SelectedDate!.Value.Date;
                if (start > end || (end - start).TotalDays > 30 || end > DateTime.UtcNow.Date) throw new InvalidOperationException("来源更新窗口须为过去或当前 UTC 日期内的 1–31 天。");
            }
            fromYear = CrawlOptionalYear(CrawlPublicationFrom); toYear = CrawlOptionalYear(CrawlPublicationTo);
            if (fromYear > toYear) throw new InvalidOperationException("发表起始年不能晚于截止年。");
            mode = SelectedTag(CrawlMode);
            if (mode == "INCREMENTAL" && !source.SupportsIncremental) throw new InvalidOperationException("本来源不支持窗口增量。");
        }
        int maxRecords = CrawlInteger(CrawlMaxRecords, 1, 10000, "最多处理条数");
        int pageSize = CrawlInteger(CrawlPageSize, 1, 100, source.IsBatch ? "每次提交条数" : "每页条数");
        int maxPages = CrawlInteger(CrawlMaxPages, 1, 100, source.IsBatch ? "提交批次数预算" : "页预算");
        var created = await api.Post("api/admin/crawl/tasks", new { sourceId = source.Id, batchId, doi, issn, query, fromDate = from, untilDate = until,
            pageSize, maxPages, parentTaskId = crawlParentTaskId, mode, maxRecords, fromPublicationYear = fromYear, toPublicationYear = toYear });
        ResetCrawlParent(); crawlPage = 0;
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

    private async void CrawlCreateFollowup(object sender, RoutedEventArgs e)
    {
        if (busy || !IsAdmin || !HasSelectedCrawlDetail || !CrawlFollowup.IsEnabled) return;
        var data = crawlSelectedDetail!;
        await Run(async () =>
        {
            RequireAccount("ADMIN"); ResetCrawlParent();
            await LoadCrawlSources(true, data.Text("sourceId"));
            var source = RequireCrawlSource();
            if (source.IsBatch)
            {
                CrawlBatch.SelectedItem = CrawlBatch.Items.OfType<CrawlBatchVm>().FirstOrDefault(batch => batch.Id == data.Text("batchId"));
                if (CrawlBatch.SelectedItem == null) throw new InvalidOperationException("原任务的登记批次已不可用，请选择新批次后创建任务。");
                UpdateCrawlBatchSummary();
            }
            CrawlDoi.Text = data.Text("doi"); CrawlIssn.Text = data.Text("issn"); CrawlQuery.Text = data.Text("queryText");
            if (DateTime.TryParseExact(data.Text("fromDate"), "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out var from)) CrawlFromDate.SelectedDate = from;
            if (DateTime.TryParseExact(data.Text("untilDate"), "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out var until)) CrawlUntilDate.SelectedDate = until;
            CrawlMode.SelectedIndex = source.SupportsIncremental && data.Text("mode") == "INCREMENTAL" ? 1 : 0;
            CrawlMaxRecords.Text = data.Text("maxRecords", "100"); CrawlPageSize.Text = data.Text("pageSize", "20"); CrawlMaxPages.Text = data.Text("maxPages", "10");
            CrawlPublicationFrom.Text = data.Text("fromPublicationYear"); CrawlPublicationTo.Text = data.Text("toPublicationYear");
            crawlParentTaskId = data.Text("id"); crawlParentSourceId = source.Id;
            CrawlParentInfo.Text = "关联前序任务 " + ShortId(crawlParentTaskId) + " · 调整范围后创建，不修改原任务";
            CrawlTaskFormExpander.IsExpanded = true; CrawlSource.BringIntoView();
        });
    }

    private async void ViewCrawlRawPage(object sender, RoutedEventArgs e) => await Run(async () =>
    {
        RequireAccount("ADMIN");
        if (!HasSelectedCrawlDetail || CrawlRawPages.SelectedItem is not CrawlPageVm page || page.Data.Text("taskId") != crawlSelectedDetail!.Text("id")) throw new InvalidOperationException("请选择一批 / 页已提交的原始记录。");
        ClearCrawlRawPreview();
        var raw = await api.Get($"api/admin/crawl/tasks/{crawlSelectedDetail!.Text("id")}/pages/{page.Number}");
        crawlRawDetail = raw;
        string content = raw.Text("rawJson");
        bool pdf = raw.Text("bodyEncoding") == "base64" && raw.Text("contentType").StartsWith("application/pdf", StringComparison.OrdinalIgnoreCase);
        string evidence = $"请求：{raw.Text("requestUrl")}\n响应 SHA-256：{raw.Text("responseChecksum")}\n原始文件 SHA-256：{raw.Text("byteChecksum", "不适用")}\n解析规则：{raw.Text("parserVersion", "见入库来源记录")} · 清单总条数：{raw.Text("recordCount", "不适用")}\n类型：{raw.Text("contentType")} · 编码：{raw.Text("bodyEncoding")}\n批次定位：{raw.Text("sliceMetadata", "见原始响应")}\n隔离记录：{raw.Text("exclusionsJson")}\n\n";
        CrawlRawPreview.Text = evidence + (pdf
            ? "PDF 原文以 Base64 编码完整存档。可保存原始附件核对；本窗口不展示编码正文，也不会自动打开文件。清单行号与公告页码请结合批次定位、成果来源记录和原始附件查看。"
            : content.Length <= 128000 ? content : content[..128000] + "\n\n界面仅预览前 128,000 个字符；服务器保留完整原文。");
        CrawlDownloadAttachment.Visibility = pdf ? Visibility.Visible : Visibility.Collapsed;
        CrawlRawPreview.Visibility = Visibility.Visible;
    });
    private void CrawlRawPageChanged(object sender, SelectionChangedEventArgs e)
    {
        if (ready && e.Source == CrawlRawPages) ClearCrawlRawPreview();
    }
    private void ClearCrawlRawPreview()
    {
        crawlRawDetail = null; CrawlRawPreview.Clear(); CrawlRawPreview.Visibility = Visibility.Collapsed;
        CrawlDownloadAttachment.Visibility = Visibility.Collapsed;
    }
    private async void DownloadCrawlAttachment(object sender, RoutedEventArgs e) => await Run(async () =>
    {
        RequireAccount("ADMIN");
        var raw = crawlRawDetail;
        if (raw == null || !HasSelectedCrawlDetail || CrawlRawPages.SelectedItem is not CrawlPageVm page ||
            raw.Text("taskId") != crawlSelectedDetail!.Text("id") || raw.Number("pageNo") != page.Number ||
            raw.Text("bodyEncoding") != "base64" || !raw.Text("contentType").StartsWith("application/pdf", StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("请先读取当前任务的原始 PDF 记录。");
        byte[] bytes;
        try { bytes = Convert.FromBase64String(raw.Text("rawJson")); }
        catch (FormatException) { throw new InvalidOperationException("服务器附件编码无效，无法保存。"); }
        string checksum = Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(bytes)).ToLowerInvariant();
        if (raw.Text("byteChecksum") is { Length: > 0 } expected && !string.Equals(checksum, expected, StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("原始附件校验值不匹配，无法保存。");
        var dialog = new SaveFileDialog { Title = "保存服务器存档的原始 PDF", Filter = "PDF 文件 (*.pdf)|*.pdf", DefaultExt = ".pdf", AddExtension = true,
            FileName = "academic-source-" + ShortId(raw.Text("taskId")).TrimEnd('…') + ".pdf", OverwritePrompt = true };
        if (dialog.ShowDialog(this) != true) return;
        await File.WriteAllBytesAsync(dialog.FileName, bytes);
        ShowMessage("原始 PDF 附件已保存；未自动打开文件。");
    });

    private async void ReloadCrawlSettings(object sender, RoutedEventArgs e) => await Run(() => LoadCrawlSources(true));
    private async void SaveCrawlSettings(object sender, RoutedEventArgs e) => await Run(async () =>
    {
        var source = RequireCrawlSource();
        if (!crawlSettingsLoaded || crawlSettingsSourceId != source.Id) throw new InvalidOperationException("请先读取当前来源的设置。");
        string issn = source.SupportsSchedule ? CrawlScheduleIssn.Text.Trim().ToUpperInvariant() : "";
        bool enabled = CrawlSourceEnabled.IsChecked == true, scheduleEnabled = source.SupportsSchedule && CrawlScheduleEnabled.IsChecked == true;
        if (scheduleEnabled && (!enabled || !Regex.IsMatch(issn, @"\A[0-9]{4}-[0-9]{3}[0-9X]\z")))
            throw new InvalidOperationException("启用定时计划需要先启用来源，并填写有效的期刊 ISSN。");
        await api.Post($"api/admin/crawl/sources/{Uri.EscapeDataString(source.Id)}/settings", new
        {
            version = crawlSettingsVersion, enabled, minIntervalMs = CrawlInteger(CrawlMinInterval, 1000, 60000, "请求间隔"), scheduleEnabled,
            scheduleEveryMinutes = source.SupportsSchedule ? CrawlInteger(CrawlScheduleEvery, 60, 10080, "计划间隔") : 1440, scheduleIssn = issn,
            schedulePageSize = source.SupportsSchedule ? CrawlInteger(CrawlSchedulePageSize, 1, 100, "计划每页条数") : 50,
            scheduleMaxPages = source.SupportsSchedule ? CrawlInteger(CrawlScheduleMaxPages, 1, 100, "计划页预算") : 20,
            scheduleLookbackDays = source.SupportsSchedule ? CrawlInteger(CrawlScheduleLookback, 1, 31, "初次回溯天数") : 1
        });
        await LoadCrawlSources(true, source.Id); await LoadCrawlTasks(); ShowMessage("来源与服务器计划设置已保存。");
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
        crawlSelectedDetail = null; crawlSettingsLoaded = false; crawlSettingsSourceId = crawlFormSourceId = null; ResetCrawlParent(); crawlPage = qualityPage = 0;
        changingCrawlSource = true;
        try { CrawlSource.ItemsSource = null; CrawlBatch.ItemsSource = null; crawlSources.Clear(); }
        finally { changingCrawlSource = false; }
        CrawlCreateButton.IsEnabled = CrawlSaveSettingsButton.IsEnabled = false; ClearCrawlRawPreview();
        CrawlAutoRefresh.IsChecked = false; CrawlTasks.ItemsSource = null; CrawlRawPages.ItemsSource = null; CrawlTaskLogs.Clear(); CrawlRawPreview.Clear();
        CrawlRawPreview.Visibility = Visibility.Collapsed; QualityConflicts.ItemsSource = null; QualityDetail.Clear();
        SetCrawlActionState();
    }
}
