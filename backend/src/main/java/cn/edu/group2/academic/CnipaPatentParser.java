package cn.edu.group2.academic;

import java.awt.geom.*;
import java.io.*;
import java.util.*;
import org.apache.pdfbox.Loader;
import org.apache.pdfbox.contentstream.PDFGraphicsStreamEngine;
import org.apache.pdfbox.contentstream.operator.Operator;
import org.apache.pdfbox.cos.*;
import org.apache.pdfbox.pdmodel.*;
import org.apache.pdfbox.pdmodel.graphics.image.PDImage;
import org.apache.pdfbox.text.*;

/** Reviewed, fixed CNIPA award attachment; not a general PDF or patent search parser. */
public final class CnipaPatentParser {
    public static final String VERSION="cnipa-gold-pdf-v1";
    private static final String BATCH="cnipa-25-gold-2025",TITLE="第二十五届中国专利金奖项目名单";
    private static final String URL="https://www.cnipa.gov.cn/module/download/downfile.jsp?classid=0&showname=%E7%AC%AC%E4%BA%8C%E5%8D%81%E4%BA%94%E5%B1%8A%E4%B8%AD%E5%9B%BD%E4%B8%93%E5%88%A9%E9%87%91%E5%A5%96%E9%A1%B9%E7%9B%AE%E5%90%8D%E5%8D%95.pdf&filename=b712cad8dee344bc8322b4b45291fdf0.pdf";
    private static final List<String> HEADERS=List.of("序号","专利号","专利名称","专利权人","发明人");
    public RegisteredHtmlParser.Result parse(byte[] bytes) {
        if(bytes==null||bytes.length<5||bytes.length>8*1024*1024||bytes[0]!='%'||bytes[1]!='P'||bytes[2]!='D'||bytes[3]!='F') throw invalid("附件不是受限 PDF 文档");
        try(PDDocument document=Loader.loadPDF(bytes)) {
            if(document.isEncrypted()||document.getNumberOfPages()<1||document.getNumberOfPages()>32) throw invalid("附件加密、为空或页数超限");
            var rows=new ArrayList<RegisteredHtmlParser.Row>();var seen=new HashSet<String>();int totalCharacters=0;
            for(int p=0;p<document.getNumberOfPages();p++) {
                PDPage page=document.getPage(p);
                if(page.getRotation()!=0||Math.abs(page.getCropBox().getWidth()-841.9)>3||Math.abs(page.getCropBox().getHeight()-595.3)>3) throw invalid("专利附件页面尺寸或方向变化");
                try(InputStream stream=page.getContents()) {if(stream.readNBytes(4*1024*1024+1).length>4*1024*1024) throw invalid("附件单页解压内容超限");}
                Grid grid=new Grid(page);grid.processPage(page);
                List<Double> x=unique(grid.vertical),y=unique(grid.horizontal);
                if(x.size()!=6||y.size()<3||y.size()>102) throw invalid("附件表格线结构变化");
                var stripper=new BoundedRegions();stripper.setSortByPosition(true);
                stripper.addRegion("title",new Rectangle2D.Double(0,0,page.getCropBox().getWidth(),y.getFirst()-1));
                for(int row=0;row<y.size()-1;row++) for(int col=0;col<5;col++) {
                    stripper.addRegion(row+":"+col,new Rectangle2D.Double(x.get(col)+.4,y.get(row)+.4,x.get(col+1)-x.get(col)-.8,y.get(row+1)-y.get(row)-.8));
                }
                stripper.extractRegions(page);totalCharacters+=stripper.characters;
                if(totalCharacters>200_000) throw invalid("附件文字总量超限");
                if(p==0&&!compact(stripper.getTextForRegion("title")).contains(TITLE)) throw invalid("附件标题与登记批次不一致");
                for(int col=0;col<5;col++) if(!compact(stripper.getTextForRegion("0:"+col)).equals(HEADERS.get(col))) throw invalid("附件表头发生变化");
                for(int r=1;r<y.size()-1;r++) {
                    int index=rows.size();if(index>=500) throw invalid("附件数据行数超限");
                    var cells=new ArrayList<String>();for(int c=0;c<5;c++) cells.add(stripper.getTextForRegion(r+":"+c).strip());
                    try {
                        if(!compact(cells.getFirst()).equals(Integer.toString(index+1))) throw new IllegalArgumentException("INVALID_ROW_NUMBER");
                        String original=compact(cells.get(1)).toUpperCase(Locale.ROOT);
                        if(!original.matches("ZL[0-9]{12}\\.[0-9X]")) throw new IllegalArgumentException("INVALID_PATENT_NUMBER");
                        String identifier="CN"+original.substring(2);
                        if(!seen.add(identifier)) throw new IllegalArgumentException("DUPLICATE_SOURCE_IDENTIFIER");
                        String title=RegisteredHtmlParser.required(joinWrapped(cells.get(2)),1000,"MISSING_PATENT_TITLE");
                        String holders=RegisteredHtmlParser.required(joinWrapped(cells.get(3)),4000,"MISSING_PATENT_HOLDER");
                        var inventors=RegisteredHtmlParser.people(joinWrapped(cells.get(4)),"INVENTOR",List.of());
                        if(inventors.isEmpty()) throw new IllegalArgumentException("MISSING_INVENTOR");
                        var details=new LinkedHashMap<String,Object>();details.put("parserVersion",VERSION);details.put("batchId",BATCH);
                        details.put("patentNumberRaw",original);details.put("applicationNumberNormalization","ZL prefix replaced by CN; original retained");
                        details.put("patentHoldersRaw",Arrays.stream(holders.split("[、；;]+" )).toList());
                        details.put("grantEvidence",URL+"（中国专利金奖项目名单）");details.put("legalStatus","未核验当前法律状态");
                        details.put("applicationDate","");details.put("grantDate","");details.put("dateMissing",true);
                        details.put("sourcePublisher","国家知识产权局");details.put("recognitionName","第二十五届中国专利金奖");
                        // The award year and announcement date are not a patent application or grant date.
                        details.put("recognitionYear",2025);
                        var raw=new LinkedHashMap<String,Object>();raw.put("sourceId","cnipa-patents");raw.put("batchId",BATCH);raw.put("cells",cells);raw.put("page",p+1);
                        var work=new ImportService.WorkInput("PATENT",title,"",null,identifier,"application_number","CN","","",null,null,"UNKNOWN",false,
                            BATCH+":"+identifier,URL,inventors,List.of(),List.of(),details,raw,null);
                        rows.add(new RegisteredHtmlParser.Row(index,work,null));
                    } catch(IllegalArgumentException e) {
                        rows.add(new RegisteredHtmlParser.Row(index,null,Map.of("index",index,"reason",Objects.toString(e.getMessage(),"INVALID_ROW"),"sourceId","cnipa-patents","page",p+1,"rowChecksum",AuthService.hash(String.join("\u001f",cells)))));
                    }
                }
            }
            if(rows.size()!=30) throw invalid("登记附件预期 30 项，实际行数不符，需人工复核");
            return new RegisteredHtmlParser.Result(rows,"",TITLE,VERSION);
        } catch(IOException | IllegalArgumentException e) {throw invalid("无法解析登记 PDF 附件："+e.getClass().getSimpleName());}
    }
    private static String compact(String value) {return RegisteredHtmlParser.normalize(value).replace(" ","");}
    private static String joinWrapped(String value) {return RegisteredHtmlParser.normalize(value.replaceAll("[\\r\\n]+","")).replaceAll("(?<=[\\p{IsHan}]) +(?=[\\p{IsHan}])","");}
    private static CrawlFailure invalid(String message) {return RegisteredHtmlParser.invalid(message);}
    private static List<Double> unique(List<Double> values) {
        var result=new ArrayList<Double>();values.stream().sorted().forEach(v->{if(result.isEmpty()||v-result.getLast()>1) result.add(v);});return result;
    }
    private static final class BoundedRegions extends PDFTextStripperByArea {
        int characters,operators;
        BoundedRegions() throws IOException {super();}
        @Override protected void processTextPosition(TextPosition position) {
            characters+=position.getUnicode().length();if(characters>30_000) throw invalid("附件单页文字超限");super.processTextPosition(position);
        }
        @Override protected void processOperator(Operator operator,List<COSBase> operands) throws IOException {
            if(++operators>100_000||Thread.currentThread().isInterrupted()) throw invalid("附件解析操作超限或已取消");super.processOperator(operator,operands);
        }
    }
    /** Only stroked grid segments count; text clipping rectangles must not become data rows. */
    private static final class Grid extends PDFGraphicsStreamEngine {
        final List<Double> horizontal=new ArrayList<>(),vertical=new ArrayList<>();
        final List<Line2D> path=new ArrayList<>();Point2D current=new Point2D.Float(),start=current;int operators;
        Grid(PDPage page) {super(page);}
        @Override protected void processOperator(Operator operator,List<COSBase> operands) throws IOException {
            if(++operators>100_000||Thread.currentThread().isInterrupted()) throw invalid("附件绘图操作超限或已取消");super.processOperator(operator,operands);
        }
        @Override public void appendRectangle(Point2D a,Point2D b,Point2D c,Point2D d) {path.add(new Line2D.Double(a,b));path.add(new Line2D.Double(b,c));path.add(new Line2D.Double(c,d));path.add(new Line2D.Double(d,a));current=a;start=a;}
        @Override public void moveTo(float x,float y) {current=new Point2D.Float(x,y);start=current;}
        @Override public void lineTo(float x,float y) {Point2D end=new Point2D.Float(x,y);path.add(new Line2D.Double(current,end));current=end;}
        @Override public void curveTo(float x1,float y1,float x2,float y2,float x3,float y3) {current=new Point2D.Float(x3,y3);}
        @Override public Point2D getCurrentPoint() {return current;}
        @Override public void closePath() {path.add(new Line2D.Double(current,start));current=start;}
        @Override public void endPath() {path.clear();}
        @Override public void strokePath() {
            for(Line2D line:path) {
                if(Math.abs(line.getY1()-line.getY2())<.6&&Math.abs(line.getX1()-line.getX2())>600) horizontal.add(getPage().getCropBox().getHeight()-line.getY1());
                if(Math.abs(line.getX1()-line.getX2())<.6&&Math.abs(line.getY1()-line.getY2())>40) vertical.add(line.getX1());
            }path.clear();
        }
        @Override public void fillAndStrokePath(int windingRule) {strokePath();}
        @Override public void fillPath(int windingRule) {path.clear();}
        @Override public void drawImage(PDImage image) {}
        @Override public void clip(int windingRule) {}
        @Override public void shadingFill(COSName name) {}
    }
}
