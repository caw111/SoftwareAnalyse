package cn.edu.group2.academic;

import java.util.*;
import jakarta.validation.constraints.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class ClaimService {
    final Db db;final ImportService audit;
    static final Set<String> TERMINAL=Set.of("APPROVED","REJECTED","WITHDRAWN");
    ClaimService(Db db,ImportService audit) {this.db=db;this.audit=audit;}
    public record Create(@NotBlank String kind,@NotBlank @Size(max=80) String targetId,
        @NotBlank @Size(max=10000) String evidence,@NotNull @Size(max=40) String contributionRole) {}
    public record Action(@Min(0) int version,@NotBlank String action,@NotNull @Size(max=2000) String reason,
        @Size(max=10000) String evidence) {}
    @Transactional
    public Map<String,Object> create(Create input,AuthService.Actor actor) {
        String label=validateTarget(input.kind(),input.targetId(),input.contributionRole(),actor.id());
        String active=actor.id()+":"+input.kind()+":"+input.targetId();
        var existing=db.rows("SELECT * FROM claim WHERE active_key=?",active);
        if(!existing.isEmpty()) return existing.getFirst();
        String id=Db.id();long now=Db.now();
        db.update("INSERT INTO claim(id,user_id,kind,target_id,target_label,evidence,contribution_role,state,version,material_version,active_key,reason,created_at,updated_at) VALUES(?,?,?,?,?,?,?,'DRAFT',0,1,?,'',?,?)",id,actor.id(),input.kind(),input.targetId(),label,input.evidence(),input.contributionRole(),active,now,now);
        audit.audit(actor.id(),id,"CREATE",null,"DRAFT","创建私有申请草稿");
        return db.one("SELECT * FROM claim WHERE id=?",id);
    }
    private String validateTarget(String kind,String target,String role,String userId) {
        var user=db.one("SELECT role FROM app_user WHERE id=? FOR UPDATE",userId);
        String userRole=user.get("role").toString();
        if(kind.equals("IDENTITY")) {
            if(!target.equals(userId)||!userRole.equals("USER")) throw ApiException.forbidden();
            return "科研人员身份申请";
        }
        if(!userRole.equals("RESEARCHER")) throw ApiException.forbidden();
        if(kind.equals("PORTAL")) {
            if(db.count("SELECT COUNT(*) FROM portal_binding WHERE user_id=?",userId)>0) throw ApiException.conflict("账号已绑定门户");
            return db.one("SELECT name FROM scholar WHERE id=?",target).get("name").toString();
        }
        if(!Set.of("OUTCOME","REVOKE").contains(kind)) throw ApiException.bad("申请类型不合法");
        if(db.count("SELECT COUNT(*) FROM portal_binding WHERE user_id=?",userId)!=1) throw ApiException.forbidden();
        var work=db.one("SELECT title,type FROM work WHERE id=?",target);
        String expected=switch(work.get("type").toString()) {case "PAPER"->"AUTHOR";case "PATENT"->"INVENTOR";case "PROJECT"->"PI";default->"AWARDEE";};
        if(!role.equals(expected)) throw ApiException.bad("贡献角色不适用于成果类型");
        boolean linked=db.count("SELECT COUNT(*) FROM outcome_binding WHERE user_id=? AND work_id=?",userId,target)>0;
        if(kind.equals("OUTCOME")&&linked) throw ApiException.conflict("已确认该成果贡献");
        if(kind.equals("REVOKE")&&!linked) throw ApiException.conflict("没有可撤销的本人贡献关系");
        return work.get("title").toString();
    }
    public Object list(AuthService.Actor actor,boolean review) {
        if(review) {actor.admin();return db.rows("SELECT c.*,u.display_name AS applicant_name FROM claim c JOIN app_user u ON u.id=c.user_id ORDER BY c.updated_at DESC,c.id LIMIT 200");}
        return db.rows("SELECT * FROM claim WHERE user_id=? ORDER BY updated_at DESC,id LIMIT 200",actor.id());
    }
    public Map<String,Object> page(AuthService.Actor actor,boolean review,int page,int size) {
        if(review) actor.admin();
        if(page<0||size<1||size>100) throw ApiException.bad("申请页码须从 0 开始，每页 1–100 条");
        long offset=(long)page*size;
        long total=review?db.count("SELECT COUNT(*) FROM claim"):db.count("SELECT COUNT(*) FROM claim WHERE user_id=?",actor.id());
        var items=review
            ?db.rows("SELECT c.*,u.display_name AS applicant_name FROM claim c JOIN app_user u ON u.id=c.user_id ORDER BY c.updated_at DESC,c.id LIMIT ? OFFSET ?",size,offset)
            :db.rows("SELECT * FROM claim WHERE user_id=? ORDER BY updated_at DESC,id LIMIT ? OFFSET ?",actor.id(),size,offset);
        return Map.of("items",items,"total",total,"page",page,"size",size);
    }
    public Object detail(String id,AuthService.Actor actor) {
        var claim=db.one("SELECT * FROM claim WHERE id=?",id);
        if(!claim.get("userId").equals(actor.id())&&!actor.role().equals("ADMIN")) throw ApiException.forbidden();
        claim.put("history",db.rows("SELECT action,before_state,after_state,reason,created_at FROM audit_event WHERE object_id=? ORDER BY sequence_no",id));
        return claim;
    }
    @Transactional
    public Map<String,Object> action(String id,Action input,AuthService.Actor actor) {
        var claim=db.one("SELECT * FROM claim WHERE id=? FOR UPDATE",id);
        boolean owner=claim.get("userId").equals(actor.id());
        if(!owner&&!actor.role().equals("ADMIN")) throw ApiException.forbidden();
        if(((Number)claim.get("version")).intValue()!=input.version()) throw ApiException.conflict("申请版本已变化，请刷新后操作");
        String state=claim.get("state").toString(),kind=claim.get("kind").toString();
        if(TERMINAL.contains(state)) throw ApiException.conflict("终审申请不可修改；再次申请请新建记录");
        switch(input.action()) {
            case "WITHDRAW" -> {
                if(!owner) throw ApiException.forbidden();
                transition(claim,"WITHDRAWN",actor.id(),"本人撤回");
            }
            case "SUBMIT" -> {
                if(!owner||!Set.of("DRAFT","NEED_MORE_INFO").contains(state)) throw ApiException.forbidden();
                if(state.equals("NEED_MORE_INFO")) {
                    if(input.evidence()==null||input.evidence().isBlank()) throw ApiException.bad("请提供补充材料");
                    db.update("UPDATE claim SET evidence=?,material_version=material_version+1 WHERE id=?",input.evidence(),id);
                }
                validateTarget(kind,claim.get("targetId").toString(),claim.get("contributionRole").toString(),actor.id());
                if(kind.equals("PORTAL")) {
                    transition(claim,"PENDING_VERIFICATION",actor.id(),"提交材料");
                    transition(claim,"VERIFYING",actor.id(),"开始本地结构与权限检查");
                }
                transition(claim,"PENDING_REVIEW",actor.id(),"本地必要检查通过，身份和证据由审核员人工核验");
            }
            case "TAKE" -> {
                actor.admin();
                if(state.equals("UNDER_REVIEW")&&claim.get("leaseUntil")!=null&&((Number)claim.get("leaseUntil")).longValue()<=Db.now()) transition(claim,"PENDING_REVIEW",actor.id(),"审核占用过期，重新领取");
                if(!claim.get("state").equals("PENDING_REVIEW")) throw ApiException.conflict("申请不在待审状态，或其他审核员仍在处理");
                db.update("UPDATE claim SET reviewer_id=?,lease_until=? WHERE id=?",actor.id(),Db.now()+10*60*1000,id);
                transition(claim,"UNDER_REVIEW",actor.id(),"领取审核，10 分钟有效");
            }
            case "RELEASE" -> {
                requireLease(claim,actor);
                transition(claim,"PENDING_REVIEW",actor.id(),"主动释放审核占用");
            }
            case "APPROVE","REJECT","NEED_MORE_INFO" -> {
                requireLease(claim,actor);
                if(input.reason().isBlank()) throw ApiException.bad("审核必须填写依据或补充项");
                if(input.action().equals("APPROVE")) authorize(claim);
                String next=switch(input.action()) {case "APPROVE"->"APPROVED";case "REJECT"->"REJECTED";default->"NEED_MORE_INFO";};
                transition(claim,next,actor.id(),input.reason());
            }
            default -> throw ApiException.bad("不支持的操作");
        }
        return db.one("SELECT * FROM claim WHERE id=?",id);
    }
    private void requireLease(Map<String,Object> claim,AuthService.Actor actor) {
        actor.admin();
        if(!claim.get("state").equals("UNDER_REVIEW")||!actor.id().equals(claim.get("reviewerId"))||claim.get("leaseUntil")==null||((Number)claim.get("leaseUntil")).longValue()<=Db.now()) throw ApiException.conflict("审核占用无效或已过期，请重新领取");
    }
    private void authorize(Map<String,Object> claim) {
        String user=claim.get("userId").toString(),target=claim.get("targetId").toString(),kind=claim.get("kind").toString(),role=claim.get("contributionRole").toString();
        validateTarget(kind,target,role,user);
        switch(kind) {
            case "IDENTITY" -> db.update("UPDATE app_user SET role='RESEARCHER' WHERE id=?",user);
            case "PORTAL" -> {
                if(db.count("SELECT COUNT(*) FROM portal_binding WHERE scholar_id=?",target)>0) throw ApiException.conflict("门户已有管理绑定，需人工处理争议");
                db.update("INSERT INTO portal_binding VALUES(?,?)",user,target);
            }
            case "OUTCOME" -> db.update("INSERT INTO outcome_binding(user_id,work_id,scholar_id,contribution_role) SELECT ?,?,scholar_id,? FROM portal_binding WHERE user_id=?",user,target,role,user);
            case "REVOKE" -> db.update("DELETE FROM outcome_binding WHERE user_id=? AND work_id=?",user,target);
            default -> throw ApiException.bad("申请类型不合法");
        }
    }
    private void transition(Map<String,Object> claim,String next,String actor,String reason) {
        String before=claim.get("state").toString();int version=((Number)claim.get("version")).intValue();
        int changed=db.update("UPDATE claim SET state=?,version=version+1,reason=?,updated_at=?,active_key=CASE WHEN ? THEN NULL ELSE active_key END WHERE id=? AND version=?",next,reason,Db.now(),TERMINAL.contains(next),claim.get("id"),version);
        if(changed!=1) throw ApiException.conflict("申请已变化");
        if(!next.equals("UNDER_REVIEW")) db.update("UPDATE claim SET reviewer_id=NULL,lease_until=NULL WHERE id=?",claim.get("id"));
        audit.audit(actor,claim.get("id").toString(),"CLAIM_TRANSITION",before,next,reason);
        claim.put("state",next);claim.put("version",version+1);
    }
    Object myOutcomes(AuthService.Actor actor) {
        actor.researcher();
        return db.rows("SELECT w.id,w.title,w.type,w.year,b.contribution_role FROM outcome_binding b JOIN work w ON w.id=b.work_id WHERE b.user_id=? ORDER BY w.year DESC NULLS LAST,w.id LIMIT 500",actor.id());
    }
}
