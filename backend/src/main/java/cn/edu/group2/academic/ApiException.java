package cn.edu.group2.academic;

public class ApiException extends RuntimeException {
    final int status;
    final String code;
    ApiException(int status,String code,String message) { super(message); this.status=status; this.code=code; }
    static ApiException bad(String message) { return new ApiException(400,"INVALID_INPUT",message); }
    static ApiException forbidden() { return new ApiException(403,"FORBIDDEN","无权进行此操作"); }
    static ApiException conflict(String message) { return new ApiException(409,"VERSION_CONFLICT",message); }
    static ApiException notFound() { return new ApiException(404,"NOT_FOUND","记录不存在或不可访问"); }
}
