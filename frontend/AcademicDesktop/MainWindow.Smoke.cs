using System.IO;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;

namespace AcademicDesktop;

public partial class MainWindow
{
    /// <summary>
    /// Explicit, sequential functional acceptance against a local demo API. This is not a load test.
    /// Creates one uniquely named synthetic account/scholar and reviews only that account's claims.
    /// Retains those records for auditability and revokes the two test sessions before closing.
    /// </summary>
    private async Task RunWorkspaceSmoke()
    {
        string output = Path.GetFullPath(Environment.GetEnvironmentVariable("ACADEMIC_SMOKE_OUTPUT")
            ?? Path.Combine(AppContext.BaseDirectory, "workspace-smoke.json"));
        Directory.CreateDirectory(Path.GetDirectoryName(output)!);
        var report = new JsonObject
        {
            ["ok"] = false,
            ["framework"] = ".NET 9 WPF",
            ["api"] = ServerAddress.Text,
            ["mode"] = "sequential-functional-acceptance; no-load-test",
            ["startedAt"] = DateTimeOffset.UtcNow.ToString("O"),
            ["retentionNote"] = "本次创建的合成账号、模拟学者及三条审核申请保留以便复核；未修改原有用户资料。"
        };
        var checks = new JsonArray();
        var screenshots = new JsonObject();
        report["checks"] = checks;
        report["screenshots"] = screenshots;
        ApiClient researcherApi = api;
        ApiClient? adminApi = null;
        string testUserId = "";
        busy = true; // Prevent SelectionChanged handlers from starting unrelated API calls.
        try
        {
            AssertSmoke(Uri.TryCreate(ServerAddress.Text, UriKind.Absolute, out var endpoint) && endpoint.IsLoopback,
                "功能验收只允许本机演示 API，避免修改远程服务器数据。");
            AssertSmoke(account == null && api.Token == null, "工作区验收须从访客入口启动。");
            AssertSmoke(WindowState == WindowState.Maximized, "启动窗口没有默认最大化。");
            AssertSmoke(WorkspaceNavIndices().SequenceEqual(new[] { 0, 1, 2, 3, 4 }), "访客侧栏应为四个公共页面和个人主页。");
            AssertSmoke(Enumerable.Range(7, 3).All(i => !((TabItem)Pages.Items[i]).IsEnabled), "访客不应能通过内置标签导航进入管理员页。");
            Pages.SelectedIndex = 9;
            AssertSmoke(Pages.SelectedIndex == 0, "内部页面选择缺少身份守卫。");
            SwitchPage(4);
            await LoadProfile();
            AssertSmoke(ProfileName.Text == "未登录" && ProfileFields.Visibility == Visibility.Collapsed &&
                ProfileRole.Visibility == Visibility.Collapsed && GuestLogin.Visibility == Visibility.Visible,
                "访客个人主页未正确隐藏资料或显示登录入口。");
            CheckWorkspaceIcons();
            checks.Add("guest-navigation-and-profile");
            checks.Add("private-tab-selection-guard");
            checks.Add("all-svg-icons-render-visible-pixels");
            await CaptureWorkspace("guest", output, screenshots);

            string suffix = DateTime.UtcNow.ToString("yyyyMMddHHmmss") + Guid.NewGuid().ToString("N")[..6];
            string username = "ui_" + suffix;
            string password = "FunctionalOnly!" + Guid.NewGuid().ToString("N");
            await api.Post("api/auth/register", new { username, password, displayName = "界面验收账号" });
            var signedIn = await api.Post("api/auth/login", new { username, password });
            api.Token = signedIn.Text("token");
            account = signedIn["user"]!.DeepClone();
            testUserId = account.Text("id");
            report["createdUsername"] = username;
            report["createdUserId"] = testUserId;
            AssertSmoke(account.Text("role") == "USER", "注册不应直接授予科研或管理员角色。");
            ConfigureWorkspace(); UpdateAccount();
            AssertSmoke(WorkspaceNavIndices().SequenceEqual(new[] { 0, 1, 2, 3, 4, 5, 6 }), "登录用户应可见个人主页、个人成果及我的申请。");
            AssertSmoke(!CanAccessPage(7) && !CanAccessPage(8) && !CanAccessPage(9), "非管理员访问控制失效。");
            await api.Post("api/me/profile", new
            {
                displayName = "界面验收 · 科研人员",
                orcid = "0000-0002-1825-0097",
                websites = new[] { new { label = "我的博客", url = "https://example.org/research" }, new { label = "GitHub", url = "https://github.com" } },
                aboutMe = "合成验收资料：研究学术信息组织、可追溯成果管理与桌面交互。",
                version = account.Number("profileVersion")
            });
            await LoadProfile();
            AssertSmoke(ProfileName.Text == "界面验收 · 科研人员" && ProfileOrcid.Text == "0000-0002-1825-0097" &&
                ProfileAbout.Text.Contains("合成验收资料") && WebsiteLinks.Children.OfType<Button>().Count() == 2,
                "个人资料保存后未正确回显。");
            AssertSmoke(WebsiteLinks.Children.OfType<Button>().All(b => Uri.TryCreate(b.ToolTip?.ToString(), UriKind.Absolute, out var link) && link.Scheme == "https"),
                "网站按钮没有有效的 HTTPS 目标。");
            checks.Add("registered-user-navigation-and-profile-persistence");
            await CaptureWorkspace("profile", output, screenshots);

            await ShowCertification();
            await FlushWorkspaceLayout();
            AssertSmoke(CertificationOverlay.IsVisible && PortalChoice.Visibility == Visibility.Collapsed,
                "新用户认证抽屉没有显示身份核验步骤。");
            AssertSmoke(CertificationInstitution.Items.Count > 0 && string.IsNullOrEmpty(CertificationEvidence.Text),
                "认证机构或空白材料输入状态异常。");
            double drawerBefore = CertificationWidth.ActualWidth;
            var splitter = CertificationOverlay.Children.OfType<GridSplitter>().Single();
            splitter.Focus();
            splitter.RaiseEvent(new KeyEventArgs(Keyboard.PrimaryDevice, PresentationSource.FromVisual(splitter)!, Environment.TickCount, Key.Left)
                { RoutedEvent = Keyboard.KeyDownEvent });
            await FlushWorkspaceLayout();
            AssertSmoke(Math.Abs(CertificationWidth.ActualWidth - drawerBefore) >= 1,
                "认证抽屉的 GridSplitter 未响应键盘宽度调整。");
            report["drawerInitialWidth"] = drawerBefore;
            report["drawerResizedWidth"] = CertificationWidth.ActualWidth;
            await CaptureWorkspace("drawer", output, screenshots);
            CloseCertificationButton.RaiseEvent(new KeyEventArgs(Keyboard.PrimaryDevice, PresentationSource.FromVisual(CloseCertificationButton)!, Environment.TickCount, Key.Escape)
                { RoutedEvent = Keyboard.PreviewKeyDownEvent });
            AssertSmoke(CertificationOverlay.Visibility == Visibility.Collapsed, "Escape 未关闭认证抽屉。");
            checks.Add("certification-overlay-resize-and-escape");

            string institutionId = ((ReferenceItem)CertificationInstitution.Items[0]).Id;
            string evidence = $"合成功能验收；账号 {username}；认证机构 {institutionId}；不代表真实机构认证。";
            await CreateAndSubmit("IDENTITY", testUserId, evidence, "");
            SwitchPage(6); claimsPage = 0; await LoadMine();
            var identity = MyClaims.Items.OfType<ClaimVm>().Single(c => c.Data.Text("kind") == "IDENTITY");
            AssertSmoke(identity.KindLabel == "门户认证申请" && identity.StateLabel == "待审核", "身份申请类型或进度标签不正确。");
            AssertSmoke(MyClaims.Items.OfType<ClaimVm>().All(c => c.Data.Text("userId") == testUserId), "我的申请包含他人数据。");
            MyClaims.SelectedItem = identity;
            await CaptureWorkspace("applications", output, screenshots);
            checks.Add("private-applications-type-and-submission");

            adminApi = new ApiClient(ServerAddress.Text);
            var adminLogin = await adminApi.Post("api/auth/login", new
            {
                username = Environment.GetEnvironmentVariable("ACADEMIC_SMOKE_ADMIN_USERNAME") ?? "admin",
                password = Environment.GetEnvironmentVariable("ACADEMIC_SMOKE_ADMIN_PASSWORD") ?? "DemoPass2026!"
            });
            adminApi.Token = adminLogin.Text("token");
            var adminAccount = adminLogin["user"]!.DeepClone();
            AssertSmoke(adminAccount.Text("role") == "ADMIN", "验收审核账号不是管理员。");
            await ApproveSmokeClaim(adminApi, identity.Id, testUserId);
            await LoadProfile();
            AssertSmoke(account!.Text("role") == "RESEARCHER", "身份申请通过后账号没有刷新科研角色。");

            string scholarId = "UI-SMOKE-" + suffix;
            await adminApi.Post("api/admin/scholars", new { id = scholarId, name = "界面验收模拟学者", institutionId, bio = "合成功能验收学者，非真实人员。", simulated = true });
            report["createdScholarId"] = scholarId;
            await CreateAndSubmit("PORTAL", scholarId, evidence + " 门户认领验证。", "");
            await LoadMine();
            var portal = MyClaims.Items.OfType<ClaimVm>().Single(c => c.Data.Text("kind") == "PORTAL");
            AssertSmoke(portal.KindLabel == "门户认证申请", "门户申请类型标签不正确。");
            await ApproveSmokeClaim(adminApi, portal.Id, testUserId);
            await LoadProfile();
            AssertSmoke(account!.Text("scholarId") == scholarId && CertificationSummary.Text.Contains(scholarId), "门户绑定未展示在个人主页。");
            checks.Add("identity-and-portal-review-flow");

            var workResponse = await api.Get("api/works?dataset=demo&type=PAPER&size=1");
            var work = new WorkVm(workResponse["items"]!.Items().First());
            AssertSmoke(work.Data.Flag("simulated"), "验收成果必须使用模拟资料。");
            OpenComposer(work);
            AssertSmoke(Pages.SelectedIndex == 6 && ApplicationComposer.Visibility == Visibility.Visible &&
                ApplicationWork.SelectedItem is WorkVm selectedWork && selectedWork.Id == work.Id, "成果申报未打开我的申请中的撰写页面。");
            ApplicationEvidence.Text = evidence + " 合成论文成果贡献验证。";
            await CaptureWorkspace("composer", output, screenshots);
            await CreateAndSubmit("OUTCOME", work.Id, ApplicationEvidence.Text, work.ContributionRole);
            ApplicationComposer.Visibility = Visibility.Collapsed;
            await LoadMine();
            var outcome = MyClaims.Items.OfType<ClaimVm>().Single(c => c.Data.Text("kind") == "OUTCOME");
            AssertSmoke(outcome.KindLabel == "成果申领", "成果申请类型标签不正确。");
            await ApproveSmokeClaim(adminApi, outcome.Id, testUserId);
            SwitchPage(5); await LoadMine();
            AssertSmoke(MyWorks.Items.OfType<WorkVm>().Any(w => w.Id == work.Id), "审核通过的成果没有进入个人成果页。");
            report["claimIds"] = new JsonArray(identity.Id, portal.Id, outcome.Id);
            report["claimedDemoWorkId"] = work.Id;
            checks.Add("outcome-composer-review-and-personal-outcomes");
            await CaptureWorkspace("outcomes", output, screenshots);
            SwitchPage(4); await LoadProfile();
            await CaptureWorkspace("verified-profile", output, screenshots);

            api = adminApi; account = adminAccount;
            ClearPrivateViews(); ConfigureWorkspace(); UpdateAccount();
            AssertSmoke(WorkspaceNavIndices().SequenceEqual(new[] { 7, 8, 9 }), "管理员侧栏必须且仅包含三个管理页面。");
            AssertSmoke(!CanAccessPage(0) && !CanAccessPage(4) && !CanAccessPage(6), "管理员工作区包含普通个人页面。");
            Dataset.SelectedIndex = 0;
            SwitchPage(7); await LoadAdminCatalog();
            AssertSmoke(AdminWorks.Items.Count > 0, "管理员成果目录未加载。");
            await CaptureWorkspace("admin-crawl", output, screenshots);
            AdminCatalogTabs.SelectedIndex = 1;
            await CaptureWorkspace("admin-catalog", output, screenshots);
            SwitchPage(8); reviewPage = 0; await LoadAdmin();
            AssertSmoke(ReviewGrid.Items.OfType<ClaimVm>().Any(c => c.Id == outcome.Id), "管理员队列未包含本次申请。");
            await CaptureWorkspace("admin-applications", output, screenshots);
            SwitchPage(9); await LoadAdminStats();
            AssertSmoke(AdminMetricCards.Children.Count == 6 && AdminTypeChart.Children.Count > 0 && AdminStateChart.Children.Count > 0,
                "管理员统计卡片或分布图未加载。");
            await CaptureWorkspace("admin", output, screenshots);
            checks.Add("administrator-three-page-workspace");
            report["ok"] = true;
        }
        catch (Exception error)
        {
            report["error"] = error.ToString();
            try { await CaptureWorkspace("failure", output, screenshots); } catch { /* Keep the primary failure. */ }
        }
        finally
        {
            var logoutErrors = new JsonArray();
            foreach (var client in new[] { researcherApi, adminApi }.OfType<ApiClient>().Distinct())
            {
                try { if (client.Token != null) await client.Post("api/auth/logout", new { }); }
                catch (Exception error) { logoutErrors.Add(error.Message); }
                finally { client.Token = null; }
            }
            if (logoutErrors.Count > 0) { report["ok"] = false; report["logoutErrors"] = logoutErrors; }
            report["finishedAt"] = DateTimeOffset.UtcNow.ToString("O");
            await File.WriteAllTextAsync(output, report.ToJsonString(new JsonSerializerOptions { WriteIndented = true }));
            if (!ReferenceEquals(researcherApi, api)) researcherApi.Dispose();
            if (adminApi != null && !ReferenceEquals(adminApi, api)) adminApi.Dispose();
            busy = false;
            Close();
        }
    }

