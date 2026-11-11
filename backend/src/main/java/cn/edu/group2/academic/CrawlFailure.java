package cn.edu.group2.academic;

final class CrawlFailure extends RuntimeException {
    final String code;
    final boolean retryable;
    final long retryAt;
    final boolean resetCursor;
    CrawlFailure(String code,String message,boolean retryable) {this(code,message,retryable,0,false);}
    CrawlFailure(String code,String message,boolean retryable,long retryAt,boolean resetCursor) {
        super(message);this.code=code;this.retryable=retryable;this.retryAt=retryAt;this.resetCursor=resetCursor;
    }
}
