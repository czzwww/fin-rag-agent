import json 
from openai import OpenAI
from app import config

_client = OpenAI(api_key=config.OPENAI_API_KEY, base_url=config.OPENAI_BASE_URL)

SYSTEM = """你是财务数据抽取助手。只从给定文本/表格中抽取数值，禁止编造。
无法确定的字段填 null。单位统一为「元」或「%」并在 unit 中标注。
输出 JSON：
{"period":"YYYY年报","metrics":[
  {"name":"revenue","value":174100000000,"unit":"元"},
  {"name":"net_profit","value":86200000000,"unit":"元"},
  {"name":"gross_margin","value":91.5,"unit":"%"},
  {"name":"roe","value":34.5,"unit":"%"},
  {"name":"debt_ratio","value":18.2,"unit":"%"},
  {"name":"operating_cashflow","value":123000000000,"unit":"元"}
]}"""

def extract_metrics(blocks, company: str, year: int, max_pages: int = 8) -> dict:
    """blocks: [(page_no, kind, text)]；挑选含关键词的块定向抽取"""
    keys = ["营业收入", "归属于上市公司股东的净利润", "毛利率", "加权平均净资产收益率", "资产负债率"]
    picked = [b for b in blocks if any(k in b[2] for k in keys)][:max_pages]
    material = "\n\n".join(f"[P{p} {k}]\n{t}" for p, k, t in picked)
    r = _client.chat.completions.create(
        model=config.CHAT_MODEL,
        response_format={"type": "json_object"},
        messages=[{"role": "system", "content": SYSTEM},
                  {"role": "user", "content": f"公司：{company}，年份：{year}\n\n{material}"}],
        temperature=0.1,
    )
    out = json.loads(r.choices[0].message.content)
    out["company"], out["year"] = company, year
    return out