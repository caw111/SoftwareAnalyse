package cn.edu.group2.academic;

import static org.junit.jupiter.api.Assertions.*;
import java.net.URI;
import java.net.http.*;
import java.util.*;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import tools.jackson.databind.ObjectMapper;

@SpringBootTest(webEnvironment=SpringBootTest.WebEnvironment.RANDOM_PORT,properties={
    "spring.datasource.url=${TEST_DB_URL:jdbc:h2:mem:httpcontracts;MODE=PostgreSQL;DATABASE_TO_LOWER=TRUE;DEFAULT_NULL_ORDERING=HIGH;NON_KEYWORDS=YEAR;DB_CLOSE_DELAY=-1}",
    "spring.datasource.username=${TEST_DB_USER:sa}","spring.datasource.password=${TEST_DB_PASSWORD:}",
    "app.demo=true","app.demo-count=64","management.server.port=0","app.crawl.worker-enabled=false"})
class HttpContractTest {
    @LocalServerPort int port;
    @Autowired ObjectMapper json;
    @Autowired Db db;
    final HttpClient client=HttpClient.newHttpClient();
    HttpResponse<String> request(String method,String path,String body,String token) throws Exception {
        var builder=HttpRequest.newBuilder(URI.create("http://127.0.0.1:"+port+path)).header("Content-Type","application/json");
        if(token!=null) builder.header("Authorization","Bearer "+token);
        builder.method(method,body==null?HttpRequest.BodyPublishers.noBody():HttpRequest.BodyPublishers.ofString(body));
        return client.send(builder.build(),HttpResponse.BodyHandlers.ofString());
    }
    String login(String username,String password) throws Exception {
        var response=request("POST","/api/auth/login",json.writeValueAsString(Map.of("username",username,"password",password)),null);
        assertEquals(200,response.statusCode(),response.body());return json.readTree(response.body()).get("token").asText();
    }
    @Test void publicCatalogAndExplicitClientErrors() throws Exception {
        var response=request("GET","/api/works?dataset=demo&size=1",null,null);
        assertEquals(200,response.statusCode());assertTrue(json.readTree(response.body()).get("total").asLong()>=64);
        assertEquals(400,request("GET","/api/works?from=2026&to=2020",null,null).statusCode());
        assertEquals(400,request("GET","/api/graph/path",null,null).statusCode());
        assertEquals(404,request("GET","/api/missing",null,null).statusCode());
    }
    @Test void anonymousAndReaderCannotAccessAdmin() throws Exception {
        assertEquals(401,request("GET","/api/admin/imports",null,null).statusCode());
        String token=login("reader","DemoPass2026!");
        assertEquals(403,request("GET","/api/admin/imports",null,token).statusCode());
        assertEquals(403,request("GET","/api/claims?review=true",null,token).statusCode());
        assertEquals(401,request("GET","/api/admin/statistics",null,null).statusCode());
        assertEquals(403,request("GET","/api/admin/statistics",null,token).statusCode());
        assertEquals(403,request("GET","/api/claims?review=true&page=0&size=10",null,token).statusCode());
        for(String path:List.of("/api/admin/crawl/sources","/api/admin/crawl/tasks","/api/admin/crawl/checkpoints","/api/admin/quality")) {
            assertEquals(401,request("GET",path,null,null).statusCode(),path);
            assertEquals(403,request("GET",path,null,token).statusCode(),path);
        }
        String task=json.writeValueAsString(Map.of("sourceId","crossref","doi","10.1038/nphys1170","pageSize",1,"maxPages",1,"maxRecords",1));
        assertEquals(401,request("POST","/api/admin/crawl/tasks",task,null).statusCode());
        assertEquals(403,request("POST","/api/admin/crawl/tasks",task,token).statusCode());
    }
    @Test void logoutRevokesTokenAndRegistrationDoesNotAcceptRoleEscalation() throws Exception {
        String username="http-"+Db.id().substring(0,10),password="HttpTest2026Password!";
        assertEquals(200,request("POST","/api/auth/register",json.writeValueAsString(Map.of("username",username,"password",password,"displayName","Test","role","ADMIN")),null).statusCode());
        String token=login(username,password);
        var me=request("GET","/api/auth/me",null,token);assertEquals("USER",json.readTree(me.body()).get("role").asText());
        assertEquals(200,request("POST","/api/auth/logout","{}",token).statusCode());
        assertEquals(401,request("GET","/api/auth/me",null,token).statusCode());
    }
    @Test void oversizedAndInvalidPayloadsAreRejected() throws Exception {
        assertEquals(400,request("POST","/api/auth/login","{broken",null).statusCode());
        assertEquals(400,request("POST","/api/auth/login","{\"username\":\"\",\"password\":\"\"}",null).statusCode());
        assertEquals(413,request("POST","/api/admin/imports","x".repeat(2*1024*1024+1),null).statusCode());
    }

