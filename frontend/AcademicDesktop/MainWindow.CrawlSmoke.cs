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
        try
        {
            AssertSmoke(Uri.TryCreate(ServerAddress.Text, UriKind.Absolute, out var endpoint) && endpoint.IsLoopback,
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
            report["retentionNote"] = "两条未启动任务以 STOPPED 状态保留；没有调用 START，也没有启用定时计划。来源请求间隔已还原。";
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
            try { if (api.Token != null) await api.Post("api/auth/logout", new { }); }
            catch (Exception error) { cleanupErrors.Add("注销失败：" + error.Message); }
            api.Token = null;
            if (cleanupErrors.Count > 0) { report["ok"] = false; report["cleanupErrors"] = cleanupErrors; }
            report["finishedAt"] = DateTimeOffset.UtcNow.ToString("O");
            await File.WriteAllTextAsync(output, report.ToJsonString(new JsonSerializerOptions { WriteIndented = true }));
            busy = false; Close();
        }
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