    private int[] WorkspaceNavIndices() => Navigation.Children.OfType<Button>().Select(button => Convert.ToInt32(button.Tag)).ToArray();

    private static void AssertSmoke(bool condition, string message)
    {
        if (!condition) throw new InvalidOperationException(message);
    }

    private static async Task ApproveSmokeClaim(ApiClient reviewer, string id, string expectedUserId)
    {
        var claim = await reviewer.Get("api/claims/" + id);
        AssertSmoke(claim.Text("userId") == expectedUserId && claim.Text("state") == "PENDING_REVIEW",
            "仅允许处理本次合成账号新提交的待审核申请。");
        claim = await reviewer.Post($"api/claims/{id}/actions", new { version = claim.Number("version"), action = "TAKE", reason = "合成功能验收领取", evidence = (string?)null });
        claim = await reviewer.Post($"api/claims/{id}/actions", new { version = claim.Number("version"), action = "APPROVE", reason = "仅合成测试资料，验证界面与审核事务闭环。", evidence = (string?)null });
        AssertSmoke(claim.Text("state") == "APPROVED", "管理员审核未通过。");
    }

    private void CheckWorkspaceIcons()
    {
        foreach (var button in Navigation.Children.OfType<Button>())
        {
            var icon = ((StackPanel)button.Content).Children.OfType<SvgIcon>().Single();
            AssertSmoke(icon.Width == 20 && icon.Height == 20, "侧栏 SVG 尺寸不统一。");
        }
        foreach (string source in new[] { "discovery", "scholars", "statistics", "graph", "profile", "outcomes", "applications", "database", "review" }
            .Select(name => $"Assets/Navigation/{name}.svg").Append("Assets/avatar-default.svg"))
        {
            var icon = new SvgIcon { Source = source, Width = 32, Height = 32, Foreground = Brushes.White };
            icon.Measure(new Size(32, 32)); icon.Arrange(new Rect(0, 0, 32, 32)); icon.UpdateLayout();
            var image = new RenderTargetBitmap(32, 32, 96, 96, PixelFormats.Pbgra32);
            image.Render(icon);
            var pixels = new byte[32 * 32 * 4]; image.CopyPixels(pixels, 32 * 4, 0);
            AssertSmoke(Enumerable.Range(0, 32 * 32).Any(i => pixels[i * 4 + 3] > 0), "SVG 未绘制出可见像素：" + source);
        }
    }

    private async Task FlushWorkspaceLayout()
    {
        await Dispatcher.InvokeAsync(UpdateLayout, DispatcherPriority.Render);
    }

    private async Task CaptureWorkspace(string name, string output, JsonObject screenshots)
    {
        await FlushWorkspaceLayout();
        var visual = (FrameworkElement)Content;
        var image = new RenderTargetBitmap(Math.Max(1, (int)Math.Ceiling(visual.ActualWidth)),
            Math.Max(1, (int)Math.Ceiling(visual.ActualHeight)), 96, 96, PixelFormats.Pbgra32);
        image.Render(visual);
        var encoder = new PngBitmapEncoder(); encoder.Frames.Add(BitmapFrame.Create(image));
        string path = Path.Combine(Path.GetDirectoryName(output)!, Path.GetFileNameWithoutExtension(output) + "-" + name + ".png");
        using (var stream = File.Create(path)) encoder.Save(stream);
        screenshots[name] = path;
    }
}