    String newAccount() throws Exception {
        String username="profile-"+Db.id().substring(0,10),password="ProfileTest2026!";
        assertEquals(200,request("POST","/api/auth/register",json.writeValueAsString(Map.of(
            "username",username,"password",password,"displayName","Original")),null).statusCode());
        return login(username,password);
    }
    Map<String,Object> profileInput(int version) {
        return new LinkedHashMap<>(Map.of("displayName","研究者甲","orcid","https://orcid.org/0000-0002-1825-0097",
            "websites",List.of(Map.of("label","GitHub","url","https://github.com/example")),
            "aboutMe","研究方向与公开成果介绍","version",version));
    }
    @Test void personalProfilePersistsWithoutEscalatingPermissionsOrChangingAnotherAccount() throws Exception {
        String token=newAccount(),other=newAccount();
        var input=profileInput(0);
        input.put("role","ADMIN");input.put("scholarId","S1");
        assertEquals(401,request("POST","/api/me/profile",json.writeValueAsString(input),null).statusCode());
        var response=request("POST","/api/me/profile",json.writeValueAsString(input),token);
        assertEquals(200,response.statusCode(),response.body());
        var saved=json.readTree(response.body());
        assertEquals("研究者甲",saved.get("displayName").asText());
        assertEquals("0000-0002-1825-0097",saved.get("orcid").asText());
        assertEquals(1,saved.get("profileVersion").asInt());
        assertEquals("USER",saved.get("role").asText());assertTrue(saved.get("scholarId").isNull());
        assertEquals("https://github.com/example",saved.get("websites").get(0).get("url").asText());
        assertEquals("研究方向与公开成果介绍",saved.get("aboutMe").asText());
        assertEquals(saved,json.readTree(request("GET","/api/auth/me",null,token).body()));
        var untouched=json.readTree(request("GET","/api/auth/me",null,other).body());
        assertEquals("Original",untouched.get("displayName").asText());
        assertEquals(0,untouched.get("profileVersion").asInt());assertEquals(0,untouched.get("websites").size());
        assertEquals(403,request("POST","/api/claims",json.writeValueAsString(Map.of(
            "kind","PORTAL","targetId","S1","evidence","Not verified","contributionRole","")),token).statusCode());
    }
    @Test void staleProfileEditCannotOverwriteNewerValues() throws Exception {
        String token=newAccount();
        assertEquals(200,request("POST","/api/me/profile",json.writeValueAsString(profileInput(0)),token).statusCode());
        var stale=profileInput(0);stale.put("displayName","Stale edit");
        assertEquals(409,request("POST","/api/me/profile",json.writeValueAsString(stale),token).statusCode());
        var current=json.readTree(request("GET","/api/auth/me",null,token).body());
        assertEquals("研究者甲",current.get("displayName").asText());
        var clear=profileInput(1);clear.put("orcid","");clear.put("websites",List.of());clear.put("aboutMe","");
        var response=request("POST","/api/me/profile",json.writeValueAsString(clear),token);
        assertEquals(200,response.statusCode(),response.body());
        assertEquals(2,json.readTree(response.body()).get("profileVersion").asInt());
        assertEquals(0,json.readTree(response.body()).get("websites").size());
    }
    @Test void unsafeLinksInvalidOrcidAndUnboundedProfilesAreRejectedAtomically() throws Exception {
        String token=newAccount();
        for(String url:List.of("javascript:alert(1)","file:///C:/Windows/system.ini","ftp://example.org/file",
                "https://user:password@example.org/","https:///missing-host","https://example.org:70000")) {
            var input=profileInput(0);input.put("websites",List.of(Map.of("label","Website","url",url)));
            assertEquals(400,request("POST","/api/me/profile",json.writeValueAsString(input),token).statusCode(),url);
        }
        var invalid=profileInput(0);invalid.put("orcid","0000-0002-1825-0098");
        assertEquals(400,request("POST","/api/me/profile",json.writeValueAsString(invalid),token).statusCode());
        invalid=profileInput(0);invalid.put("websites",Collections.nCopies(9,Map.of("label","Web","url","https://example.org/")));
        assertEquals(400,request("POST","/api/me/profile",json.writeValueAsString(invalid),token).statusCode());
        invalid=profileInput(0);invalid.remove("version");
        assertEquals(400,request("POST","/api/me/profile",json.writeValueAsString(invalid),token).statusCode());
        var unchanged=json.readTree(request("GET","/api/auth/me",null,token).body());
        assertEquals(0,unchanged.get("profileVersion").asInt());assertEquals("Original",unchanged.get("displayName").asText());
    }
    @Test void pagedApplicationsIncludeOnlyOwnerAndAdminSummaryRequiresAdmin() throws Exception {
        String token=newAccount(),other=newAccount();
        String owner=json.readTree(request("GET","/api/auth/me",null,token).body()).get("id").asText();
        String foreign=json.readTree(request("GET","/api/auth/me",null,other).body()).get("id").asText();
        for(int i=0;i<3;i++) {
            String id=Db.id(),user=i<2?owner:foreign;
            db.update("""
                INSERT INTO claim(id,user_id,kind,target_id,target_label,evidence,contribution_role,state,version,material_version,reason,created_at,updated_at)
                VALUES(?,?,'IDENTITY',?,'Test identity','Private evidence','','WITHDRAWN',1,1,'Test fixture',?,?)
                """,id,user,user,Db.now(),Db.now()+i);
        }
        var first=json.readTree(request("GET","/api/claims?page=0&size=1",null,token).body());
        var second=json.readTree(request("GET","/api/claims?page=1&size=1",null,token).body());
        assertEquals(2,first.get("total").asInt());assertEquals(1,first.get("items").size());
        assertEquals(owner,first.get("items").get(0).get("userId").asText());
        assertEquals(owner,second.get("items").get(0).get("userId").asText());
        assertNotEquals(first.get("items").get(0).get("id"),second.get("items").get(0).get("id"));
        assertEquals(0,json.readTree(request("GET","/api/claims?page=2&size=1",null,token).body()).get("items").size());
        assertEquals(2,json.readTree(request("GET","/api/claims",null,token).body()).size());
        assertEquals(400,request("GET","/api/claims?page=-1&size=1",null,token).statusCode());
        assertEquals(400,request("GET","/api/claims?page=0&size=101",null,token).statusCode());
        var statistics=request("GET","/api/admin/statistics",null,login("admin","DemoPass2026!"));
        assertEquals(200,statistics.statusCode(),statistics.body());
        var summary=json.readTree(statistics.body());
        assertTrue(summary.get("catalogTotal").asLong()>=64);
        assertEquals(summary.get("catalogTotal").asLong(),summary.get("realCatalogTotal").asLong()+summary.get("demoCatalogTotal").asLong());
        assertEquals(4,summary.get("byType").size());
    }
}
