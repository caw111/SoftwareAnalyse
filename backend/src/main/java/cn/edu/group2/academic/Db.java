package cn.edu.group2.academic;

import java.util.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

@Component
public class Db {
    final JdbcTemplate jdbc;
    public Db(JdbcTemplate jdbc) { this.jdbc = jdbc; }
    public List<Map<String,Object>> rows(String sql, Object... args) {
        return jdbc.query(sql, (rs, row) -> {
            Map<String,Object> value = new LinkedHashMap<>();
            var md = rs.getMetaData();
            for (int i=1;i<=md.getColumnCount();i++) {
                String[] parts = md.getColumnLabel(i).toLowerCase(Locale.ROOT).split("_");
                StringBuilder key = new StringBuilder(parts[0]);
                for (int j=1;j<parts.length;j++) key.append(Character.toUpperCase(parts[j].charAt(0))).append(parts[j].substring(1));
                value.put(key.toString(), rs.getObject(i));
            }
            return value;
        }, args);
    }
    public Map<String,Object> one(String sql, Object... args) {
        var rows = rows(sql,args);
        if (rows.isEmpty()) throw ApiException.notFound();
        return rows.getFirst();
    }
    public long count(String sql,Object...args) { return jdbc.queryForObject(sql,Long.class,args); }
    public int update(String sql,Object...args) { return jdbc.update(sql,args); }
    static String id() { return UUID.randomUUID().toString(); }
    static long now() { return System.currentTimeMillis(); }
}
