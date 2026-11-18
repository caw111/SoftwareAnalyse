using System.Diagnostics;
using System.IO;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;

namespace AcademicDesktop;

public partial class MainWindow
{
    /// <summary>
    /// Explicit local WPF/API acceptance. Clicks Create/Stop/settings, never START or scheduler enable.
    /// Drafts are retained as stopped audit records; no external source request is initiated.
    /// </summary>
    private async Task RunCrawlSmoke()
    {
        string output = Path.GetFullPath(Environment.GetEnvironmentVariable("ACADEMIC_SMOKE_OUTPUT")
            ?? Path.Combine(AppContext.BaseDirectory, "crawl-smoke.json"));
        Directory.CreateDirectory(Path.GetDirectoryName(output)!);
        var report = new JsonObject { ["ok"] = false, ["api"] = ServerAddress.Text, ["startedAt"] = DateTimeOffset.UtcNow.ToString("O"),
            ["mode"] = "local-functional-ui; no-START; no-external-requests; no-load-test" };
        var screenshots = new JsonObject(); var checks = new JsonArray(); var createdIds = new List<string>();
        report["screenshots"] = screenshots; report["checks"] = checks;
        JsonNode? originalSource = null;
        bool settingsTouched = false;
        var batchSettingsToRestore = new Dictionary<string, JsonNode>();
        try
        {
            AssertSmoke(ServerEndpoint.IsLocalDemo(ServerAddress.Text),
                "采集界面验收只允许本机 API。");
            AssertSmoke(account == null && api.Token == null, "采集界面验收必须从访客入口启动。");
            busy = true;
            var login = await api.Post("api/auth/login", new
            {
                username = Environment.GetEnvironmentVariable("ACADEMIC_SMOKE_ADMIN_USERNAME") ?? "admin",
                password = Environment.GetEnvironmentVariable("ACADEMIC_SMOKE_ADMIN_PASSWORD") ?? "DemoPass2026!"
            });
            api.Token = login.Text("token"); account = login["user"]!.DeepClone();
            AssertSmoke(account.Text("role") == "ADMIN", "验收账号没有管理员权限。");
            ConfigureWorkspace(); UpdateAccount(); SwitchPage(7); AdminCatalogTabs.SelectedIndex = 0;
            await LoadAdminCatalog();
            CrawlAutoRefresh.IsChecked = false;
            busy = false; SetBusyState(false);
            await FlushWorkspaceLayout();
            AssertSmoke(WorkspaceNavIndices().SequenceEqual(new[] { 7, 8, 9 }) && AdminCatalogTabs.SelectedIndex == 0 && CrawlTasks.IsVisible,
                "管理员采集入口或三个侧栏未正确呈现。");
            AssertSmoke(ScopeSelector.Visibility == Visibility.Collapsed && ScopeFooter.Text.Contains("真实来源"), "来源采集不应显示真实/模拟目录筛选器。");
            originalSource = (await api.Get("api/admin/crawl/sources")).Items().Single(source => source.Text("id") == "crossref").DeepClone();
            AssertSmoke(originalSource.Flag("enabled") && !originalSource.Flag("scheduleEnabled"),
                "请在已启用 Crossref、未启用定时计划的本机演示 API 上运行；验收不会开启来源或真实定时计划。");
            checks.Add("administrator-navigation-and-source-entry");
            var deprecatedSource = FindCrawlSource("lynu-patents");
            AssertSmoke(deprecatedSource is { Deprecated: true, Available: false } && deprecatedSource.Label.Contains("已弃用"),
                "服务器没有保留已弃用 LYNU 的历史元信息。");
            AssertSmoke(CrawlSource.Items.OfType<CrawlSourceVm>().All(source => source.Available && !source.Deprecated) &&
                !CrawlSource.Items.OfType<CrawlSourceVm>().Any(source => source.Id == "lynu-patents"),
                "已弃用来源仍出现在新建任务或配置选择列表中。");
            checks.Add("deprecated-source-hidden-from-create-and-settings");
            var historicalTask = CrawlTasks.Items.OfType<CrawlTaskVm>().FirstOrDefault(task => task.Data.Text("sourceId") == "lynu-patents");
            if (historicalTask != null)
            {
                busy = true;
                try
                {
                    CrawlTasks.SelectedItem = historicalTask; await LoadCrawlDetail(historicalTask.Id);
                    AssertSmoke(crawlSelectedDetail?.Text("id") == historicalTask.Id && historicalTask.SourceLabel.Contains("已弃用") &&
                        CrawlTaskSummary.Text.Contains(deprecatedSource!.UnavailableReason) && !CrawlStart.IsEnabled && !CrawlRetry.IsEnabled && !CrawlFollowup.IsEnabled,
                        "已弃用来源历史详情不可读，或仍允许启动、重试、续建。");
                    AssertSmoke(CrawlOpenCatalog.IsEnabled == (crawlSelectedDetail!.Number("publicationRevision") > 0),
                        "弃用来源已发布的成果目录入口没有保留。");
                    if (CrawlRawPages.SelectedItem is CrawlPageVm historicalPage)
                    {
                        var originalPage = await api.Get($"api/admin/crawl/tasks/{historicalTask.Id}/pages/{historicalPage.Number}");
                        AssertSmoke(originalPage.Text("taskId") == historicalTask.Id && originalPage.Text("rawJson").Length > 0,
                            "弃用来源的已存档原始页不可读。");
                    }
                    report["deprecatedHistory"] = new JsonObject { ["checked"] = true, ["taskId"] = historicalTask.Id };
                    checks.Add("deprecated-history-readable-without-restart");
                }
                finally { busy = false; }
            }
            else report["deprecatedHistory"] = new JsonObject { ["checked"] = false, ["reason"] = "当前任务页没有 LYNU 历史记录；不为验收创建弃用来源任务。" };

            AssertSmoke(ContributorAffiliation(new JsonObject { ["rawAffiliationsJson"] = "[\"来源署名大学\"]" }).Contains("来源署名大学（来源署名，未匹配规范机构）") &&
                ContributorAffiliation(new JsonObject { ["institutionName"] = "规范机构", ["rawAffiliationsJson"] = "[\"原文机构\"]" }) == "规范机构",
                "来源原署名机构未正确回显，或覆盖了已匹配的规范机构。");
            checks.Add("source-affiliation-fallback-without-entity-match");
            await SelectCrawlSmokeSource("crossref");
            AssertSmoke(CrawlCrossrefScope.Visibility == Visibility.Visible && CrawlBatchScope.Visibility == Visibility.Collapsed &&
                CrawlIncrementalMode.IsEnabled && CrawlScheduleEnabled.IsEnabled, "Crossref 范围与计划能力未正确呈现。");

            CrawlMode.SelectedIndex = 0; CrawlMaxRecords.Text = "2"; CrawlPageSize.Text = "2"; CrawlMaxPages.Text = "1";
            CrawlDoi.Text = "10.1038/nphys1170"; CrawlIssn.Clear(); CrawlQuery.Clear();
            CrawlPublicationFrom.Clear(); CrawlPublicationTo.Clear();
            CrawlTaskFormExpander.IsExpanded = true;
            CrawlContentScroll.ScrollToTop();
            await CaptureWorkspace("collection", output, screenshots);
            var beforeIds = CrawlTasks.Items.OfType<CrawlTaskVm>().Select(task => task.Id).ToHashSet();
            await ClickCrawlSmoke(CrawlCreateButton, "采集任务已创建");
            AssertSmoke(CrawlTasks.SelectedItem is CrawlTaskVm && crawlSelectedDetail != null, "创建后没有选中新任务。");
            var firstTask = crawlSelectedDetail ?? throw new InvalidOperationException("创建后任务详情缺失。");
            string firstId = firstTask.Text("id"); createdIds.Add(firstId);
            AssertSmoke(!beforeIds.Contains(firstId) && firstTask.Text("state") == "PENDING" && !firstTask.Flag("runnable") &&
                firstTask.Text("mode") == "BOUNDED" && firstTask.Number("maxRecords") == 2 &&
                firstTask.Text("doi") == "10.1038/nphys1170", "界面创建的限量 DOI 任务参数或初始状态不正确。");
            AssertSmoke(firstTask.Number("attempt") == 0 && firstTask.Number("committedPages") == 0 && CrawlStart.IsEnabled && !CrawlOpenCatalog.IsEnabled,
                "创建动作不得自动开始采集，也不能显示尚未发布的成果。");
            checks.Add("create-click-bounded-doi-remains-unstarted");
            await ClickCrawlSmoke(CrawlStop, "停止请求已提交");
            AssertSmoke(crawlSelectedDetail!.Text("id") == firstId && crawlSelectedDetail.Text("state") == "STOPPED" &&
                crawlSelectedDetail.Number("attempt") == 0 && crawlSelectedDetail.Number("received") == 0,
                "未运行的任务没有立即取消，或发生了意外执行。");
            AssertSmoke(!CrawlStart.IsEnabled && !CrawlStop.IsEnabled && !CrawlRetry.IsEnabled && CrawlFollowup.IsEnabled,
                "停止后的任务按钮状态不正确。");
            checks.Add("stop-click-cancels-unstarted-task");

            await ClickCrawlSmoke(CrawlFollowup);
            AssertSmoke(crawlParentTaskId == firstId && CrawlParentInfo.Text.Contains(ShortId(firstId)), "按此范围新建未保留前序任务关联。");
            CrawlDoi.Clear(); CrawlIssn.Clear(); CrawlQuery.Text = "wpf-crawl-ui-" + Guid.NewGuid().ToString("N")[..12];
            CrawlMode.SelectedIndex = 1;
            CrawlFromDate.SelectedDate = DateTime.UtcNow.Date.AddDays(-1); CrawlUntilDate.SelectedDate = DateTime.UtcNow.Date;
            CrawlPublicationFrom.Text = "2019"; CrawlPublicationTo.Text = "2025";
            await ClickCrawlSmoke(CrawlCreateButton, "采集任务已创建");
            string secondId = crawlSelectedDetail!.Text("id"); createdIds.Add(secondId);
            AssertSmoke(secondId != firstId && crawlSelectedDetail.Text("parentTaskId") == firstId &&
                crawlSelectedDetail.Text("mode") == "INCREMENTAL" && crawlSelectedDetail.Text("state") == "PENDING" &&
                crawlSelectedDetail.Number("fromPublicationYear") == 2019 && crawlSelectedDetail.Number("toPublicationYear") == 2025 &&
                crawlSelectedDetail.Text("fromDate") == DateTime.UtcNow.Date.AddDays(-1).ToString("yyyy-MM-dd"),
                "关联窗口增量任务未正确保存范围和发表年份。");
            await ClickCrawlSmoke(CrawlStop, "停止请求已提交");
            AssertSmoke(crawlSelectedDetail!.Text("id") == secondId && crawlSelectedDetail.Text("state") == "STOPPED" && crawlSelectedDetail.Number("attempt") == 0,
                "窗口增量验收任务未保持未执行状态。");
            checks.Add("followup-parent-and-incremental-window-through-ui");
            CrawlTaskFormExpander.IsExpanded = false; CrawlTasks.BringIntoView();
            await CaptureWorkspace("tasks", output, screenshots);

            var batchSourceIds = crawlSources.Where(source => source.Available && source.IsBatch && source.Data.Flag("enabled") && source.Batches.Count > 0).Select(source => source.Id).ToList();
            AssertSmoke(batchSourceIds.OrderBy(id => id).SequenceEqual(new[] { "cnipa-patents", "most-awards", "nsfc-projects" }) &&
                new[] { "PATENT", "PROJECT", "AWARD" }.All(type => crawlSources.Any(source => batchSourceIds.Contains(source.Id) && source.OutcomeType == type)),
                "本机 API 应启用 CNIPA 专利、MOST 获奖、NSFC 项目三个有效公告来源。");
            foreach (string sourceId in batchSourceIds)
            {
                await SelectCrawlSmokeSource(sourceId);
                var source = RequireCrawlSource();
                var originalBatchSource = source.Data.DeepClone();
                AssertSmoke(!originalBatchSource.Flag("scheduleEnabled") && !source.SupportsSchedule && !source.SupportsIncremental,
                    "公告来源不应启用窗口增量或自动定时。");
                AssertSmoke(CrawlBatchScope.Visibility == Visibility.Visible && CrawlCrossrefScope.Visibility == Visibility.Collapsed &&
                    CrawlPublicationRange.Visibility == Visibility.Collapsed && !CrawlMode.IsEnabled && CrawlMode.SelectedIndex == 0 &&
                    !CrawlIncrementalMode.IsEnabled && !CrawlScheduleEnabled.IsEnabled && CrawlScheduleEnabled.IsChecked == false &&
                    CrawlScheduleFields.Visibility == Visibility.Collapsed, "切换公告来源后表单或能力限制不正确：" + sourceId);
                AssertSmoke(crawlParentTaskId == null && crawlSettingsSourceId == sourceId &&
                    crawlSettingsVersion == source.Data.Number("configVersion"), "来源切换保留了其他来源的关联任务或设置版本。");
                var batch = CrawlBatch.SelectedItem as CrawlBatchVm ?? throw new InvalidOperationException("未选中已登记批次。");
                AssertSmoke(CrawlBatchSummary.Text.Contains(batch.Id) && CrawlBatchSummary.Text.Contains(batch.Url) &&
                    CrawlBatchSummary.Text.Contains("清单年度"), "登记批次证据未正确展示。");
                CrawlTaskFormExpander.IsExpanded = true; CrawlMaxRecords.Text = "2"; CrawlPageSize.Text = "2"; CrawlMaxPages.Text = "1";
                // A changed source must not send old Crossref scope, even if hidden fields contain stale input.
                CrawlDoi.Text = "10.1038/nphys1170"; CrawlIssn.Text = "1234-567X"; CrawlQuery.Text = "hidden-crossref-scope";
                CrawlPublicationFrom.Text = "2019"; CrawlPublicationTo.Text = "2025";
                var oldIds = CrawlTasks.Items.OfType<CrawlTaskVm>().Select(task => task.Id).ToHashSet();
                await ClickCrawlSmoke(CrawlCreateButton, "采集任务已创建");
                var batchTask = crawlSelectedDetail ?? throw new InvalidOperationException("公告任务详情缺失。");
                string batchTaskId = batchTask.Text("id"); createdIds.Add(batchTaskId);
                AssertSmoke(!oldIds.Contains(batchTaskId) && batchTask.Text("sourceId") == sourceId && batchTask.Text("batchId") == batch.Id &&
                    batchTask.Text("state") == "PENDING" && !batchTask.Flag("runnable") && batchTask.Text("mode") == "BOUNDED" &&
                    batchTask.Number("maxRecords") == 2 && batchTask.Number("pageSize") == 2 && batchTask.Number("maxPages") == 1,
                    "公告批次创建的范围、预算或初始状态不正确：" + sourceId);
                AssertSmoke(new[] { "doi", "issn", "queryText", "fromDate", "untilDate", "fromPublicationYear", "toPublicationYear" }
                    .All(field => string.IsNullOrEmpty(batchTask.Text(field))) && batchTask.Number("attempt") == 0 && batchTask.Number("received") == 0,
                    "公告批次混入 Crossref 参数，或发生了意外执行。");
                AssertSmoke(CrawlTaskSummary.Text.Contains(batch.Id) && CrawlTaskSummary.Text.Contains(source.Name) && !CrawlOpenCatalog.IsEnabled,
                    "任务详情没有显示正确来源与批次，或误开放未发布目录。");
                await ClickCrawlSmoke(CrawlStop, "停止请求已提交");
                AssertSmoke(crawlSelectedDetail!.Text("id") == batchTaskId && crawlSelectedDetail.Text("state") == "STOPPED" &&
                    crawlSelectedDetail.Number("attempt") == 0 && !CrawlStart.IsEnabled, "公告验收任务没有保持未执行且已停止状态。");
                checks.Add("registered-batch-create-stop-" + sourceId);
                CrawlContentScroll.ScrollToTop(); await CaptureWorkspace("source-" + sourceId, output, screenshots);

                // Selecting a different source must not redirect a follow-up task or a settings write.
                await SelectCrawlSmokeSource("crossref");
                await ClickCrawlSmoke(CrawlFollowup);
                AssertSmoke((CrawlSource.SelectedItem as CrawlSourceVm)?.Id == sourceId && (CrawlBatch.SelectedItem as CrawlBatchVm)?.Id == batch.Id &&
                    crawlParentTaskId == batchTaskId && crawlParentSourceId == sourceId && CrawlMode.SelectedIndex == 0,
                    "按公告范围新建没有恢复原来源、登记批次与父任务。");
                checks.Add("registered-batch-followup-restores-source-" + sourceId);

                CrawlSettingsExpander.IsExpanded = true;
                int interval = (int)originalBatchSource.Number("minIntervalMs");
                int alteredInterval = interval >= 60000 ? 59000 : interval + 1000;
                var crossrefBeforeSave = (await api.Get("api/admin/crawl/sources")).Items().Single(item => item.Text("id") == "crossref");
                batchSettingsToRestore[sourceId] = originalBatchSource;
                CrawlMinInterval.Text = alteredInterval.ToString();
                await ClickCrawlSmoke(CrawlSaveSettingsButton, "来源与服务器计划设置已保存");
                var afterSave = (await api.Get("api/admin/crawl/sources")).Items().ToList();
                var batchSaved = afterSave.Single(item => item.Text("id") == sourceId);
                var crossrefAfterSave = afterSave.Single(item => item.Text("id") == "crossref");
                AssertSmoke(batchSaved.Number("minIntervalMs") == alteredInterval && !batchSaved.Flag("scheduleEnabled") &&
                    batchSaved.Number("configVersion") > originalBatchSource.Number("configVersion") &&
                    crossrefAfterSave.Number("configVersion") == crossrefBeforeSave.Number("configVersion") &&
                    crossrefAfterSave.Number("minIntervalMs") == crossrefBeforeSave.Number("minIntervalMs"),
                    "来源设置没有独立保存，或误修改 Crossref 设置。");
                CrawlMinInterval.Text = interval.ToString();
                await ClickCrawlSmoke(CrawlSaveSettingsButton, "来源与服务器计划设置已保存");
                batchSettingsToRestore.Remove(sourceId);
                checks.Add("independent-source-settings-" + sourceId);
            }
            await SelectCrawlSmokeSource("crossref");
            CrawlSettingsExpander.IsExpanded = true;
            long originalInterval = originalSource.Number("minIntervalMs");
            int testInterval = originalInterval >= 60000 ? 59000 : (int)Math.Min(60000, originalInterval + 1000);
            CrawlMinInterval.Text = testInterval.ToString(); CrawlScheduleEnabled.IsChecked = false;
            settingsTouched = true;
            await ClickCrawlSmoke(CrawlSaveSettingsButton, "来源与服务器计划设置已保存");
            var changedSource = (await api.Get("api/admin/crawl/sources")).Items().Single(source => source.Text("id") == "crossref");
            AssertSmoke(changedSource.Number("minIntervalMs") == testInterval && !changedSource.Flag("scheduleEnabled") &&
                changedSource.Number("configVersion") > originalSource.Number("configVersion"), "来源设置未完成版本化保存，或意外开启定时计划。");
            await ClickCrawlSmoke(CrawlReloadSettingsButton);
            AssertSmoke(CrawlMinInterval.Text == testInterval.ToString() && CrawlScheduleEnabled.IsChecked == false,
                "重新读取设置没有回显服务器值。");
            CrawlSettingsExpander.BringIntoView();
            await CaptureWorkspace("source-settings", output, screenshots);
            CrawlMinInterval.Text = originalInterval.ToString();
            await ClickCrawlSmoke(CrawlSaveSettingsButton, "来源与服务器计划设置已保存");
            settingsTouched = false;
            checks.Add("source-settings-version-roundtrip-with-scheduler-disabled");

            AdminCatalogTabs.SelectedIndex = 3;
            await WaitCrawlSmokeIdle("数据质量页没有完成加载。");
            AssertSmoke(QualitySummary.Text.Contains("待复核") && QualitySummary.Text.Contains("规范成果") && QualityConflicts.IsVisible,
                "数据质量页未展示统计和只读冲突列表。");
            await CaptureWorkspace("quality", output, screenshots);
            checks.Add("read-only-quality-tab");

            AdminCatalogTabs.SelectedIndex = 0;
            await WaitCrawlSmokeIdle("返回采集页面没有完成加载。");
            WindowState = WindowState.Normal; Width = 960; Height = 560;
            CrawlTaskFormExpander.IsExpanded = true; CrawlSettingsExpander.IsExpanded = true;
            await Dispatcher.InvokeAsync(UpdateLayout, DispatcherPriority.ContextIdle);
            AssertSmoke(CrawlContentScroll.ViewportHeight > 0 && CrawlContentScroll.ScrollableHeight > 0,
                "较小窗口无法纵向访问采集表单与来源设置。");
            CrawlSaveSettingsButton.BringIntoView();
            await FlushWorkspaceLayout();
            AssertSmoke(CrawlContentScroll.VerticalOffset > 0 && CrawlSaveSettingsButton.IsVisible, "小窗口中无法滚动到设置保存操作。");
            await CaptureWorkspace("compact-settings", output, screenshots);
            WindowState = WindowState.Maximized;
            checks.Add("compact-window-scroll-access");
            report["createdTaskIds"] = new JsonArray(createdIds.Select(id => (JsonNode?)JsonValue.Create(id)).ToArray());
            report["retentionNote"] = $"{createdIds.Count} 条未启动任务以 STOPPED 状态保留；没有调用 START，也没有启用定时计划。各来源请求间隔已还原。";
            report["ok"] = true;
        }
        catch (Exception error)
        {
            report["error"] = error.ToString();
            try { await CaptureWorkspace("failure", output, screenshots); } catch { }
        }
        finally
        {
            busy = true;
            var cleanupErrors = new JsonArray();
            foreach (string id in createdIds)
            {
                try
                {
                    var task = await api.Get("api/admin/crawl/tasks/" + id);
                    if (task.Text("state") == "PENDING" && !task.Flag("runnable"))
                        await api.Post($"api/admin/crawl/tasks/{id}/actions", new { version = task.Number("version"), action = "STOP" });
                    AssertSmoke(task.Number("attempt") == 0 && task.Number("received") == 0, "验收任务发生意外执行：" + id);
                }
                catch (Exception error) { cleanupErrors.Add(error.Message); }
            }
            if (settingsTouched && originalSource != null)
            {
                try
                {
                    var latest = (await api.Get("api/admin/crawl/sources")).Items().Single(source => source.Text("id") == "crossref");
                    await api.Post("api/admin/crawl/sources/crossref/settings", new
                    {
                        version = latest.Number("configVersion"), enabled = originalSource.Flag("enabled"), minIntervalMs = originalSource.Number("minIntervalMs"),
                        scheduleEnabled = false, scheduleEveryMinutes = originalSource.Number("scheduleEveryMinutes"), scheduleIssn = originalSource.Text("scheduleIssn"),
                        schedulePageSize = originalSource.Number("schedulePageSize"), scheduleMaxPages = originalSource.Number("scheduleMaxPages"), scheduleLookbackDays = originalSource.Number("scheduleLookbackDays")
                    });
                }
                catch (Exception error) { cleanupErrors.Add("还原来源设置失败：" + error.Message); }
            }
            foreach (var original in batchSettingsToRestore)
            {
                try
                {
                    var latest = (await api.Get("api/admin/crawl/sources")).Items().Single(source => source.Text("id") == original.Key);
                    await api.Post($"api/admin/crawl/sources/{Uri.EscapeDataString(original.Key)}/settings", new
                    {
                        version = latest.Number("configVersion"), enabled = original.Value.Flag("enabled"), minIntervalMs = original.Value.Number("minIntervalMs"),
                        scheduleEnabled = false, scheduleEveryMinutes = original.Value.Number("scheduleEveryMinutes"), scheduleIssn = original.Value.Text("scheduleIssn"),
                        schedulePageSize = original.Value.Number("schedulePageSize"), scheduleMaxPages = original.Value.Number("scheduleMaxPages"), scheduleLookbackDays = original.Value.Number("scheduleLookbackDays")
                    });
                }
                catch (Exception error) { cleanupErrors.Add("还原来源设置失败（" + original.Key + "）：" + error.Message); }
            }
            try { if (api.Token != null) await api.Post("api/auth/logout", new { }); }
            catch (Exception error) { cleanupErrors.Add("注销失败：" + error.Message); }
            api.Token = null;
            if (cleanupErrors.Count > 0) { report["ok"] = false; report["cleanupErrors"] = cleanupErrors; }
            report["finishedAt"] = DateTimeOffset.UtcNow.ToString("O");
            await File.WriteAllTextAsync(output, report.ToJsonString(new JsonSerializerOptions { WriteIndented = true }));
            busy = false; Close();
        }
    }

