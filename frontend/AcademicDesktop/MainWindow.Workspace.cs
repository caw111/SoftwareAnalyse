using System.Text.Json.Nodes;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;

namespace AcademicDesktop;

public partial class MainWindow
{
    private const int ApplicationPageSize = 20;
    private int claimsPage, reviewPage, adminPage;
    private long? adminRevision;
    private string? adminActiveQuery;
    private long profileEditVersion;
    private IInputElement? drawerReturnFocus;

    private bool configuringNavigation;
    private bool IsAdmin => account?.Text("role") == "ADMIN";
    private bool CanAccessPage(int index) => IsAdmin ? index is 7 or 8 or 9 : index is >= 0 and <= 4 || (account != null && index is 5 or 6);
    private void SetBusyState(bool value)
    {
        Pages.IsEnabled = !value; Navigation.IsEnabled = !value; Dataset.IsEnabled = !value;
        SessionButton.IsEnabled = !value; CertificationForm.IsEnabled = !value;
    }
    private void ConfigureWorkspace()
    {
        configuringNavigation = true;
        for (int i = 0; i < Pages.Items.Count; i++) ((TabItem)Pages.Items[i]).IsEnabled = CanAccessPage(i);
        Navigation.Children.Clear();
        void Heading(string text) => Navigation.Children.Add(new TextBlock { Text = text, FontSize = 10, Foreground = Brush("#81A3AE"), Margin = new Thickness(28, 16, 0, 12) });
        void Nav(int index, string icon)
        {
            var content = new StackPanel { Orientation = Orientation.Horizontal };
            content.Children.Add(new SvgIcon { Source = $"Assets/Navigation/{icon}.svg", Width = 20, Height = 20, Margin = new Thickness(0, 0, 12, 0) });
            content.Children.Add(new TextBlock { Text = titles[index] });
            var button = new Button { Content = content, Tag = index, Style = (Style)FindResource("Nav") };
            System.Windows.Automation.AutomationProperties.SetName(button, titles[index]);
            button.Click += Navigate; Navigation.Children.Add(button);
        }
        if (IsAdmin) { Heading("管理 / ADMINISTRATION"); Nav(7, "database"); Nav(8, "review"); Nav(9, "statistics"); }
        else
        {
            Heading("探索 / EXPLORE"); Nav(0, "discovery"); Nav(1, "scholars"); Nav(2, "statistics"); Nav(3, "graph");
            Heading("个人 / PERSONAL"); Nav(4, "profile");
            if (account != null) { Nav(5, "outcomes"); Nav(6, "applications"); }
        }
        if (!ready || !CanAccessPage(Pages.SelectedIndex)) Pages.SelectedIndex = IsAdmin ? 7 : account == null ? 0 : 4;
        HighlightNavigation(Pages.SelectedIndex);
        configuringNavigation = false;
    }
    private async void PageSelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (!ready || configuringNavigation || e.Source != Pages) return;
        if (!CanAccessPage(Pages.SelectedIndex)) { ConfigureWorkspace(); return; }
        HighlightNavigation(Pages.SelectedIndex);
        if (!busy) await Run(LoadPage);
    }
    private void SwitchPage(int index)
    {
        if (!CanAccessPage(index)) throw new InvalidOperationException("当前身份不能访问此页面。");
        Pages.SelectedIndex = index; HighlightNavigation(index);
    }
    private void UpdateAccount()
    {
        SidebarUser.Text = account == null ? "访客模式" : account.Text("displayName") + " · " + (account.Text("role") == "USER" ? "待认证" : Labels.Role(account.Text("role")));
        PublicPortalApply.Visibility = account != null && !IsAdmin ? Visibility.Visible : Visibility.Collapsed;
        SessionButton.Content = account == null ? "登录 / 注册" : "退出登录";
        ProfileName.Text = account?.Text("displayName") ?? "未登录";
        ProfileRole.Text = account == null ? "" : account.Text("role") == "USER" ? "账号已注册 · 等待科研身份认证" : Labels.Role(account.Text("role"));
        ProfileRole.Visibility = account == null ? Visibility.Collapsed : Visibility.Visible;
        GuestLogin.Visibility = account == null ? Visibility.Visible : Visibility.Collapsed;
        EditProfileButton.Visibility = account == null ? Visibility.Collapsed : Visibility.Visible;
        ProfileFields.Visibility = account == null ? Visibility.Collapsed : Visibility.Visible;
        if (account == null) { ProfileEditor.Visibility = Visibility.Collapsed; return; }
        ProfileOrcid.Text = account.Text("orcid") is { Length: > 0 } orcid ? orcid : "尚未填写";
        ProfileAbout.Text = account.Text("aboutMe") is { Length: > 0 } about ? about : "介绍你的研究方向、学术成就或正在关注的问题。";
        CertificationSummary.Text = account.Text("scholarId") is { Length: > 0 } scholar
            ? $"已认证 · {account.Text("scholarName")} · {account.Text("institutionName")}\n门户标识：{scholar}"
            : account.Text("role") == "RESEARCHER" ? "科研身份已通过 · 尚未认领学者门户" : "尚未认证 · 提交机构身份材料，由管理员审核";
        WebsiteLinks.Children.Clear();
        if (account["websites"] is JsonArray sites && sites.Count > 0)
            foreach (var site in sites.Items())
            {
                string url = site.Text("url"); var button = SecondaryButton(site.Text("label", url) + " ↗");
                button.ToolTip = url; button.Margin = new Thickness(0, 0, 12, 8); button.Click += (_, _) => OpenLink(url); WebsiteLinks.Children.Add(button);
            }
        else WebsiteLinks.Children.Add(Text("尚未添加博客、GitHub 或个人网站", 12, false, "#72858F"));
    }
    private void ClearPrivateViews()
    {
        MyClaims.ItemsSource = null; MyWorks.ItemsSource = null; ReviewGrid.ItemsSource = null; ImportsGrid.ItemsSource = null;
        ReviewEvidence.Clear(); ReviewReason.Clear(); SupplementEvidence.Clear(); CertificationEvidence.Clear();
        ApplicationEvidence.Clear(); ApplicationWork.ItemsSource = null; ProfileEditor.Visibility = Visibility.Collapsed; ApplicationComposer.Visibility = Visibility.Collapsed;
        AdminMetricCards.Children.Clear(); AdminTypeChart.Children.Clear(); AdminStateChart.Children.Clear(); AdminStatsContext.Text = "";
        AdminWorks.ItemsSource = null; AdminWorkDetail.Clear(); EditName.Clear(); EditOrcid.Clear(); EditWebsites.Clear(); EditAbout.Clear();
        claimsPage = reviewPage = 0; MyClaimReason.Text = "登录后查看本人申请";
    }
    private async void ChangeSession(object sender, RoutedEventArgs e)
    {
        if (busy) return;
        await Run(async () =>
        {
            try { if (api.Token != null) await api.Post("api/auth/logout", new { }); }
            finally { api.Token = null; account = null; ClearPrivateViews(); }
        });
        changingSession = true;
        string address = ServerAddress.Text;
        Close();
        ((App)Application.Current).OpenEntry(address);
    }
    private async Task LoadProfile()
    {
        if (account != null) { account = await api.Get("api/auth/me"); ConfigureWorkspace(); }
        UpdateAccount();
    }
    private async Task LoadMine()
    {
        RequireAccount();
        await LoadProfile();
        if (Pages.SelectedIndex == 5)
        {
            var works = account!.Text("role") == "RESEARCHER" ? (await api.Get("api/me/outcomes")).Items().Select(w => new WorkVm(w)).ToList() : [];
            MyWorks.ItemsSource = works;
            MyWorksSummary.Text = works.Count > 0 ? $"共 {works.Count} 项已认证成果 · 按审核通过的个人贡献展示" : "暂无已认证成果。完成门户认证后，可在“我的申请”申报成果。";
        }
        if (Pages.SelectedIndex == 6)
        {
            var response = await api.Get($"api/claims?page={claimsPage}&size={ApplicationPageSize}");
            MyClaims.ItemsSource = response["items"]!.Items().Select(c => new ClaimVm(c)).ToList();
            UpdatePager(response, ClaimsPageInfo, ClaimsPrevious, ClaimsNext);
        }
    }
    private async void RefreshMine(object sender, RoutedEventArgs e) => await Run(LoadMine);
    private static void UpdatePager(JsonNode response, TextBlock label, Button previous, Button next)
    {
        long current = response.Number("page"), size = response.Number("size"), count = response.Number("total");
        label.Text = $"{current + 1} / {Math.Max(1, (count + size - 1) / size)} 页 · 共 {count} 份";
        previous.IsEnabled = current > 0; next.IsEnabled = (current + 1) * size < count;
    }
    private async void ClaimsPage(object sender, RoutedEventArgs e) => await Run(async () => { claimsPage = Math.Max(0, claimsPage + int.Parse(((Button)sender).Tag.ToString()!)); await LoadMine(); });
    private async void ReviewPage(object sender, RoutedEventArgs e) => await Run(async () => { reviewPage = Math.Max(0, reviewPage + int.Parse(((Button)sender).Tag.ToString()!)); await LoadAdmin(); });
    private void EditProfile(object sender, RoutedEventArgs e)
    {
        if (account == null) return;
        EditName.Text = account.Text("displayName"); EditOrcid.Text = account.Text("orcid"); EditAbout.Text = account.Text("aboutMe");
        EditWebsites.Text = account["websites"] is JsonArray sites ? string.Join("\n", sites.Items().Select(s => s.Text("label") + " | " + s.Text("url"))) : "";
        profileEditVersion = account.Number("profileVersion"); ProfileFields.Visibility = Visibility.Collapsed; ProfileEditor.Visibility = Visibility.Visible;
        EditName.Focus(); EditName.BringIntoView();
    }
    private void CancelProfileEdit(object sender, RoutedEventArgs e) { ProfileEditor.Visibility = Visibility.Collapsed; UpdateAccount(); }
    private async void SaveProfile(object sender, RoutedEventArgs e) => await Run(async () =>
    {
        RequireAccount();
        var sites = EditWebsites.Text.Split('\n', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries).Select(line =>
        {
            var parts = line.Split('|', 2, StringSplitOptions.TrimEntries);
            if (parts.Length != 2 || string.IsNullOrWhiteSpace(parts[0])) throw new InvalidOperationException("网站请按“名称 | https://网址”填写，每行一个。");
            return new { label = parts[0], url = parts[1] };
        }).ToArray();
        try
        {
            account = await api.Post("api/me/profile", new { displayName = EditName.Text.Trim(), orcid = EditOrcid.Text.Trim(), websites = sites, aboutMe = EditAbout.Text.Trim(), version = profileEditVersion });
            ProfileEditor.Visibility = Visibility.Collapsed; UpdateAccount(); ShowMessage("个人资料已保存。");
        }
        catch (ApiFailure ex) when (ex.Status == 409)
        {
            // Keep the edited values visible; cancel + edit explicitly reloads the latest revision.
            account = await api.Get("api/auth/me");
            throw new InvalidOperationException("资料已在另一处更新，本次未覆盖。当前输入已保留，请复制后取消编辑，查看最新资料再合并修改。");
        }
    });
    private async void OpenCertification(object sender, RoutedEventArgs e) => await Run(() => ShowCertification());
    private async Task ShowCertification(ScholarVm? selected = null)
    {
        RequireAccount();
        if (IsAdmin) throw new InvalidOperationException("管理员请在申请管理中处理认证。");
        account = await api.Get("api/auth/me"); UpdateAccount();
        drawerReturnFocus = Keyboard.FocusedElement;
        CertificationWidth.Width = new GridLength(Math.Clamp(ActualWidth * .25, 320, Math.Max(320, ActualWidth * .7)));
        CertificationOverlay.Visibility = Visibility.Visible; CertificationError.Text = "";
        bool identity = account.Text("role") == "USER", bound = account.Text("scholarId") != "";
        CertificationStage.Text = bound ? "学术门户已认证。认证信息可在个人主页查看。"
            : identity ? "第 1 步 · 科研身份核验\n先由管理员审核机构身份，通过后在此选择并认领你的学者门户。"
            : "第 2 步 · 学者门户认领\n科研身份已通过，请选择机构和对应的学者门户，提交认领依据。";
        PortalChoice.Visibility = identity || bound ? Visibility.Collapsed : Visibility.Visible;
        CertificationSubmit.IsEnabled = !bound;
        CertificationSubmit.Content = identity ? "提交身份核验申请" : "提交门户认证申请";
        if (CertificationInstitution.Items.Count == 0) await LoadReference();
        if (selected != null) CertificationInstitution.SelectedValue = selected.Data.Text("institutionId");
        else if (CertificationInstitution.SelectedIndex < 0 && CertificationInstitution.Items.Count > 0) CertificationInstitution.SelectedIndex = 0;
        if (!identity && !bound)
        {
            if (selected != null) CertificationScholarSearch.Text = selected.Id;
            await LoadCertificationScholars();
            if (selected != null) CertificationScholar.SelectedValue = selected.Id;
        }
        CloseCertificationButton.Focus();
    }
    private void HideCertification()
    {
        CertificationOverlay.Visibility = Visibility.Collapsed;
        if (drawerReturnFocus != null) Keyboard.Focus(drawerReturnFocus);
    }
    private void CloseCertification(object sender, RoutedEventArgs e) => HideCertification();
    private void DismissCertification(object sender, MouseButtonEventArgs e) => HideCertification();
    private void WindowKeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key == Key.Escape && CertificationOverlay.Visibility == Visibility.Visible) { HideCertification(); e.Handled = true; }
    }
    private void WindowSizeChanged(object sender, SizeChangedEventArgs e)
    {
        if (CertificationWidth != null && CertificationOverlay.Visibility == Visibility.Visible && ActualWidth > 0)
            CertificationWidth.Width = new GridLength(Math.Clamp(CertificationWidth.ActualWidth, 300, Math.Max(300, ActualWidth * .75)));
    }
    private async void CertificationInstitutionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (!ready || busy || CertificationOverlay.Visibility != Visibility.Visible) return;
        await Run(LoadCertificationScholars);
    }
    private async void FindCertificationScholars(object sender, RoutedEventArgs e) => await Run(LoadCertificationScholars);
    private async Task LoadCertificationScholars()
    {
        var response = await api.Get("api/scholars?dataset=" + DataScope + "&q=" + Uri.EscapeDataString(CertificationScholarSearch.Text.Trim()));
        var choices = response.Items().Select(s => new ScholarVm(s)).Where(s => s.Data.Text("institutionId") == SelectedId(CertificationInstitution)).ToList();
        CertificationScholar.ItemsSource = choices; CertificationScholar.SelectedIndex = choices.Count > 0 ? 0 : -1;
    }
    private async void SubmitCertification(object sender, RoutedEventArgs e) => await Run(async () =>
    {
        RequireAccount();
        if (CertificationInstitution.SelectedItem is not ReferenceItem institution) throw new InvalidOperationException("请选择认证机构。");
        if (string.IsNullOrWhiteSpace(CertificationEvidence.Text)) throw new InvalidOperationException("请填写机构身份与核验材料。");
        account = await api.Get("api/auth/me");
        bool identity = account.Text("role") == "USER";
        string target = identity ? account.Text("id") : SelectedId(CertificationScholar);
        if (target == "") throw new InvalidOperationException("请选择对应学者门户；可先按姓名或独立标识查找。");
        string evidence = $"认证机构：{institution.Name}（{institution.Id}）\n{CertificationEvidence.Text.Trim()}";
        // TODO: once institution authentication endpoints are registered in the database,
        // offer an explicit confirmation before opening that institution's own login in the default browser.
        // Never infer researcher verification from an external browser navigation alone.
        await CreateAndSubmit(identity ? "IDENTITY" : "PORTAL", target, evidence, "");
        CertificationEvidence.Clear(); HideCertification(); claimsPage = 0; SwitchPage(6); await LoadMine();
        ShowMessage(identity ? "身份核验申请已提交。通过后可继续认领学者门户。" : "门户认证申请已提交，等待管理员审核。");
    });
    private void OpenComposer(WorkVm? work = null)
    {
        RequireAccount(); SwitchPage(6); ApplicationComposer.Visibility = Visibility.Visible;
        if (work != null) { ApplicationWork.ItemsSource = new[] { work }; ApplicationWork.SelectedIndex = 0; ApplicationSearch.Text = work.Title; }
        ApplicationSearchInfo.Text = account!.Text("scholarId") == "" ? "请先完成门户认证，再提交成果申请。" : "";
        ApplicationSearch.Focus();
    }
    private async void NewOutcomeApplication(object sender, RoutedEventArgs e) => await Run(async () => { OpenComposer(); claimsPage = 0; await LoadMine(); });
    private void CloseComposer(object sender, RoutedEventArgs e) => ApplicationComposer.Visibility = Visibility.Collapsed;
    private async void FindApplicationWorks(object sender, RoutedEventArgs e) => await Run(SearchApplicationWorks);
    private async void ApplicationSearchKey(object sender, KeyEventArgs e) { if (e.Key == Key.Enter) await Run(SearchApplicationWorks); }
    private async Task SearchApplicationWorks()
    {
        var response = await api.Get($"api/works?dataset={DataScope}&q={Uri.EscapeDataString(ApplicationSearch.Text.Trim())}&size=50");
        var works = response["items"]!.Items().Select(w => new WorkVm(w)).ToList();
        ApplicationWork.ItemsSource = works; ApplicationWork.SelectedIndex = works.Count > 0 ? 0 : -1;
        ApplicationSearchInfo.Text = $"找到 {response.Number("total")} 项；显示前 50 项，可输入更准确的关键词。";
    }
    private async void SubmitOutcomeApplication(object sender, RoutedEventArgs e) => await Run(async () =>
    {
        RequireAccount("RESEARCHER");
        if (account!.Text("scholarId") == "") throw new InvalidOperationException("请先在个人主页完成学术门户认证。");
        if (ApplicationWork.SelectedItem is not WorkVm work) throw new InvalidOperationException("请检索并选择一项成果。");
        await CreateAndSubmit("OUTCOME", work.Id, ApplicationEvidence.Text.Trim(), work.ContributionRole);
        ApplicationEvidence.Clear(); ApplicationComposer.Visibility = Visibility.Collapsed; claimsPage = 0; await LoadMine();
        ShowMessage("成果申领申请已提交，审核通过后将出现在“个人成果”。");
    });
    private string AdminQuery() => $"dataset={DataScope}&q={Uri.EscapeDataString(AdminSearch.Text.Trim())}&type={SelectedTag(AdminType)}";
    private async Task LoadAdminCatalog()
    {
        RequireAccount("ADMIN");
        string query = AdminQuery();
        if (query != adminActiveQuery) { adminPage = 0; adminRevision = null; }
        var response = await api.Get($"api/works?{query}&page={adminPage}&size=20" + (adminRevision == null ? "" : $"&revision={adminRevision}"));
        adminActiveQuery = query; adminRevision = response.Number("revision");
        AdminWorks.ItemsSource = response["items"]!.Items().Select(w => new WorkVm(w)).ToList();
        long count = response.Number("total");
        AdminCatalogInfo.Text = $"共 {count:N0} 项 · 第 {adminPage + 1} 页 · 目录版本 {adminRevision}";
        AdminPrevious.IsEnabled = adminPage > 0; AdminNext.IsEnabled = (adminPage + 1) * 20 < count && (adminPage + 1) * 20 <= 10000;
        AdminWorkDetail.Text = "选择成果查看规范字段与原始来源。";
        ImportsGrid.ItemsSource = (await api.Get("api/admin/imports")).Items().Select(i => new ImportVm(i)).ToList();
    }
    private async void AdminSearchClick(object sender, RoutedEventArgs e) => await Run(async () => { adminPage = 0; adminRevision = null; await LoadAdminCatalog(); });
    private async void AdminPage(object sender, RoutedEventArgs e) => await Run(async () => { adminPage = Math.Max(0, adminPage + int.Parse(((Button)sender).Tag.ToString()!)); await LoadAdminCatalog(); });
    private async void AdminWorkSelected(object sender, SelectionChangedEventArgs e)
    {
        if (busy || AdminWorks.SelectedItem is not WorkVm work) return;
        await Run(async () =>
        {
            var detail = await api.Get($"api/works/{work.Id}?revision={adminRevision}");
            AdminWorkDetail.Text = $"{work.Title}\n{Labels.Type(work.Type)} · {detail.Text("dateValue")} · {detail.Text("doi", detail.Text("identifier"))}\n{detail.Text("abstractText")}\n来源：\n" +
                string.Join("\n", detail["sources"]!.Items().Select(s => $"{s.Text("sourceName")} · {s.Text("sourceKey")}\n{s.Text("sourceUrl")}\nSHA-256: {s.Text("checksum")}"));
        });
    }
    private async void AdminStatsClick(object sender, RoutedEventArgs e) => await Run(LoadAdminStats);
    private async Task LoadAdminStats()
    {
        RequireAccount("ADMIN"); var data = await api.Get("api/admin/statistics"); AdminMetricCards.Children.Clear();
        foreach (var item in new[] { ("规范成果", "catalogTotal"), ("注册账号", "users"), ("科研人员", "researchers"), ("待审核申请", "pendingApplications"), ("审核中申请", "reviewingApplications"), ("已通过申请", "approvedApplications") })
        {
            var panel = new StackPanel(); panel.Children.Add(Text(item.Item1, 12, false, "#72858F")); panel.Children.Add(Text(data.Number(item.Item2).ToString("N0"), 28, true, "#087F78"));
            AdminMetricCards.Children.Add(new Border { Style = (Style)FindResource("Card"), Child = panel, Margin = new Thickness(0, 0, 12, 12) });
        }
        AdminStatsContext.Text = $"更新于 {DateTime.Now:yyyy-MM-dd HH:mm:ss} · 全平台概况 · 真实成果 {data.Number("realCatalogTotal")} / 模拟成果 {data.Number("demoCatalogTotal")} · 导入 {data.Number("imports")} 批 · 版本 {data.Number("catalogRevision")}";
        DrawBars(AdminTypeChart, data["byType"]!.Items().Select(i => (Labels.Type(i.Text("type")), i.Number("count"))));
        DrawBars(AdminStateChart, data["byState"]!.Items().Select(i => (Labels.State(i.Text("state")), i.Number("count"))));
    }
}
