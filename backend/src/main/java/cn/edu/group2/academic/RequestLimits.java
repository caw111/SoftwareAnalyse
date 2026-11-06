package cn.edu.group2.academic;

import java.io.*;
import java.util.concurrent.Semaphore;
import jakarta.servlet.*;
import jakarta.servlet.http.*;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

@Component
public class RequestLimits extends OncePerRequestFilter {
    private final Semaphore requests=new Semaphore(96);
    private static final int MAX_BODY=2*1024*1024;
    @Override protected void doFilterInternal(HttpServletRequest request,HttpServletResponse response,FilterChain chain) throws ServletException,IOException {
        response.setHeader("X-Content-Type-Options","nosniff");
        response.setHeader("Cache-Control","no-store");
        if(!requests.tryAcquire()) { reject(response,429,"BUSY","服务繁忙，请稍后重试");return; }
        try {
            if(request.getMethod().equals("POST")||request.getMethod().equals("PUT")) {
                byte[] body=request.getInputStream().readNBytes(MAX_BODY+1);
                if(body.length>MAX_BODY) {reject(response,413,"BODY_TOO_LARGE","批次不能超过 2 MiB");return;}
                request=new HttpServletRequestWrapper(request) {
                    @Override public ServletInputStream getInputStream() {
                        var input=new ByteArrayInputStream(body);
                        return new ServletInputStream() {
                            public int read() {return input.read();}
                            public int read(byte[] b,int off,int len) {return input.read(b,off,len);}
                            public boolean isFinished() {return input.available()==0;}
                            public boolean isReady() {return true;}
                            public void setReadListener(ReadListener l) {throw new UnsupportedOperationException();}
                        };
                    }
                };
            }
            chain.doFilter(request,response);
        } finally {requests.release();}
    }
    private static void reject(HttpServletResponse response,int status,String code,String message) throws IOException {
        response.setStatus(status);response.setContentType("application/json;charset=UTF-8");
        response.getWriter().write("{\"code\":\""+code+"\",\"message\":\""+message+"\"}");
    }
}