    private async Task SelectCrawlSmokeSource(string id)
    {
        AssertSmoke(!busy, "来源切换前仍有未完成请求。");
        var source = CrawlSource.Items.OfType<CrawlSourceVm>().Single(item => item.Id == id);
        CrawlSource.BringIntoView(); CrawlSource.SelectedItem = source;
        await WaitCrawlSmokeIdle("来源切换超时：" + id);
        AssertSmoke((CrawlSource.SelectedItem as CrawlSourceVm)?.Id == id && crawlFormSourceId == id && crawlSettingsSourceId == id && crawlSettingsLoaded,
            "来源切换未同步表单和设置：" + id);
    }

    private async Task ClickCrawlSmoke(Button button, string? expectedMessage = null)
    {
        AssertSmoke(!busy, "操作前仍有未完成的界面请求。");
        button.BringIntoView(); await FlushWorkspaceLayout();
        AssertSmoke(button.IsEnabled && button.IsVisible, "验收按钮不可用：" + button.Content);
        button.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
        await WaitCrawlSmokeIdle("界面操作超时：" + button.Content);
        if (expectedMessage != null)
            AssertSmoke(Banner.Visibility == Visibility.Visible && BannerText.Text.Contains(expectedMessage), "操作未得到成功反馈：" + BannerText.Text);
    }

    private async Task WaitCrawlSmokeIdle(string failure)
    {
        var timeout = Stopwatch.StartNew();
        while (busy)
        {
            if (timeout.Elapsed > TimeSpan.FromSeconds(45)) throw new TimeoutException(failure);
            await Task.Delay(50);
        }
        await Dispatcher.InvokeAsync(UpdateLayout, DispatcherPriority.ContextIdle);
        AssertSmoke(!StatusText.Text.StartsWith("操作未完成", StringComparison.Ordinal), "界面请求失败：" + BannerText.Text);
    }
}
