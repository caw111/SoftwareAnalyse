package cn.edu.group2.academic;

import java.net.URI;
import java.util.*;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.ObjectMapper;

@Service
public class ProfileService {
    private final Db db;
    private final AuthService auth;
    private final ImportService audit;
    private final ObjectMapper json;
    ProfileService(Db db,AuthService auth,ImportService audit,ObjectMapper json) {
        this.db=db;this.auth=auth;this.audit=audit;this.json=json;
    }
    public record Website(@NotBlank @Size(max=60) String label,@NotBlank @Size(max=2048) String url) {}
    public record Update(@NotBlank @Size(max=100) String displayName,
        @NotNull @Size(max=80) String orcid,@NotNull @Size(max=8) List<@NotNull @Valid Website> websites,
        @NotNull @Size(max=4000) String aboutMe,@NotNull @Min(0) Integer version) {}

    @Transactional
    public Map<String,Object> update(Update input,AuthService.Actor actor) {
        String name=input.displayName().strip(),orcid=normalizeOrcid(input.orcid());
        if(name.isBlank()) throw ApiException.bad("姓名不能为空");
        var websites=new ArrayList<Website>();
        var urls=new HashSet<String>();
        for(var entry:input.websites()) {
            String label=entry.label().strip(),url=entry.url().strip();
            if(label.isBlank()||!validWebsite(url)) throw ApiException.bad("网站须填写名称和有效的 HTTP/HTTPS 地址，不能包含登录凭据");
            if(!urls.add(url)) throw ApiException.bad("网站地址不能重复");
            websites.add(new Website(label,url));
        }
        // A single conditional write protects all profile fields from stale edits across API instances.
        int updated=db.update("""
            UPDATE app_user SET display_name=?,orcid=?,websites_json=?,about_me=?,profile_version=profile_version+1
            WHERE id=? AND profile_version=?
            """,name,orcid,json.writeValueAsString(websites),input.aboutMe().strip(),actor.id(),input.version());
        if(updated!=1) throw ApiException.conflict("个人资料已在其他窗口更新，请刷新后重新编辑");
        audit.audit(actor.id(),actor.id(),"PROFILE_UPDATE",null,null,"更新本人附加资料");
        return auth.profile(actor);
    }
    private static boolean validWebsite(String value) {
        try {
            URI uri=URI.create(value);
            String scheme=uri.getScheme();
            return scheme!=null&&(scheme.equalsIgnoreCase("http")||scheme.equalsIgnoreCase("https"))
                &&uri.getHost()!=null&&!uri.getHost().isBlank()&&uri.getRawUserInfo()==null
                &&uri.getPort()<=65535&&uri.getPort()>=-1;
        } catch(IllegalArgumentException ignored) {return false;}
    }
    static String normalizeOrcid(String value) {
        String orcid=value.strip().replaceFirst("(?i)^https?://orcid\\.org/", "").toUpperCase(Locale.ROOT);
        if(orcid.isEmpty()) return "";
        if(!orcid.matches("[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]"))
            throw ApiException.bad("ORCID 须为 0000-0000-0000-0000 格式");
        String digits=orcid.replace("-", "");
        int total=0;
        for(int i=0;i<15;i++) total=(total+digits.charAt(i)-'0')*2;
        int check=(12-total%11)%11;
        char expected=check==10?'X':(char)('0'+check);
        if(digits.charAt(15)!=expected) throw ApiException.bad("ORCID 校验位不正确，请核对完整编号");
        return orcid;
    }
}
