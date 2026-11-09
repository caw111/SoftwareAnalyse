using System.Collections.Concurrent;
using System.Globalization;
using System.IO;
using System.Windows;
using System.Windows.Documents;
using System.Windows.Media;
using System.Xml;
using System.Xml.Linq;

namespace AcademicDesktop;

/// <summary>
/// Renders the application's small, embedded SVG drawings without a browser or native dependency.
/// This deliberately accepts a limited SVG subset, never external images, scripts or fonts.
/// </summary>
public sealed class SvgIcon : FrameworkElement
{
    private static readonly ConcurrentDictionary<string, SvgDrawing> Cache = new(StringComparer.Ordinal);
    private static readonly char[] NumberSeparators = [' ', ',', '\t', '\r', '\n'];
    private static readonly XNamespace SvgNamespace = "http://www.w3.org/2000/svg";

    public static readonly DependencyProperty SourceProperty = DependencyProperty.Register(
        nameof(Source), typeof(string), typeof(SvgIcon),
        new FrameworkPropertyMetadata(null, FrameworkPropertyMetadataOptions.AffectsRender));

    public static readonly DependencyProperty ForegroundProperty = TextElement.ForegroundProperty.AddOwner(
        typeof(SvgIcon), new FrameworkPropertyMetadata(Brushes.Black,
            FrameworkPropertyMetadataOptions.Inherits | FrameworkPropertyMetadataOptions.AffectsRender));

    static SvgIcon()
    {
        WidthProperty.OverrideMetadata(typeof(SvgIcon), new FrameworkPropertyMetadata(20d));
        HeightProperty.OverrideMetadata(typeof(SvgIcon), new FrameworkPropertyMetadata(20d));
        IsHitTestVisibleProperty.OverrideMetadata(typeof(SvgIcon), new UIPropertyMetadata(false));
    }

    public string? Source
    {
        get => (string?)GetValue(SourceProperty);
        set => SetValue(SourceProperty, value);
    }

    public Brush Foreground
    {
        get => (Brush)GetValue(ForegroundProperty);
        set => SetValue(ForegroundProperty, value);
    }

    protected override void OnRender(DrawingContext context)
    {
        base.OnRender(context);
        if (string.IsNullOrWhiteSpace(Source) || ActualWidth <= 0 || ActualHeight <= 0) return;
        var drawing = Cache.GetOrAdd(Source, Load);
        var scale = Math.Min(ActualWidth / drawing.ViewBox.Width, ActualHeight / drawing.ViewBox.Height);
        var offsetX = (ActualWidth - drawing.ViewBox.Width * scale) / 2 - drawing.ViewBox.X * scale;
        var offsetY = (ActualHeight - drawing.ViewBox.Height * scale) / 2 - drawing.ViewBox.Y * scale;
        context.PushTransform(new MatrixTransform(scale, 0, 0, scale, offsetX, offsetY));
        foreach (var shape in drawing.Shapes)
        {
            var stroke = ResolveBrush(shape.Stroke);
            Pen? pen = stroke is null || shape.StrokeWidth <= 0 ? null : new Pen(stroke, shape.StrokeWidth)
            {
                StartLineCap = shape.LineCap,
                EndLineCap = shape.LineCap,
                LineJoin = shape.LineJoin
            };
            context.DrawGeometry(ResolveBrush(shape.Fill), pen, shape.Geometry);
        }
        context.Pop();
    }

    private Brush? ResolveBrush(string value) => value switch
    {
        "none" => null,
        "currentColor" => Foreground,
        _ => BrushCache.GetOrAdd(value, color =>
        {
            var brush = (Brush)new BrushConverter().ConvertFromInvariantString(color)!;
            brush.Freeze();
            return brush;
        })
    };

    private static readonly ConcurrentDictionary<string, Brush> BrushCache = new(StringComparer.Ordinal);

    private static SvgDrawing Load(string source)
    {
        // Embedded assets only. No absolute, file, network, parent traversal or markup URI.
        if (!source.StartsWith("Assets/", StringComparison.Ordinal) ||
            !source.EndsWith(".svg", StringComparison.Ordinal) ||
            source.Split('/').Any(segment => segment.Length == 0 || segment == "." || segment == ".." ||
                segment.Any(c => !(char.IsAsciiLetterOrDigit(c) || c is '-' or '_' or '.'))))
            throw new ArgumentException("SVG Source must reference an embedded Assets/*.svg resource.", nameof(source));

        var uri = new Uri("/AcademicDesktop;component/" + source, UriKind.Relative);
        var resource = Application.GetResourceStream(uri)
            ?? throw new FileNotFoundException("Embedded SVG resource was not found.", source);
        using var stream = resource.Stream;
        using var reader = XmlReader.Create(stream, new XmlReaderSettings
        {
            DtdProcessing = DtdProcessing.Prohibit,
            XmlResolver = null,
            MaxCharactersInDocument = 65_536
        });
        var root = XElement.Load(reader);
        if (root.Name != SvgNamespace + "svg")
            throw new FormatException("SVG root and namespace are required.");
        var values = ParseNumbers(root.Attribute("viewBox")?.Value ?? "");
        if (values.Length != 4 || values[2] <= 0 || values[3] <= 0)
            throw new FormatException("SVG must define a positive viewBox.");
        var shapes = new List<SvgShape>();
        var defaults = new SvgStyle("black", "none", 1, PenLineCap.Flat, PenLineJoin.Miter);
        ReadShapes(root, InheritStyle(root, defaults), shapes);
        return new SvgDrawing(new Rect(values[0], values[1], values[2], values[3]), shapes);
    }

