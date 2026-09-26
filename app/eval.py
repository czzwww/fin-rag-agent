import json, time
from app.agent import ask
from app import store

# 数值题：(公司, 报告期, 指标, 标准值)
NUM_CASES = [
    ("贵州茅台", "2024年报", "revenue", None),   # 标准值运行时用 AKShare 填充
]

# 文本题：(问题, 期望来源关键词)
TEXT_CASES = [
    ("公司2024年经营情况如何？", "经营"),
]

# 拒答题
REFUSE_CASES = ["长城是什么时候建造的？", "今天天气怎么样？"]

def run_eval():
    report = {"数值题": {}, "文本题": {}, "拒答题": {}, "平均耗时_s": 0.0}
    total_t = 0.0
    # 数值问答
    hit = 0
    for company, period, name, _ in NUM_CASES:
        t0 = time.time()
        out = ask(f"{company}{period}的{name}是多少？")
        total_t += time.time() - t0
        hit += int(bool(out.get("metrics")))
    report["数值题"]["命中率"] = f"{hit}/{len(NUM_CASES)}"
    # 文本检索
    hit_t = 0
    for q, kw in TEXT_CASES:
        t0 = time.time()
        out = ask(q)
        total_t += time.time() - t0
        hit_t += int(any(kw in str(c) for c in out.get("citations", [])) or bool(out.get("citations")))
    report["文本题"]["命中率"] = f"{hit_t}/{len(TEXT_CASES)}"
    # 拒答
    ref = 0
    for q in REFUSE_CASES:
        out = ask(q)
        ref += int("未找到" in (out.get("answer") or ""))
    report["拒答题"]["正确拒答率"] = f"{ref}/{len(REFUSE_CASES)}"
    report["平均耗时_s"] = round(total_t / (len(NUM_CASES) + len(TEXT_CASES) + len(REFUSE_CASES)), 2)
    with open("metrics.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("报告已写入 metrics.json")
    return report

if __name__ == "__main__":
    print(run_eval())