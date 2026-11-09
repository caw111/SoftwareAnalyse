package cn.edu.group2.academic;

import java.nio.charset.StandardCharsets;
import java.security.*;
import java.util.*;
import java.util.concurrent.Semaphore;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.security.crypto.password.Pbkdf2PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.ObjectMapper;

@Service
public class AuthService {
    private final Db db;
    private final ObjectMapper json;
    private final Pbkdf2PasswordEncoder encoder = Pbkdf2PasswordEncoder.defaultsForSpringSecurity_v5_8();
    private final Semaphore passwordSlots = new Semaphore(2);
    private final SecureRandom random = new SecureRandom();
    private final String dummyHash;
    public AuthService(Db db,ObjectMapper json) { this.db=db; this.json=json; dummyHash=encoder.encode("unused-timing-equalizer"); }
    record Actor(String id,String username,String displayName,String role) {
        void admin() { if (!role.equals("ADMIN")) throw ApiException.forbidden(); }
        void researcher() { if (!role.equals("RESEARCHER")) throw ApiException.forbidden(); }
    }
    public Actor require(HttpServletRequest request) {
        String header=request.getHeader("Authorization");
        if(header==null||!header.startsWith("Bearer ")||header.length()>200) throw unauthorized();
        var rows=db.rows("SELECT u.id,u.username,u.display_name,u.role FROM auth_session s JOIN app_user u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>?", hash(header.substring(7)),Db.now());
        if(rows.isEmpty()) throw unauthorized();
        var u=rows.getFirst();
        return new Actor(u.get("id").toString(),u.get("username").toString(),u.get("displayName").toString(),u.get("role").toString());
    }
    public Map<String,Object> profile(Actor actor) {
        var value=new LinkedHashMap<>(db.one("""
            SELECT u.id,u.username,u.display_name,u.role,u.orcid,u.websites_json,u.about_me,u.profile_version,
                   p.scholar_id,s.name AS scholar_name,s.institution_id,i.name AS institution_name
            FROM app_user u LEFT JOIN portal_binding p ON p.user_id=u.id
            LEFT JOIN scholar s ON s.id=p.scholar_id LEFT JOIN institution i ON i.id=s.institution_id
            WHERE u.id=?
            """,actor.id()));
        value.put("websites",json.readTree(value.remove("websitesJson").toString()));
        return value;
    }
    @Transactional
    public Map<String,Object> login(String username,String password) {
        enterPasswordSlot();
        try {
            var users=db.rows("SELECT * FROM app_user WHERE username=?",username.toLowerCase(Locale.ROOT));
            boolean valid=encoder.matches(password,users.isEmpty()?dummyHash:users.getFirst().get("passwordHash").toString());
            if(users.isEmpty()||!valid) throw new ApiException(401,"INVALID_CREDENTIALS","账号或密码不正确");
            var u=users.getFirst();
            byte[] bytes=new byte[32];random.nextBytes(bytes);
            String token=Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
            long expiry=Db.now()+8*60*60*1000L;
            db.update("DELETE FROM auth_session WHERE expires_at<=?",Db.now());
            db.update("INSERT INTO auth_session(token_hash,user_id,expires_at) VALUES(?,?,?)",hash(token),u.get("id"),expiry);
            return Map.of("token",token,"expiresAt",expiry,"user",profile(new Actor(u.get("id").toString(),username,u.get("displayName").toString(),u.get("role").toString())));
        } finally { passwordSlots.release(); }
    }
    @Transactional
    public Map<String,Object> register(String username,String password,String displayName) {
        if(!username.matches("[a-zA-Z0-9_.-]{3,40}")||password.length()<12||password.length()>128||displayName.isBlank()||displayName.length()>100) throw ApiException.bad("账号为 3–40 位字母数字，密码为 12–128 位，姓名不能为空");
        enterPasswordSlot();
        try {
            String id=createUser(username.toLowerCase(Locale.ROOT),password,displayName,"USER");
            return Map.of("id",id,"message","注册成功，请登录；科研人员身份需另行申请审核");
        } finally {passwordSlots.release();}
    }
    String createUser(String username,String password,String displayName,String role) {
        String id=Db.id();
        db.update("INSERT INTO app_user(id,username,password_hash,display_name,role,created_at) VALUES(?,?,?,?,?,?)",id,username,encoder.encode(password),displayName,role,Db.now());
        return id;
    }
    void logout(HttpServletRequest request) {
        require(request);
        db.update("DELETE FROM auth_session WHERE token_hash=?",hash(request.getHeader("Authorization").substring(7)));
    }
    private void enterPasswordSlot() { if(!passwordSlots.tryAcquire()) throw new ApiException(429,"AUTH_BUSY","登录请求较多，请稍后重试"); }
    private static ApiException unauthorized() { return new ApiException(401,"UNAUTHENTICATED","请登录，或重新登录以更新会话"); }
    static String hash(String value) {
        try { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8))); }
        catch(NoSuchAlgorithmException e) { throw new IllegalStateException(e); }
    }
}
