using System.Diagnostics;
using System.IO;
using System.Text.Json.Nodes;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using Microsoft.Win32;

namespace AcademicDesktop;

public partial class MainWindow : Window
{
    private ApiClient api = new("http://127.0.0.1:8080");
    private bool ready, busy;
    private int page;
    private long total;
    private long? release;
    private string? activeQuery;
    private JsonNode? account;
    private readonly string[] titles = ["成果发现", "学者门户", "数据观察", "共著路径", "我的工作台", "管理与审核"];
    private readonly string[] subtitles = ["从一项成果出发，发现知识与人的连接。", "让每一位学者，都有准确而独立的位置。", "用清晰的口径，理解成果的分布。", "沿着论文证据，看见协作的距离。", "身份、门户与贡献，分别确认，清晰追踪。", "让每一次授权与入库，都有依据可查。"];
    public MainWindow()
    {
        InitializeComponent();
        var address = Environment.GetEnvironmentVariable("ACADEMIC_API_URL");
        if (!string.IsNullOrWhiteSpace(address)) ServerAddress.Text = address;
    }
    protected override void OnSourceInitialized(EventArgs e)
    {
        base.OnSourceInitialized(e);
        WindowPlacement.StartMaximized(this);
    }
    private string DataScope => ((ComboBoxItem)Dataset.SelectedItem).Tag.ToString()!;
    private static string SelectedTag(ComboBox box) => (box.SelectedItem as ComboBoxItem)?.Tag.ToString() ?? "";
    private static string SelectedId(ComboBox box) => box.SelectedValue?.ToString() ?? "";
    private async Task Run(Func<Task> work)
    {
        if (busy) return;
        busy = true; Pages.IsEnabled = false; Navigation.IsEnabled = false; Dataset.IsEnabled = false;
        Banner.Visibility = Visibility.Collapsed; StatusText.Text = "正在处理…";
        try { await work(); StatusText.Text = $"就绪 · 最近一次 API 请求 {api.LastMilliseconds} ms"; }
        catch (Exception ex)
        {
            if (api.Token == null && account != null) { account = null; UpdateAccount(); ClearPrivateViews(); }
            ShowMessage(ex.Message); StatusText.Text = "操作未完成 · 条件已保留";
        }
        finally { busy = false; Pages.IsEnabled = true; Navigation.IsEnabled = true; Dataset.IsEnabled = true; }
    }
    private void ShowMessage(string message) { BannerText.Text = message; Banner.Visibility = Visibility.Visible; }
    private async void WindowLoaded(object sender, RoutedEventArgs e)
    {
        ready = true;
        HighlightNavigation(0);
        await Run(async () => { await ConnectCore(); });
        if (Environment.GetCommandLineArgs().Contains("--smoke")) await RunSmoke();
    }
    private async void Connect(object sender, RoutedEventArgs e) => await Run(ConnectCore);
    private async Task ConnectCore()
    {
        var replacement = new ApiClient(ServerAddress.Text);
        api.Dispose(); api = replacement; account = null; UpdateAccount(); ClearPrivateViews();
        try
        {
            await LoadReference(); await Search(true);
            ConnectionDot.Fill = Brush("#2D9B82"); ConnectionText.Text = "服务已连接";
        }
        catch { ConnectionDot.Fill = Brush("#C98057"); ConnectionText.Text = "服务未连接"; throw; }
    }
    private async Task LoadReference()
    {
        var reference = await api.Get("api/reference");
        var institutions = new List<ReferenceItem> { new("", "全部机构") };
        institutions.AddRange(reference["institutions"]!.Items().Select(i => new ReferenceItem(i.Text("id"), i.Text("name"))));
        InstitutionFilter.ItemsSource = institutions; InstitutionFilter.SelectedIndex = 0;
        var fields = new List<ReferenceItem> { new("", "全部领域") };
        fields.AddRange(reference["fields"]!.Items().Select(f => new ReferenceItem(f.Text("name"), f.Text("name"))));
        FieldFilter.ItemsSource = fields; FieldFilter.SelectedIndex = 0;
        var scholars = (await api.Get("api/scholars?dataset=" + DataScope)).Items().Select(s => new ScholarVm(s)).ToList();
        ScholarFilter.ItemsSource = new[] { new ScholarVm(new JsonObject { ["id"] = "", ["name"] = "全部学者", ["institutionName"] = "" }) }.Concat(scholars).ToList(); ScholarFilter.SelectedIndex = 0;
        GraphStart.ItemsSource = scholars; GraphEnd.ItemsSource = scholars;
        if (scholars.Count > 0) GraphStart.SelectedIndex = 0;
        if (scholars.Count > 1) GraphEnd.SelectedIndex = 1;
        ScopeFooter.Text = DataScope == "demo" ? "课程模拟资料 · 不用于科研评价" : "真实资料 · 与模拟资料分开统计";
    }
    private async void DatasetChanged(object sender, SelectionChangedEventArgs e)
    {
        if (!ready) return;
        await Run(async () => { release = null; await LoadReference(); await Search(true); await LoadPage(); });
    }
    private async void Navigate(object sender, RoutedEventArgs e)
    {
        int index = int.Parse(((Button)sender).Tag.ToString()!);
        Pages.SelectedIndex = index; HighlightNavigation(index);
        await Run(LoadPage);
    }
    private void HighlightNavigation(int index)
    {
        PageTitle.Text = titles[index]; PageSubtitle.Text = subtitles[index];
        foreach (var button in Navigation.Children.OfType<Button>())
        {
            bool selected = button.Tag.ToString() == index.ToString();
            button.Background = Brush(selected ? "#25515C" : "Transparent");
            button.Foreground = Brush(selected ? "#FFFFFF" : "#BDD0D7");
        }
    }
    private Task LoadPage() => Pages.SelectedIndex switch { 1 => LoadScholars(), 2 => LoadStats(), 4 => LoadMine(), 5 => LoadAdmin(), _ => Task.CompletedTask };
    private string Query(bool includePage = true)
    {
        var values = new Dictionary<string, string>
        {
            ["dataset"] = DataScope, ["q"] = SearchText.Text.Trim(), ["type"] = SelectedTag(WorkType),
            ["sort"] = SelectedTag(Sort), ["institution"] = SelectedId(InstitutionFilter),
            ["scholar"] = SelectedId(ScholarFilter), ["field"] = SelectedId(FieldFilter)
        };
        foreach (var (key, box) in new[] { ("from", YearFrom), ("to", YearTo) })
            if (!string.IsNullOrWhiteSpace(box.Text))
            {
                if (!int.TryParse(box.Text, out _)) throw new InvalidOperationException("年份请输入四位数字。");
                values[key] = box.Text;
            }
        if (includePage) { values["page"] = page.ToString(); values["size"] = "20"; }
        if (release != null) values["revision"] = release.ToString()!;
        return string.Join("&", values.Select(v => Uri.EscapeDataString(v.Key) + "=" + Uri.EscapeDataString(v.Value)));
    }
    private async Task Search(bool reset)
    {
        if (reset) { page = 0; release = null; }
        var response = await api.Get("api/works?" + Query());
        total = response.Number("total"); release = response.Number("revision");
        activeQuery = Query(false);
        var works = response["items"]!.Items().Select(w => new WorkVm(w)).ToList();
        WorkList.ItemsSource = works;
        ResultSummary.Text = total == 0 ? "没有符合条件的成果 · 可调整筛选条件" : $"找到 {total:N0} 项成果";
        ReleaseText.Text = $"目录版本 {release}  ·  {(DataScope == "demo" ? "含模拟资料" : "真实资料")}";
        PageNumber.Text = $"{page + 1} / {Math.Max(1, (total + 19) / 20)}";
        PreviousPage.IsEnabled = page > 0; NextPage.IsEnabled = (page + 1) * 20 < total && (page + 1) * 20 <= 10000;
        if (works.Count > 0) { WorkList.SelectedIndex = 0; await ShowDetail(works[0].Id, release); }
        else { DetailPanel.Children.Clear(); DetailPanel.Children.Add(Text("当前筛选没有结果", 20, true)); DetailPanel.Children.Add(Text("条件已保留。清空关键词或调整类型、年份与学者后重试。", 13)); }
    }
    private async void SearchClick(object sender, RoutedEventArgs e) => await Run(() => Search(true));
    private async void SearchKey(object sender, KeyEventArgs e) { if (e.Key == Key.Enter) await Run(() => Search(true)); }
    private async void Previous(object sender, RoutedEventArgs e) => await Run(async () => { if (activeQuery != Query(false)) await Search(true); else if (page > 0) { page--; await Search(false); } });
    private async void Next(object sender, RoutedEventArgs e) => await Run(async () => { if (activeQuery != Query(false)) await Search(true); else if ((page + 1) * 20 < total) { page++; await Search(false); } });
    private async void ResetSearch(object sender, RoutedEventArgs e)
    {
        SearchText.Clear(); YearFrom.Clear(); YearTo.Clear(); WorkType.SelectedIndex = 0; Sort.SelectedIndex = 0;
        ScholarFilter.SelectedIndex = 0; InstitutionFilter.SelectedIndex = 0; FieldFilter.SelectedIndex = 0;
        await Run(() => Search(true));
    }
    private async void WorkSelected(object sender, SelectionChangedEventArgs e)
    { if (!busy && WorkList.SelectedItem is WorkVm work) await Run(() => ShowDetail(work.Id, release)); }
    private async Task ShowDetail(string id, long? version)
    {
        var work = await api.Get($"api/works/{id}" + (version == null ? "" : "?revision=" + version));
        DetailPanel.Children.Clear();
        DetailPanel.Children.Add(Text(Labels.Type(work.Text("type")) + (work.Flag("simulated") ? "  /  模拟资料" : "  /  真实资料"), 11, false, "#087F78"));
        DetailPanel.Children.Add(Text(work.Text("title"), 19, true));
        DetailPanel.Children.Add(Text("规范 ID  " + id, 10, false, "#7F929B"));
        AddDetail(Labels.DateKind(work.Text("dateKind")), work.Text("dateValue", "未知") + "  ·  " + Labels.Precision(work.Text("datePrecision")));
        AddDetail("发表 / 公告", work.Text("venue", "未知"));
        AddDetail("标识", work.Text("doi", work.Text("identifier", "无公开编号")) + "  " + Labels.Identifier(work.Text("identifierType")));
        if (work.Text("type") == "PAPER") AddDetail("引用与开放状态", (work["citationCount"] == null ? "引用未知" : $"引用 {work.Text("citationCount")} · {work.Text("citationSource")}") + "\n" + (work.Text("oaStatus") switch { "OPEN" => "发现开放版本", "NOT_FOUND" => "未发现开放版本", _ => "开放状态未知" }));
        var people = work["contributors"]!.Items().Select(p => $"{p.Text("name")} · {Labels.Role(p.Text("role"))}\n{p.Text("institutionName", "署名机构未知")}  {p.Text("scholarId")}").ToList();
        AddDetail("贡献者与署名机构", people.Count == 0 ? "未公开个人名单；不根据单位推断个人。" : string.Join("\n\n", people));
        if (work["institutions"] is JsonArray institutions) AddDetail("成果单位", string.Join("、", institutions.Items().Select(i => i.Text("name"))));
        AddDetail("领域", string.Join("、", work["fields"]!.Items().Select(f => f.Text("fieldName"))));
        AddDetail("摘要 / 说明", work.Text("abstractText", "未提供"));
        if (work["details"] is JsonObject details)
            foreach (var item in details) AddDetail(Labels.Field(item.Key), item.Value?.ToString() ?? "未知");
        DetailPanel.Children.Add(Text("来源与证据", 14, true));
        foreach (var source in work["sources"]!.Items())
        {
            DetailPanel.Children.Add(Text(source.Text("sourceName") + "\n来源键：" + source.Text("sourceKey"), 12));
            string url = source.Text("sourceUrl");
            var button = SecondaryButton("打开原始来源 ↗"); button.ToolTip = url;
            button.Click += (_, _) => OpenLink(url); DetailPanel.Children.Add(button);
            DetailPanel.Children.Add(Text("SHA-256  " + source.Text("checksum"), 10, false, "#83959C"));
        }
        var claimButton = SecondaryButton("申请确认本人贡献");
        claimButton.Click += async (_, _) => await Run(async () =>
        {
            RequireAccount("RESEARCHER");
            string? evidence = Prompt("成果认领", "请填写本人贡献及核验依据（仅本人和审核员可见）。");
            if (evidence == null) return;
            var vm = new WorkVm(work);
            await CreateAndSubmit("OUTCOME", id, evidence, vm.ContributionRole);
            ShowMessage("成果认领申请已提交，可在我的工作台追踪进度。");
        });
        DetailPanel.Children.Add(claimButton);
    }
    private void AddDetail(string label, string value) { DetailPanel.Children.Add(Text(label, 11, true, "#748A94")); DetailPanel.Children.Add(Text(value, 12)); }
    private async Task LoadScholars()
    {
        var list = await api.Get("api/scholars?dataset=" + DataScope + "&q=" + Uri.EscapeDataString(ScholarSearch.Text));
        ScholarsGrid.ItemsSource = list.Items().Select(s => new ScholarVm(s)).ToList();
        if (ScholarsGrid.Items.Count > 0) ScholarsGrid.SelectedIndex = 0;
        else { ScholarName.Text = "未找到学者"; ScholarBio.Text = "请尝试其他姓名或切换数据范围。"; }
    }
    private async void LoadScholarsClick(object sender, RoutedEventArgs e) => await Run(LoadScholars);
    private void ScholarSelected(object sender, SelectionChangedEventArgs e)
    { if (ScholarsGrid.SelectedItem is ScholarVm s) { ScholarName.Text = s.Name + " · " + s.Id; ScholarBio.Text = s.InstitutionName + "\n\n" + s.Data.Text("bio") + "\n\n" + s.ClaimLabel; } }
    private async void ScholarWorks(object sender, RoutedEventArgs e)
    {
        if (ScholarsGrid.SelectedItem is not ScholarVm s) return;
        SearchText.Clear(); WorkType.SelectedIndex = 0; InstitutionFilter.SelectedIndex = 0; FieldFilter.SelectedIndex = 0; YearFrom.Clear(); YearTo.Clear();
        ScholarFilter.SelectedValue = s.Id; Pages.SelectedIndex = 0; HighlightNavigation(0);
        await Run(() => Search(true));
    }
    private async void ClaimPortal(object sender, RoutedEventArgs e) => await Run(async () =>
    {
        RequireAccount("RESEARCHER"); if (ScholarsGrid.SelectedItem is not ScholarVm s) throw new InvalidOperationException("请先选择学者。");
        await CreateAndSubmit("PORTAL", s.Id, PortalEvidence.Text, "");
        ShowMessage("门户申请已进入人工审核；通过后仍需分别认领成果贡献。");
    });
    private async void StatsClick(object sender, RoutedEventArgs e) => await Run(LoadStats);
    private async Task LoadStats()
    {
        var data = await api.Get("api/statistics?" + Query(false)); var metrics = data["metrics"]!;
        MetricCards.Children.Clear();
        AddMetric("规范成果", metrics.Number("total").ToString("N0"), "按成果 ID 去重");
        AddMetric("论文", metrics.Number("papers").ToString("N0"), "四类成果分别统计");
        AddMetric("引用覆盖", metrics.Number("papers") == 0 ? "不适用" : $"{metrics.Number("citationKnown"):N0} / {metrics.Number("papers"):N0}", "未知引用不计为零");
        AddMetric("开放论文", metrics.Number("openPapers").ToString("N0"), $"未知开放状态 {metrics.Number("oaUnknown"):N0} 项");
        DrawBars(TypeChart, data["types"]!.Items().Select(i => (Labels.Type(i.Text("type")), i.Number("count"))));
        DrawBars(YearChart, data["years"]!.Items().Select(i => (i.Text("year", "年份未知"), i.Number("count"))));
        DrawBars(InstitutionChart, data["institutions"]!.Items().Select(i => ($"{i.Number("rank")}  {i.Text("name")}", i.Number("count"))));
        DrawBars(FieldChart, data["fields"]!.Items().Select(i => (i.Text("name"), i.Number("count"))));
        StatsContext.Text = $"版本 {data.Number("revision")} · {(DataScope == "demo" ? "模拟资料" : "真实资料")} · 沿用成果发现中的筛选条件";
        StatisticsNotes.Text = data.Text("notes") + "\n引用来源汇总：" + string.Join("；", data["citations"]!.Items().Select(c => $"{c.Text("source")}：{c.Number("count")} 次，覆盖 {c.Number("covered")} 篇"));
    }
    private void AddMetric(string label, string value, string note)
    {
        var stack = new StackPanel(); stack.Children.Add(Text(label, 12, false, "#70868F")); stack.Children.Add(Text(value, 28, true, "#087F78")); stack.Children.Add(Text(note, 10, false, "#82949C"));
        MetricCards.Children.Add(new Border { Style = (Style)FindResource("Card"), Margin = new Thickness(0, 0, 12, 0), Child = stack });
    }
    private static void DrawBars(StackPanel panel, IEnumerable<(string Label, long Value)> input)
    {
        panel.Children.Clear(); var rows = input.ToList(); long max = rows.Count == 0 ? 1 : Math.Max(1, rows.Max(x => x.Value));
        if (rows.Count == 0) panel.Children.Add(Text("当前范围暂无统计资料", 13));
        foreach (var row in rows)
        {
            var grid = new Grid { Margin = new Thickness(0, 9, 0, 2) }; grid.ColumnDefinitions.Add(new()); grid.ColumnDefinitions.Add(new() { Width = GridLength.Auto });
            grid.Children.Add(Text(row.Label, 12)); var count = Text(row.Value.ToString("N0"), 12, true); Grid.SetColumn(count, 1); grid.Children.Add(count); panel.Children.Add(grid);
            var track = new Grid { Height = 5, Background = Brush("#EDF2F4"), Margin = new Thickness(0, 0, 0, 5) };
            track.ColumnDefinitions.Add(new() { Width = new GridLength(row.Value, GridUnitType.Star) }); track.ColumnDefinitions.Add(new() { Width = new GridLength(max - row.Value, GridUnitType.Star) });
            track.Children.Add(new Border { Background = Brush("#4EA99D"), CornerRadius = new CornerRadius(3) }); panel.Children.Add(track);
        }
    }
    private async void FindPath(object sender, RoutedEventArgs e) => await Run(async () =>
    {
        string start = SelectedId(GraphStart), end = SelectedId(GraphEnd);
        if (start == "" || end == "") throw new InvalidOperationException("请选择两位学者。");
        var query = new Dictionary<string, string> { ["start"] = start, ["end"] = end, ["dataset"] = DataScope, ["field"] = SelectedId(FieldFilter), ["institution"] = SelectedId(InstitutionFilter) };
        if (release != null) query["revision"] = release.ToString()!;
        if (YearFrom.Text != "") query["from"] = YearFrom.Text; if (YearTo.Text != "") query["to"] = YearTo.Text;
        var path = await api.Get("api/graph/path?" + string.Join("&", query.Select(i => i.Key + "=" + Uri.EscapeDataString(i.Value))));
        GraphPath.Children.Clear(); GraphEvidence.Children.Clear();
        GraphMessage.Text = $"版本 {path.Number("revision")} · {path.Text("message")} · 沿用机构/领域/年份筛选";
        foreach (var node in path["nodes"]!.Items())
        {
            if (GraphPath.Children.Count > 0) GraphPath.Children.Add(Text("  →  ", 23, false, "#63A497"));
            var stack = new StackPanel(); stack.Children.Add(Text(node.Text("name"), 18, true)); stack.Children.Add(Text(node.Text("id") + " · " + node.Text("institutionName"), 11));
            GraphPath.Children.Add(new Border { Style = (Style)FindResource("Card"), Margin = new Thickness(0, 0, 0, 10), Child = stack });
        }
        foreach (var edge in path["edges"]!.Items())
        {
            var stack = new StackPanel(); stack.Children.Add(Text($"{edge.Text("source")} ↔ {edge.Text("target")}  ·  {edge.Number("weight")} 篇共同论文", 16, true));
            foreach (var paper in edge["evidence"]!.Items())
            {
                var button = SecondaryButton(paper.Text("title") + "  ↗"); button.HorizontalContentAlignment = HorizontalAlignment.Left;
                string id = paper.Text("id"); long revision = path.Number("revision");
                button.Click += async (_, _) => { Pages.SelectedIndex = 0; HighlightNavigation(0); await Run(() => ShowDetail(id, revision)); };
                stack.Children.Add(button);
            }
            if (edge.Flag("evidenceTruncated")) stack.Children.Add(Text("仅展示前 20 篇证据。", 11));
            GraphEvidence.Children.Add(new Border { Style = (Style)FindResource("Card"), Margin = new Thickness(0, 0, 0, 12), Child = stack });
        }
    });
    private void RequireAccount(string? role = null)
    {
        if (account == null || api.Token == null) throw new InvalidOperationException("请先在「我的工作台」登录。");
        if (role != null && account.Text("role") != role) throw new InvalidOperationException(role == "ADMIN" ? "此操作仅管理员可用。" : "此操作需要已审核的科研人员身份。");
    }
    private void UpdateAccount()
    {
        string text = account == null ? "访客模式" : $"{account.Text("displayName")} · {Labels.Role(account.Text("role"))}";
        SidebarUser.Text = text; AccountInfo.Text = text;
    }
    private void ClearPrivateViews()
    { MyClaims.ItemsSource = null; MyWorks.ItemsSource = null; ReviewGrid.ItemsSource = null; ImportsGrid.ItemsSource = null; ReviewEvidence.Clear(); ReviewReason.Clear(); SupplementEvidence.Clear(); PortalEvidence.Clear(); MyClaimReason.Text = "登录后查看本人申请"; }
    private async void Login(object sender, RoutedEventArgs e) => await Run(async () =>
    {
        var result = await api.Post("api/auth/login", new { username = Username.Text, password = Password.Password });
        api.Token = result.Text("token"); account = result["user"]!.DeepClone(); Password.Clear(); ClearPrivateViews(); UpdateAccount(); await LoadMine();
    });
    private async void Register(object sender, RoutedEventArgs e) => await Run(async () =>
    {
        string? name = Prompt("注册账号", "请填写显示姓名。账号和密码使用工作台输入框中的内容；密码至少 12 位。", false);
        if (name == null) return;
        await api.Post("api/auth/register", new { username = Username.Text, password = Password.Password, displayName = name });
        ShowMessage("账号已创建，请点击登录；科研身份需另行申请审核。");
    });
    private async void Logout(object sender, RoutedEventArgs e) => await Run(async () =>
    {
        try { if (api.Token != null) await api.Post("api/auth/logout", new { }); }
        finally { api.Token = null; account = null; Password.Clear(); ClearPrivateViews(); UpdateAccount(); }
    });
    private async Task LoadMine()
    {
        if (api.Token == null) { ShowMessage("登录后可查看本人申请和已确认成果。公开检索无需登录。"); return; }
        account = await api.Get("api/auth/me"); UpdateAccount();
        MyClaims.ItemsSource = (await api.Get("api/claims")).Items().Select(c => new ClaimVm(c)).ToList();
        MyWorks.ItemsSource = account.Text("role") == "RESEARCHER" ? (await api.Get("api/me/outcomes")).Items().Select(w => new WorkVm(w)).ToList() : null;
    }
    private async void RefreshMine(object sender, RoutedEventArgs e) => await Run(LoadMine);
    private async void IdentityClaim(object sender, RoutedEventArgs e) => await Run(async () =>
    {
        RequireAccount("USER"); string? evidence = Prompt("科研身份申请", "请填写身份核验依据，例如机构身份说明和可核查的公开信息。材料仅本人和审核员可见。");
        if (evidence == null) return;
        await CreateAndSubmit("IDENTITY", account!.Text("id"), evidence, ""); await LoadMine();
    });
    private async Task CreateAndSubmit(string kind, string target, string evidence, string role)
    {
        if (string.IsNullOrWhiteSpace(evidence)) throw new InvalidOperationException("请填写核验依据。");
        var claim = await api.Post("api/claims", new { kind, targetId = target, evidence, contributionRole = role });
        if (claim.Text("state") == "DRAFT") await api.Post($"api/claims/{claim.Text("id")}/actions", new { version = claim.Number("version"), action = "SUBMIT", reason = "", evidence = (string?)null });
    }
    private void MyClaimSelected(object sender, SelectionChangedEventArgs e)
    {
        if (MyClaims.SelectedItem is ClaimVm c)
        { MyClaimReason.Text = $"{c.StateLabel} · 材料版本 {c.Data.Number("materialVersion")}\n{c.Data.Text("reason")}"; SupplementEvidence.Text = c.Data.Text("evidence"); }
    }
    private async void MineAction(object sender, RoutedEventArgs e) => await Run(async () =>
    {
        RequireAccount(); if (MyClaims.SelectedItem is not ClaimVm claim) throw new InvalidOperationException("请选择一份申请。");
        await api.Post($"api/claims/{claim.Id}/actions", new { version = claim.Version, action = ((Button)sender).Tag.ToString(), reason = "", evidence = SupplementEvidence.Text }); await LoadMine();
    });
    private async void RevokeOutcome(object sender, RoutedEventArgs e) => await Run(async () =>
    {
        RequireAccount("RESEARCHER"); if (MyWorks.SelectedItem is not WorkVm work) throw new InvalidOperationException("请选择已确认成果。");
        string? evidence = Prompt("撤销本人关联", "请说明撤销原因。审核通过后只取消本人关联，公共成果和其他贡献者的关系保留。");
        if (evidence == null) return;
        await CreateAndSubmit("REVOKE", work.Id, evidence, work.ContributionRole); await LoadMine();
    });
    private async Task LoadAdmin()
    {
        RequireAccount("ADMIN");
        ReviewGrid.ItemsSource = (await api.Get("api/claims?review=true")).Items().Select(c => new ClaimVm(c)).ToList();
        ImportsGrid.ItemsSource = (await api.Get("api/admin/imports")).Items().Select(i => new ImportVm(i)).ToList();
    }
    private async void RefreshAdmin(object sender, RoutedEventArgs e) => await Run(LoadAdmin);
    private async void ReviewSelected(object sender, SelectionChangedEventArgs e)
    {
        if (busy || ReviewGrid.SelectedItem is not ClaimVm claim) return;
        await Run(async () =>
        {
            var data = await api.Get("api/claims/" + claim.Id);
            ReviewEvidence.Text = data.Text("evidence") + "\n\n处理历史：\n" + string.Join("\n", data["history"]!.Items().Select(h => $"{Labels.State(h.Text("beforeState"))} → {Labels.State(h.Text("afterState"))} · {h.Text("reason")}"));
        });
    }
    private async void ReviewAction(object sender, RoutedEventArgs e) => await Run(async () =>
    {
        RequireAccount("ADMIN"); if (ReviewGrid.SelectedItem is not ClaimVm claim) throw new InvalidOperationException("请选择审核记录。");
        var updated = await api.Post($"api/claims/{claim.Id}/actions", new { version = claim.Version, action = ((Button)sender).Tag.ToString(), reason = ReviewReason.Text, evidence = (string?)null });
        await LoadAdmin();
        ReviewGrid.SelectedItem = ReviewGrid.Items.OfType<ClaimVm>().FirstOrDefault(c => c.Id == claim.Id);
        ReviewEvidence.Text = updated.Text("evidence") + "\n\n" + Labels.State(updated.Text("state")) + " · " + updated.Text("reason");
        ShowMessage("操作完成：" + Labels.State(updated.Text("state")));
    });
    private async void ImportFile(object sender, RoutedEventArgs e) => await Run(async () =>
    {
        RequireAccount("ADMIN"); var dialog = new OpenFileDialog { Filter = "JSON 导入批次 (*.json)|*.json", Title = "选择受控导入批次" };
        if (dialog.ShowDialog(this) != true) return;
        if (new FileInfo(dialog.FileName).Length > 2 * 1024 * 1024) throw new InvalidOperationException("文件超过 2 MiB，请拆分批次。");
        string content = await File.ReadAllTextAsync(dialog.FileName);
        _ = JsonNode.Parse(content) ?? throw new InvalidOperationException("JSON 内容为空。");
        var result = await api.PostJson("api/admin/imports", content);
        await LoadAdmin(); ShowMessage($"导入完成：新增 {result.Number("inserted")}，重复 {result.Number("duplicates")}，版本 {result.Number("revision")}。重新检索可看到新版本。");
    });
    private string? Prompt(string title, string explanation, bool multiline = true)
    {
        var dialog = new Window { Title = title, Icon = Icon, Width = 520, Height = multiline ? 340 : 240, ResizeMode = ResizeMode.NoResize, Owner = this, WindowStartupLocation = WindowStartupLocation.CenterOwner };
        var panel = new StackPanel { Margin = new Thickness(24) }; panel.Children.Add(Text(explanation, 13));
        var input = new TextBox { Height = multiline ? 140 : 40, TextWrapping = TextWrapping.Wrap, AcceptsReturn = multiline, Margin = new Thickness(0, 14, 0, 16), VerticalScrollBarVisibility = ScrollBarVisibility.Auto };
        panel.Children.Add(input); var submit = new Button { Content = "确认提交", HorizontalAlignment = HorizontalAlignment.Right, IsDefault = !multiline };
        submit.Click += (_, _) => { if (!string.IsNullOrWhiteSpace(input.Text)) dialog.DialogResult = true; };
        panel.Children.Add(submit); dialog.Content = panel; dialog.Loaded += (_, _) => input.Focus();
        return dialog.ShowDialog() == true ? input.Text.Trim() : null;
    }
    private void OpenLink(string url)
    {
        if (!Uri.TryCreate(url, UriKind.Absolute, out var uri) || !(uri.Scheme == "https" || uri.Scheme == "http")) { ShowMessage("来源链接格式不合法。"); return; }
        try { Process.Start(new ProcessStartInfo(uri.AbsoluteUri) { UseShellExecute = true }); }
        catch { ShowMessage("无法启动默认浏览器。"); }
    }
    private Button SecondaryButton(string label) => new() { Content = label, Style = (Style)FindResource("Secondary"), Margin = new Thickness(0, 8, 0, 8) };
    private static SolidColorBrush Brush(string color) => (SolidColorBrush)new BrushConverter().ConvertFromString(color)!;
    private static TextBlock Text(string value, double size, bool bold = false, string color = "#294652") => new()
    { Text = value, FontSize = size, FontWeight = bold ? FontWeights.SemiBold : FontWeights.Normal, Foreground = Brush(color), TextWrapping = TextWrapping.Wrap, Margin = new Thickness(0, 3, 0, 6) };
    protected override void OnClosed(EventArgs e) { api.Dispose(); base.OnClosed(e); }
    // Runs against a real API and WPF visual tree; no mock responses. Explicit --smoke only.
    private async Task RunSmoke()
    {
        string output = Environment.GetEnvironmentVariable("ACADEMIC_SMOKE_OUTPUT") ?? Path.Combine(AppContext.BaseDirectory, "desktop-smoke.json");
        try
        {
            if (Pages.SelectedIndex != 0 || !WorkList.IsVisible) throw new InvalidOperationException("启动后成果发现页面不可见");
            if (WorkList.Items.Count == 0) throw new InvalidOperationException("目录未加载");
            await LoadScholars(); await LoadStats();
            var path = await api.Get("api/graph/path?start=S1&end=S2&dataset=demo");
            if (!path.Flag("found")) throw new InvalidOperationException("共著路径未加载");
            Pages.SelectedIndex = 0; HighlightNavigation(0); UpdateLayout();
            var visual = (FrameworkElement)Content;
            var bitmap = new System.Windows.Media.Imaging.RenderTargetBitmap((int)visual.ActualWidth, (int)visual.ActualHeight, 96, 96, PixelFormats.Pbgra32); bitmap.Render(visual);
            var encoder = new System.Windows.Media.Imaging.PngBitmapEncoder(); encoder.Frames.Add(System.Windows.Media.Imaging.BitmapFrame.Create(bitmap));
            using (var stream = File.Create(Path.ChangeExtension(output, ".png"))) encoder.Save(stream);
            await File.WriteAllTextAsync(output, new JsonObject { ["ok"] = true, ["workCards"] = WorkList.Items.Count, ["scholars"] = ScholarsGrid.Items.Count, ["metricCards"] = MetricCards.Children.Count, ["pathFound"] = true, ["framework"] = ".NET 9 WPF", ["api"] = ServerAddress.Text }.ToJsonString());
        }
        catch (Exception ex) { await File.WriteAllTextAsync(output, new JsonObject { ["ok"] = false, ["error"] = ex.ToString() }.ToJsonString()); }
        finally { Close(); }
    }
}
