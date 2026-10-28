"""要約を250文字ちょうどにそろえる。

〔...〕で囲んだ部分は「省いても文が成り立つ」部分。前に書いたものほど大事とみなす。
加えて、省いても意味が変わらない副詞（大きく・さらに など）と、
文の切れ目の読点（「〜て、」「〜が、」など。列挙の読点は対象外）も細かな調整に使う。
条件を満たす組み合わせのうち、残る中身の価値が最も高いものを選ぶ。"""
import itertools, json, re, sys

TARGET = 250
PAT = re.compile(r"〔(.*?)〕")
ADVERBS = ["大きく", "さらに", "ひとまず", "特に", "とくに", "幅広く", "わずかに", "改めて", "すでに", "新しく", "少し", "今のところ"]
CLAUSE_END = set("てでりがしくらばずきもはに")  # この字の直後の読点は省いても読める
MAXCOMMA = 3

ALTS = [("米連邦公開市場委員会（FOMC）", "FOMC"), ("欧州中央銀行（ECB）", "ECB"), ("ニューヨーク", "NY"),
        ("前の日より", "前日より"), ("前の月より", "前月より"), ("前の週", "前週"), ("取引を終えた", "終えた"),
        ("日経平均株価", "日経平均"), ("ことが分かった", "と分かった"), ("と発表した", "と公表した"),
        ("1年前と比べると", "前年比で"), ("情報処理推進機構", "IPA")]

# 短い表現を、意味を変えずに少し長くできる言い換え（短い表現, 長い表現）
EXPAND = [("社説は", "毎日新聞の社説は"), ("だ。", "である。")]

def micro(text):
    """〔〕の外にある副詞を、価値の低い任意部分として印をつける（各語の最初の1回）。
    言い換え（長い表現｜短い表現）は〈A|B〉として印をつける。"""
    for a, b in ALTS:
        if a in text and "〈" + a not in text:
            text = text.replace(a, "〈" + a + "|" + b + "〉", 1)
    for short, long in EXPAND:
        if long in text: continue
        # 〔〕や〈〉の外で最初に出てくる短い表現を言い換え候補にする
        parts = re.split(r"(〔.*?〕|〈.*?〉)", text)
        for i, p in enumerate(parts):
            if p.startswith(("〔", "〈")): continue
            j = p.find(short)
            if j >= 0:
                parts[i] = p[:j] + "〈" + long + "|" + short + "〉" + p[j+len(short):]
                break
        text = "".join(parts)
    parts = re.split(r"(〔.*?〕)", text)
    used = set()
    for i, p in enumerate(parts):
        if p.startswith("〔"): continue
        for w in ADVERBS:
            if w in used: continue
            j = p.find(w)
            if j >= 0:
                p = p[:j] + "《" + w + "》" + p[j+len(w):]
                used.add(w)
        parts[i] = p
    return "".join(parts)

def droppable_commas(t):
    out = []
    for i, c in enumerate(t):
        if c != "、" or i == 0: continue
        prev, nxt = t[i-1], t[i+1] if i+1 < len(t) else ""
        if prev in CLAUSE_END and not nxt.isdigit():
            out.append(i)
    return out

def render(text, keep_opt, keep_adv, long_alt=None):
    oi = iter(range(10**6)); ai = iter(range(10**6)); li = iter(range(10**6))
    t = re.sub(r"〔(.*?)〕", lambda m: m.group(1) if next(oi) in keep_opt else "", text)
    t = re.sub(r"《(.*?)》", lambda m: m.group(1) if next(ai) in keep_adv else "", t)
    la = long_alt if long_alt is not None else set()
    t = re.sub(r"〈(.*?)\|(.*?)〉", lambda m: m.group(1) if next(li) in la else m.group(2), t)
    return t

def fit(text):
    text = micro(text)
    opts = PAT.findall(text)
    advs = re.findall(r"《(.*?)》", text)
    alts = re.findall(r"〈(.*?)\|(.*?)〉", text)
    n, m, a = len(opts), len(advs), len(alts)
    best = None
    for keep_o in itertools.product([1, 0], repeat=n):
        ko = {i for i in range(n) if keep_o[i]}
        # 前の任意部分ほど価値が高い
        vo = sum((n - i) * 10 for i in ko)
        for keep_a in itertools.product([1, 0], repeat=m + a):
            ka = {i for i in range(m) if keep_a[i]}
            la = {i for i in range(a) if keep_a[m + i]}
            t = render(text, ko, ka, la)
            over = len(t) - TARGET
            if over < 0: continue
            cs = droppable_commas(t)
            if over > min(MAXCOMMA, len(cs)): continue
            score = vo + len(ka) * 3 + len(la) * 2 - over * 4
            if best is None or score > best[0]:
                # 後ろの方の読点から省く
                for i in sorted(cs[-over:] if over else [], reverse=True):
                    t = t[:i] + t[i+1:]
                best = (score, t)
    if best is None:
        base = render(text, set(), set(), set())
        full = render(text, set(range(n)), set(range(m)), set(range(a)))
        return None, f"組み合わせなし（最短{len(base)}字・最長{len(full)}字・任意{[len(o) for o in opts]}）"
    assert len(best[1]) == TARGET, len(best[1])
    return best[1], "ok"

if __name__ == "__main__":
    src = json.load(open(sys.argv[1], encoding="utf8"))
    res, bad = {}, {}
    for k, t in src.items():
        out, msg = fit(t)
        if out: res[k] = out
        else: bad[k] = msg
    json.dump(res, open(sys.argv[2], "w", encoding="utf8"), ensure_ascii=False, indent=1)
    print(f"ok {len(res)} / {len(src)}")
    for k, m in bad.items(): print("NG", k, m)
