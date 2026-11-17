using System.Diagnostics;
using System.Globalization;
using System.Text;
using System.Text.Json;
using Spectre.Console;
using Spectre.Console.Rendering;

return await new Installer().Run(args);

sealed class Installer
{
    const int ContentMargin = 2;
    static readonly Spinner WorkingSpinner = new IndentedSpinner(Spinner.Known.Dots);
    readonly string sources = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, ".."));
    JsonDocument? catalog;
    string language = "en";
    string? directory;
    bool rich;
    bool runningOperation;
    bool themeApplied;
    Color previousForeground;
    Color previousBackground;
    static readonly Color BackgroundColor = new(38, 38, 38);
    static readonly Color TextColor = new(238, 238, 238);
    static readonly Color AccentColor = new(0, 200, 255);
    static readonly Style Accent = new(AccentColor);
    static readonly Style Muted = new(new Color(160, 160, 160));
    static readonly Style Border = new(new Color(105, 105, 105));
    static readonly Style ErrorStyle = new(new Color(255, 107, 107));
    static readonly Style SuccessStyle = new(new Color(106, 216, 142));

    string T(string key, params object[] values) => string.Format(CultureInfo.InvariantCulture,
        catalog!.RootElement.GetProperty(language).GetProperty(key).GetString()!, values);

    void Write(string text, Style? style = null)
    {
        if (rich) AnsiConsole.Write(Inset(new Text(text, style ?? Style.Plain)));
        else Console.WriteLine(text);
    }

    void WriteParagraph(string text, Style? style = null)
    {
        Write(text, style);
        Console.WriteLine();
    }

    bool MatchesMessage(string line, string key)
    {
        // These messages have either no argument or a single path argument.
        // Compare both fixed ends of the localized template; never inspect path contents.
        var parts = T(key, "\0").Split('\0');
        return parts.Length == 1 ? line == parts[0]
            : line.StartsWith(parts[0], StringComparison.Ordinal)
                && line.EndsWith(parts[1], StringComparison.Ordinal);
    }

    void WriteOperationOutput(string output, bool succeeded, string action)
    {
        Style? style = null;
        foreach (var line in output.TrimEnd().Split('\n'))
        {
            var text = line.TrimEnd('\r');
            // These result views already include a separate destination block.
            if (succeeded && action is "Install" or "Status" && MatchesMessage(text, "detectedDirectory")) continue;
            if (text.StartsWith(T("errorPrefix", ""), StringComparison.Ordinal)) style = ErrorStyle;
            else if (MatchesMessage(text, "diagnosticSaved") || MatchesMessage(text, "diagnosticUnavailable")) style = null;
            else if (succeeded && SuccessKeys.Any(key => MatchesMessage(text, key))) style = SuccessStyle;
            else if (style == SuccessStyle) style = null;
            Write(text, text == T("installDirectoryLabel") ? Muted : style);
        }
    }

    static readonly string[] SuccessKeys = ["checkOk", "installOk", "disableOk", "enableOk", "uninstallOk", "loaderRemoved"];

    string? ReadInput()
    {
        if (rich) Console.Write(new string(' ', ContentMargin));
        return Console.ReadLine();
    }

    public async Task<int> Run(string[] args)
    {
        Console.InputEncoding = new UTF8Encoding(false);
        Console.OutputEncoding = new UTF8Encoding(false);
        try { Console.Title = "SnowRunner FFB Fix"; } catch (IOException) { }
        bool selectedLanguage = false, plain = false, preview = false;
        for (int i = 0; i < args.Length; i++)
        {
            switch (args[i].ToLowerInvariant())
            {
                case "-language" when i + 1 < args.Length && args[i + 1] is "fr" or "en":
                    language = args[++i]; selectedLanguage = true; break;
                case "-gamedirectory" when i + 1 < args.Length: directory = args[++i]; break;
                case "--plain": plain = true; break;
                case "--preview": preview = true; break;
                default:
                    Console.WriteLine("Arguments invalides / Invalid arguments. -Language fr|en -GameDirectory <path> [--plain] [--preview]");
                    return 2;
            }
        }
        rich = !plain && !Console.IsInputRedirected && !Console.IsOutputRedirected
            && AnsiConsole.Profile.Capabilities.Interactive && AnsiConsole.Profile.Capabilities.Ansi;
        Console.CancelKeyPress += (_, e) => { if (runningOperation) e.Cancel = true; else RestoreTheme(); };
        try
        {
            ApplyTheme();
            if (!selectedLanguage && !SelectLanguage()) return 0;
            catalog = JsonDocument.Parse(File.ReadAllText(Path.Combine(sources, "Locales", "messages.json")));
            // Validate both translations before allowing any operation.
            foreach (var lang in new[] { "fr", "en" })
                foreach (var key in RequiredKeys)
                    if (catalog.RootElement.GetProperty(lang).GetProperty(key).ValueKind != JsonValueKind.String)
                        throw new InvalidDataException();
            bool options = false;
            while (true)
            {
                Header(options);
                var keys = options ? new[] { "check", "disable", "enable", "chooseDirectory" }
                    : new[] { "install", "status", "uninstall", "options", "help", "language" };
                var labels = keys.Select(k => T(k)).Append(T(options ? "back" : "quit")).ToArray();
                if (preview)
                {
                    if (rich) AnsiConsole.Write(MenuView(null, labels, 0));
                    else for (int i = 0; i < labels.Length; i++) Write(labels[i]);
                    return 0;
                }
                int choice = Choose(T("choice"), labels, mainMenu: true);
                if (choice == -1) return 0;
                if (choice == keys.Length) { if (options) { options = false; continue; } return 0; }
                switch (keys[choice])
                {
                    case "options": options = true; break;
                    case "language": if (!SelectLanguage()) return 0; break;
                    case "help": Write(T("helpText")); Pause(); break;
                    case "chooseDirectory":
                        WriteParagraph(T("directoryPrompt")); WriteParagraph(T("directoryReset"));
                        var path = ReadInput();
                        if (path is null) return 0;
                        directory = path.Trim().Trim('"'); break;
                    default:
                        var action = keys[choice] switch
                        {
                            "install" => "Install", "status" => "Status", "uninstall" => "Uninstall",
                            "check" => "Check", "disable" => "Disable", "enable" => "Enable",
                            _ => throw new InvalidOperationException()
                        };
                        await Operate(action); break;
                }
            }
        }
        catch (Exception ex) when (ex is IOException or JsonException or KeyNotFoundException or InvalidOperationException)
        {
            WriteParagraph(language == "fr" ? "Le paquet est incomplet ou illisible. Extrayez à nouveau le ZIP complet."
                : "The package is incomplete or unreadable. Extract the complete ZIP again.", ErrorStyle);
            Write(language == "fr" ? "Appuyez sur Entrée pour fermer." : "Press Enter to close.");
            ReadInput(); return 1;
        }
        finally { RestoreTheme(); catalog?.Dispose(); }
    }

    void ApplyTheme()
    {
        if (!rich || AnsiConsole.Profile.Capabilities.ColorSystem == ColorSystem.NoColors) return;
        previousForeground = AnsiConsole.Foreground;
        previousBackground = AnsiConsole.Background;
        themeApplied = true;
        // Session-only terminal background: also colors the unused cells and erased lines.
        // Unsupported OSC sequences are ignored; Spectre still colors rendered content.
        Console.Write("\u001b]10;rgb:ee/ee/ee\u001b\\\u001b]11;rgb:26/26/26\u001b\\");
        AnsiConsole.Foreground = TextColor;
        AnsiConsole.Background = BackgroundColor;
    }

    void RestoreTheme()
    {
        if (!themeApplied) return;
        themeApplied = false;
        AnsiConsole.Foreground = previousForeground;
        AnsiConsole.Background = previousBackground;
        Console.Write("\u001b[0m\u001b]110\u001b\\\u001b]111\u001b\\");
    }

    bool SelectLanguage()
    {
        var labels = new[] { "Français", "English", "Quitter / Exit" };
        const string title = "Choisissez votre langue / Choose your language";
        if (!rich) WriteParagraph("\n" + title);
        else
        {
            AnsiConsole.Clear();
            Brand("SnowRunner FFB Fix");
            AnsiConsole.WriteLine();
        }
        int choice = Choose(title, labels, languageMenu: true);
        if (choice < 0 || choice == 2) return false;
        language = choice == 0 ? "fr" : "en";
        return true;
    }

    int ContentWidth => Math.Max(16, Math.Min(64, AnsiConsole.Profile.Width - 4));
    bool Spacious => AnsiConsole.Profile.Height >= 32;
    IRenderable Inset(IRenderable content) => new Padder(content, new Padding(ContentMargin, 0, ContentMargin, 0));

    sealed class IndentedSpinner(Spinner spinner) : Spinner
    {
        public override TimeSpan Interval => spinner.Interval;
        public override bool IsUnicode => spinner.IsUnicode;
        public override IReadOnlyList<string> Frames { get; } =
            spinner.Frames.Select(frame => new string(' ', ContentMargin) + frame).ToArray();
    }

    void Brand(string subtitle)
    {
        if (Spacious) AnsiConsole.WriteLine();
        var panel = new Panel(new Rows(new Text("S N O W R U N N E R", Accent), new Text(subtitle, Muted)))
            .Border(BoxBorder.Rounded).BorderStyle(Border)
            .Padding(2, Spacious ? 1 : 0);
        panel.Width = ContentWidth;
        AnsiConsole.Write(Inset(panel));
    }

    void Header(bool options)
    {
        if (rich)
        {
            AnsiConsole.Clear();
            Brand(T("subtitle"));
            AnsiConsole.WriteLine();
            var info = new Grid().AddColumn().AddColumn();
            info.Width = ContentWidth;
            info.AddRow(new Text(T("versionLabel"), Muted), new Text("0.2.0"));
            info.AddRow(new Text(T("gameFolderLabel"), Muted), new Text(string.IsNullOrEmpty(directory)
                ? T("automaticSteam") : directory, string.IsNullOrEmpty(directory) ? Muted : Style.Plain));
            AnsiConsole.Write(Inset(info));
            AnsiConsole.WriteLine();
            AnsiConsole.Write(Inset(new Text(T("closeGameHint"))));
            AnsiConsole.WriteLine();
            if (Spacious) AnsiConsole.WriteLine();
            AnsiConsole.Write(Inset(new Rows(new Text(T(options ? "optionsHeading" : "mainHeading"), Accent),
                new Text(new string('─', ContentWidth), Border))));
            AnsiConsole.WriteLine();
            return;
        }
        Write("\n==================================================\n" + T("title") + "\n==================================================");
        Write(string.IsNullOrEmpty(directory) ? T("autoDirectory") : T("selectedDirectory", directory));
        Write(T("closeGameHint") + "\n");
    }

    IRenderable MenuView(string? title, string[] labels, int selected, bool languageMenu = false)
    {
        var rows = new List<IRenderable>();
        if (title is not null) { rows.Add(new Text(title.Trim(), Accent)); rows.Add(new Text("")); }
        for (int i = 0; i < labels.Length; i++)
            rows.Add(new Text((i == selected ? "› " : "  ") + labels[i],
                i == selected ? new Style(AccentColor, decoration: Decoration.Bold) : Style.Plain));
        rows.Add(new Text(""));
        if (Spacious) rows.Add(new Text(""));
        rows.Add(new Text(languageMenu ? "↑ ↓  Naviguer / Navigate    Entrée / Enter"
            : T("navigationHint"), Muted));
        return Inset(new Rows(rows));
    }

    // The final entry is always 0 in the line-oriented fallback. EOF never confirms an action.
    int Choose(string title, string[] labels, bool languageMenu = false, bool defaultFirst = false, bool mainMenu = false)
    {
        if (rich)
        {
            int selected = 0;
            string? heading = mainMenu ? null : title;
            // Render the choices and their footer together; input never executes a command.
            return AnsiConsole.Live(MenuView(heading, labels, selected, languageMenu)).AutoClear(true).Start(ctx =>
            {
                ctx.Refresh();
                while (true)
                {
                    var key = Console.ReadKey(intercept: true).Key;
                    switch (key)
                    {
                        case ConsoleKey.UpArrow: selected = (selected + labels.Length - 1) % labels.Length; break;
                        case ConsoleKey.DownArrow: selected = (selected + 1) % labels.Length; break;
                        case ConsoleKey.Home: selected = 0; break;
                        case ConsoleKey.End: selected = labels.Length - 1; break;
                        case ConsoleKey.Enter: return selected;
                        case ConsoleKey.Escape: return labels.Length - 1;
                    }
                    ctx.UpdateTarget(MenuView(heading, labels, selected, languageMenu));
                }
            });
        }
        for (int i = 0; i < labels.Length; i++) Write($"  {(i == labels.Length - 1 ? 0 : i + 1)}  {labels[i]}");
        while (true)
        {
            Console.Write(languageMenu ? "> " : title);
            var line = Console.ReadLine();
            if (line is null) return -1;
            line = line.Trim();
            if (defaultFirst && line.Length == 0) return 0;
            if (int.TryParse(line, out int n) && n >= 0 && n < labels.Length)
                return n == 0 ? labels.Length - 1 : n - 1;
            Write(languageMenu ? "Choisissez 1 ou 2 / Choose 1 or 2." : T("invalidChoice"), ErrorStyle);
        }
    }

    void Pause() { Write("\n" + T("returnPrompt")); ReadInput(); }

    async Task Operate(string action)
    {
        bool removeLoader = false;
        if (action == "Uninstall")
        {
            WriteParagraph(T("keepLoaderQuestion")); WriteParagraph(T("keepLoaderExplanation"));
            int choice = Choose(T("keepLoaderPrompt"),
                new[] { T("keepLoaderYes"), T("keepLoaderNo"), T("cancelUninstall") }, defaultFirst: true);
            if (choice < 0 || choice == 2) return;
            removeLoader = choice == 1;
        }
        try
        {
            foreach (var file in new[] { "Scripts/manage.ps1", "package.json", "Scripts/steam-paths.ps1", "Locales/messages.json", "Scripts/i18n.ps1" })
                if (!File.Exists(Path.Combine(sources, file))) { Write(T("missingPackage"), ErrorStyle); Pause(); return; }
            var start = new ProcessStartInfo(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System),
                "WindowsPowerShell", "v1.0", "powershell.exe"))
            {
                UseShellExecute = false, CreateNoWindow = true, WorkingDirectory = sources,
                RedirectStandardOutput = true, RedirectStandardError = true, RedirectStandardInput = true,
                StandardOutputEncoding = Encoding.UTF8, StandardErrorEncoding = Encoding.UTF8
            };
            foreach (var arg in new[] { "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File",
                Path.Combine(sources, "Scripts", "manage.ps1"), "-Action", action, "-Language", language }) start.ArgumentList.Add(arg);
            if (!string.IsNullOrEmpty(directory)) { start.ArgumentList.Add("-GameDirectory"); start.ArgumentList.Add(directory); }
            if (removeLoader) start.ArgumentList.Add("-RemoveLoader");

            async Task<(int Code, string Output, string Error)> Execute()
            {
                using var process = Process.Start(start) ?? throw new IOException();
                process.StandardInput.Close();
                var output = process.StandardOutput.ReadToEndAsync();
                var error = process.StandardError.ReadToEndAsync();
                await process.WaitForExitAsync();
                return (process.ExitCode, await output, await error);
            }
            runningOperation = true;
            var result = rich ? await AnsiConsole.Status().Spinner(WorkingSpinner)
                .StartAsync(Markup.Escape(T("working")), _ => Execute()) : await Execute();
            // Text, never markup: paths and backend messages may contain brackets.
            WriteOperationOutput(result.Output, result.Code == 0, action);
            if (!string.IsNullOrWhiteSpace(result.Error)) Write(result.Error.TrimEnd(), ErrorStyle);
            if (result.Code != 0) Write(T("operationFailed"), ErrorStyle);
        }
        catch (Exception ex) when (ex is IOException or System.ComponentModel.Win32Exception or UnauthorizedAccessException)
        {
            Write(T("backendUnavailable"), ErrorStyle);
        }
        finally { runningOperation = false; }
        Pause();
    }

    static readonly string[] RequiredKeys = ["title", "autoDirectory", "selectedDirectory", "closeGameHint", "choice",
        "install", "status", "uninstall", "options", "help", "language", "quit", "back", "check", "disable", "enable",
        "chooseDirectory", "helpText", "directoryPrompt", "directoryReset", "invalidChoice", "returnPrompt", "working",
        "keepLoaderQuestion", "keepLoaderExplanation", "keepLoaderPrompt", "keepLoaderYes", "keepLoaderNo", "cancelUninstall",
        "missingPackage", "operationFailed", "backendUnavailable", "subtitle", "versionLabel", "gameFolderLabel",
        "automaticSteam", "mainHeading", "optionsHeading", "navigationHint", "errorPrefix", "diagnosticSaved",
        "diagnosticUnavailable", "checkOk", "installOk", "disableOk", "enableOk", "uninstallOk", "loaderRemoved",
        "installDirectoryLabel", "installNextStep", "detectedDirectory"];
}
