package cn.edu.group2.academic;

import java.text.Normalizer;
import java.util.*;
import java.util.regex.Pattern;

/** Versioned, deterministic bilingual tokenizer; no inferred discipline labels. */
public final class SearchTerms {
    public static final String VERSION="unicode-cjk-bigram-v1";
    private static final Pattern PARTS=Pattern.compile("[\\p{IsHan}]+|[\\p{L}\\p{N}]+(?:[+#][+#]?)?");
    private static final Set<String> STOP=Set.of("a","an","the","of","and","or","for","in","on","to","with","by","is","are","as","at","from","this","that","be","we","our","using","study","analysis","based","et","al");
    private SearchTerms() {}
    public static List<String> tokens(String text) {
        List<String> result=new ArrayList<>();
        var matcher=PARTS.matcher(Normalizer.normalize(Objects.toString(text,""),Normalizer.Form.NFKC).toLowerCase(Locale.ROOT));
        while(matcher.find()) {
            String word=matcher.group();
            if(Character.UnicodeScript.of(word.codePointAt(0))==Character.UnicodeScript.HAN) {
                int[] chars=word.codePoints().toArray();
                for(int i=0;i<chars.length;i++) {
                    result.add(new String(chars,i,1));
                    if(i+1<chars.length) result.add(new String(chars,i,2));
                }
            } else if(word.length()<=120) result.add(word);
        }
        return result;
    }
    public static List<String> query(String text) {
        var terms=new LinkedHashSet<String>();
        var matcher=PARTS.matcher(Normalizer.normalize(Objects.toString(text,""),Normalizer.Form.NFKC).toLowerCase(Locale.ROOT));
        while(matcher.find()) {
            String word=matcher.group();int[] chars=word.codePoints().toArray();
            if(Character.UnicodeScript.of(chars[0])==Character.UnicodeScript.HAN&&chars.length>1)
                for(int i=0;i+1<chars.length;i++) terms.add(new String(chars,i,2));
            else if(word.length()<=120) terms.add(word);
        }
        if(terms.size()>40) throw ApiException.bad("检索词项过多，请缩短关键词");
        return List.copyOf(terms);
    }
    public static boolean isHotspot(String term) {
        return term.codePointCount(0,term.length())>=2&&!STOP.contains(term)&&!term.chars().allMatch(Character::isDigit);
    }
}
