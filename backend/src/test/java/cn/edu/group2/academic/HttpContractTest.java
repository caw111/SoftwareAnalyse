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
    "app.demo=true","app.demo-count=64","management.server.port=0"})
class HttpContractTest {
    @LocalServerPort int port;
    @Autowired ObjectMapper json;
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
}
