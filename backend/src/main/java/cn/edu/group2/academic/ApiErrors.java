package cn.edu.group2.academic;

import java.util.Map;
import org.slf4j.LoggerFactory;
import org.springframework.dao.*;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.servlet.resource.NoResourceFoundException;
import org.springframework.web.HttpRequestMethodNotSupportedException;

@RestControllerAdvice
public class ApiErrors {
    @ExceptionHandler(ApiException.class)
    ResponseEntity<?> business(ApiException e) { return response(e.status,e.code,e.getMessage()); }
    @ExceptionHandler({MethodArgumentNotValidException.class,HttpMessageNotReadableException.class,MethodArgumentTypeMismatchException.class,MissingServletRequestParameterException.class})
    ResponseEntity<?> invalid(Exception e) { return response(400,"INVALID_INPUT","参数格式不正确，请检查必填项、长度和数据类型"); }
    @ExceptionHandler(NoResourceFoundException.class)
    ResponseEntity<?> missing(Exception e) { return response(404,"NOT_FOUND","接口不存在"); }
    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    ResponseEntity<?> method(Exception e) { return response(405,"METHOD_NOT_ALLOWED","请求方法不支持"); }
    @ExceptionHandler(DataIntegrityViolationException.class)
    ResponseEntity<?> duplicate(Exception e) { return response(409,"CONSTRAINT_CONFLICT","数据关系已变化或存在重复，请刷新后重试"); }
    @ExceptionHandler({QueryTimeoutException.class,CannotAcquireLockException.class})
    ResponseEntity<?> timeout(Exception e) { return response(503,"BUSY","请求超时或资源繁忙，请稍后重试"); }
    @ExceptionHandler(Exception.class)
    ResponseEntity<?> unexpected(Exception e) {
        // Do not log request bodies, tokens or claim evidence.
        LoggerFactory.getLogger(ApiErrors.class).error("API failure type={}",e.getClass().getName());
        return response(500,"INTERNAL_ERROR","服务暂时不可用，请联系管理员查看运行记录");
    }
    static ResponseEntity<?> response(int status,String code,String message) {
        return ResponseEntity.status(status).body(Map.of("code",code,"message",message));
    }
}
