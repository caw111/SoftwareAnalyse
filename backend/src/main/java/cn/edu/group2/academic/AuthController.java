package cn.edu.group2.academic;

import java.util.Map;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/auth")
public class AuthController {
    private final AuthService auth;
    AuthController(AuthService auth) {this.auth=auth;}
    record Login(@NotBlank @Size(max=80) String username,@NotBlank @Size(max=128) String password) {}
    record Register(@NotBlank @Size(max=80) String username,@NotBlank @Size(max=128) String password,@NotBlank @Size(max=100) String displayName) {}
    @PostMapping("/login") Object login(@Valid @RequestBody Login body) {return auth.login(body.username(),body.password());}
    @PostMapping("/register") Object register(@Valid @RequestBody Register body) {return auth.register(body.username(),body.password(),body.displayName());}
    @GetMapping("/me") Object me(HttpServletRequest request) {return auth.profile(auth.require(request));}
    @PostMapping("/logout") Object logout(HttpServletRequest request) {auth.logout(request);return Map.of("message","已退出");}
}
