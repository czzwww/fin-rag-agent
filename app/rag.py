from openai import OpenAI
from app import config

_client = OpenAI(api_key=config.OPENAI_API_KEY, base_url=config.OPENAI_BASE_URL)

SYSTEM = """你是财报分析助手。只依据给定资料与指标回答，禁止编造。
资料不足时回答"知识库中未找到相关信息"。
回答中引用资料时标注来源，格式 [来源:文件名 P页码]。"""

def answer_with_rag(question, contexts, metrics, threshold=1.5):
    # 阈值拒答：无资料且无指标
    if not contexts and not metrics:
        return "知识库中未找到相关信息。", []
    ctx_text, cites = [], []
    for cid in contexts:
        from app import store
        c = store.get_chunks([cid]).get(cid)
        if not c:
            continue
        ctx_text.append(f"[{c['doc_id']} P{c['page']}] {c['text']}")
        cites.append({"doc_id": c["doc_id"], "page": c["page"]})
    metric_text = "\n".join(f"{m['company']} {m['period']} {m['name']}={m['value']}{m['unit']}"
                            for m in metrics)
    prompt = f"""资料：
{chr(10).join(ctx_text)}

结构化指标：
{metric_text}

问题：{question}"""
    r = _client.chat.completions.create(
        model=config.CHAT_MODEL,
        messages=[{"role": "system", "content": SYSTEM},
                  {"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return r.choices[0].message.content, cites