    private static void ReadShapes(XElement parent, SvgStyle inherited, List<SvgShape> shapes)
    {
        foreach (var element in parent.Elements())
        {
            if (element.Name.Namespace != SvgNamespace)
                throw new FormatException("Unsupported SVG namespace.");
            var style = InheritStyle(element, inherited);
            if (element.Name.LocalName is "title" or "desc") continue;
            if (element.Name.LocalName == "g")
            {
                ReadShapes(element, style, shapes);
                continue;
            }
            // SVG transforms and paint servers are unnecessary for our icon set.
            // Reject them rather than silently drawing a misleading icon.
            if (element.Attribute("transform") is not null || element.Attribute("style") is not null)
                throw new FormatException("Use explicit geometry and paint attributes for embedded SVG icons.");
            Geometry geometry = element.Name.LocalName switch
            {
                "path" => Geometry.Parse(element.Attribute("d")?.Value ?? ""),
                "circle" => new EllipseGeometry(new Point(Number(element, "cx"), Number(element, "cy")),
                    Number(element, "r"), Number(element, "r")),
                "rect" => new RectangleGeometry(
                    new Rect(Number(element, "x"), Number(element, "y"),
                        Number(element, "width"), Number(element, "height")),
                    Number(element, "rx"), Number(element, "ry", Number(element, "rx"))),
                "line" => new LineGeometry(
                    new Point(Number(element, "x1"), Number(element, "y1")),
                    new Point(Number(element, "x2"), Number(element, "y2"))),
                "polyline" => Polyline(element),
                _ => throw new FormatException("Unsupported embedded SVG element: " + element.Name.LocalName)
            };
            geometry.Freeze();
            shapes.Add(new SvgShape(geometry, style.Fill, style.Stroke, style.StrokeWidth, style.LineCap, style.LineJoin));
        }
    }

    private static Geometry Polyline(XElement element)
    {
        var points = ParseNumbers(element.Attribute("points")?.Value ?? "");
        if (points.Length < 4 || points.Length % 2 != 0)
            throw new FormatException("SVG polyline must contain point pairs.");
        var path = new StreamGeometry();
        using (var context = path.Open())
        {
            context.BeginFigure(new Point(points[0], points[1]), false, false);
            for (var i = 2; i < points.Length; i += 2)
                context.LineTo(new Point(points[i], points[i + 1]), true, false);
        }
        return path;
    }

    private static SvgStyle InheritStyle(XElement element, SvgStyle parent) => new(
        element.Attribute("fill")?.Value ?? parent.Fill,
        element.Attribute("stroke")?.Value ?? parent.Stroke,
        Number(element, "stroke-width", parent.StrokeWidth),
        element.Attribute("stroke-linecap")?.Value switch
        {
            "round" => PenLineCap.Round, "square" => PenLineCap.Square, "butt" => PenLineCap.Flat, _ => parent.LineCap
        },
        element.Attribute("stroke-linejoin")?.Value switch
        {
            "round" => PenLineJoin.Round, "bevel" => PenLineJoin.Bevel, "miter" => PenLineJoin.Miter, _ => parent.LineJoin
        });

    private static double Number(XElement element, string name, double fallback = 0) =>
        element.Attribute(name) is { } attribute ? ParseNumber(attribute.Value) : fallback;

    private static double[] ParseNumbers(string text) =>
        text.Split(NumberSeparators, StringSplitOptions.RemoveEmptyEntries).Select(ParseNumber).ToArray();

    private static double ParseNumber(string text)
    {
        var value = double.Parse(text, NumberStyles.Float, CultureInfo.InvariantCulture);
        if (!double.IsFinite(value)) throw new FormatException("SVG numbers must be finite.");
        return value;
    }

    private sealed record SvgDrawing(Rect ViewBox, List<SvgShape> Shapes);
    private sealed record SvgShape(Geometry Geometry, string Fill, string Stroke, double StrokeWidth, PenLineCap LineCap, PenLineJoin LineJoin);
    private sealed record SvgStyle(string Fill, string Stroke, double StrokeWidth, PenLineCap LineCap, PenLineJoin LineJoin);
}
