package cn.edu.group2.academic;

import java.util.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.*;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
public class Bootstrap implements ApplicationRunner {
    final Db db;final AuthService auth;final ImportService imports;
    @Value("${app.demo}") boolean demo;
    @Value("${app.admin-password}") String adminPassword;
    @Value("${app.demo-count}") int demoCount;
    Bootstrap(Db db,AuthService auth,ImportService imports) {this.db=db;this.auth=auth;this.imports=imports;}
    @Override @Transactional
    public void run(ApplicationArguments args) {
        db.one("SELECT revision FROM catalog_release WHERE id=1 FOR UPDATE");
        if(db.count("SELECT COUNT(*) FROM app_user")>0) return;
        if(!demo&&adminPassword.length()<16) throw new IllegalStateException("Production first start requires ADMIN_PASSWORD with at least 16 characters");
        String admin=auth.createUser("admin",demo?"DemoPass2026!":adminPassword,"平台管理员","ADMIN");
        if(!demo) return;
        auth.createUser("researcher","DemoPass2026!","林知远 · 演示科研人员","RESEARCHER");
        auth.createUser("reader","DemoPass2026!","访客研究员 · 演示普通用户","USER");
        String[] institutions={"示例大学 · 计算机学院","示例科技大学","示例研究院","示例大学 · 信息学院"};
        for(int i=0;i<institutions.length;i++) db.update("INSERT INTO institution VALUES(?,?)","I"+(i+1),institutions[i]);
        String[] names={"林知远","林知远","陈思宁","周予安","李文澜","王清和","赵亦舟","刘星遥","孙嘉禾","吴明川","郑时雨","许予墨"};
        for(int i=0;i<names.length;i++) db.update("INSERT INTO scholar VALUES(?,?,?,?,TRUE)","S"+(i+1),names[i],"I"+(i%4+1),"课程演示人物，独立标识 S"+(i+1)+"；同名不代表同一人。姓名、机构与成果均为模拟资料。");
        var actor=new AuthService.Actor(admin,"admin","平台管理员","ADMIN");
        int count=Math.max(0,Math.min(demoCount,100000));
        for(int offset=0;offset<count;offset+=200) {
            List<ImportService.WorkInput> works=new ArrayList<>();
            for(int i=offset;i<Math.min(offset+200,count);i++) works.add(sample(i,names));
            imports.ingest(new ImportService.Batch("bootstrap-"+offset,"课程模拟数据 v1",works),actor);
        }
    }
    static ImportService.WorkInput sample(int i,String[] names) {
        String type=switch(i%8) {case 5->"PATENT";case 6->"PROJECT";case 7->"AWARD";default->"PAPER";};
        String role=switch(type) {case "PAPER"->"AUTHOR";case "PATENT"->"INVENTOR";case "PROJECT"->"PI";default->"AWARDEE";};
        String[] themes={"知识图谱","分布式系统","机器学习","数据治理","软件工程","并发控制","可信计算","学术网络"};
        String[] titles={"面向学术发现的知识表示与推理","低延迟服务中的一致性与并发优化","多模态学习的可解释性研究","科研数据的溯源与质量评估","软件架构演化及质量度量","高并发事务的冲突检测方法","隐私保护下的可信数据协同","跨机构协作网络分析"};
        List<ImportService.Contributor> people=new ArrayList<>();
        if(!type.equals("AWARD")||i%16!=7) {
            for(int s:new int[]{i%names.length,(i+1)%names.length}) people.add(new ImportService.Contributor("S"+(s+1),names[s],role,"I"+(s%4+1)));
        }
        String identifierType=switch(type) {case "PATENT"->"application_number";case "PROJECT"->"approval_number";case "AWARD"->"award_project_number";default->null;};
        Map<String,Object> details=type.equals("PATENT")?Map.of("grantEvidence","模拟授权公告，仅用于课程测试","jurisdiction","DEMO"):Map.of("notice","模拟记录，不作为真实科研评价依据");
        return new ImportService.WorkInput(type,titles[i%titles.length]+" · "+String.format("%05d",i+1),i%19==0?null:String.valueOf(2019+i%8),type.equals("PAPER")?"10.99999/demo."+(i+1):null,type.equals("PAPER")?null:"000"+(i+1),identifierType,type.equals("PAPER")?null:"DEMO",
            "本记录用于演示"+themes[i%8]+"领域的检索、统计和来源追踪。所有人物、题录、编号及评价数值均为人工构造；不是外部来源的真实科研成果。",
            type.equals("PAPER")?"示例计算研究学报":"课程模拟公告",type.equals("PAPER")&&i%3!=0?i%80:null,type.equals("PAPER")?"DemoCitation":null,i%3==0?"UNKNOWN":(i%3==1?"OPEN":"NOT_FOUND"),true,
            "demo-"+(i+1),"https://example.org/academic/demo/"+(i+1),people,List.of("I"+(i%4+1)),List.of(themes[i%8]),details);
    }
}
