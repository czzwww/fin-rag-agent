import json     # 解析JSON响应
from typing import TypedDict    # 定义状态类型
from langgraph.graph import StateGraph, END # 状态图
from openai import OpenAI # 调用OpenAI API
from app import config  # 导入配置  
from app.retriever import Retriever # 文档检索器
from app.rag import answer_with_rag # 文档检索器
from app.tools import registry # 工具注册器

_client = OpenAI(api_key=config.OPENAI_API_KEY, base_url=config.OPENAI_BASE_URL)
_retriever = Retriever()

class State(TypedDict):
    question: str
    route: str          # metrics | text | both
    metrics: list
    contexts: list
    answer: str
    citations: list
    verified: bool
    retries: int

def route_node(state):
    r = _client.chat.completions.create(
        model=config.CHAT_MODEL, response_format={"type": "json_object"},
        messages=[{"role": "user", "content":
            f"判断问题类型，只输出JSON {{\"route\":\"metrics|text|both\"}}。\n"
            f"数值型(问具体数字/计算)→metrics；文本型(问观点/描述)→text；两者都要→both。\n问题：{state['question']}"}],
        temperature=0)
    return {"route": json.loads(r.choices[0].message.content)["route"]}

def metrics_node(state):
    m = registry.run_tool("query_metrics", {})
    return {"metrics": m if isinstance(m, list) else []}

def text_node(state):
    contexts = _retriever.search(state["question"], k=5)
    return {"contexts": contexts}

def answer_node(state):
    ans, cites = answer_with_rag(state["question"], state.get("contexts", []), state.get("metrics", []))
    return {"answer": ans, "citations": cites}

def verify_node(state):
    """自检：有答案且(引用非空 或 数值非空) 视为通过"""
    ok = bool(state.get("answer")) and (bool(state.get("citations")) or bool(state.get("metrics")))
    return {"verified": ok, "retries": state.get("retries", 0) + 1}

def after_verify(state):
    if state["verified"] or state["retries"] >= 2:
        return "end"
    return "retry"

g = StateGraph(State)
g.add_node("route", route_node)
g.add_node("metrics", metrics_node)
g.add_node("text", text_node)
g.add_node("answer", answer_node)
g.add_node("verify", verify_node)
g.set_entry_point("route")
g.add_conditional_edges("route", lambda s: s["route"],
                        {"metrics": "metrics", "text": "text", "both": "text"})
g.add_edge("metrics", "answer")
g.add_edge("text", "answer")
g.add_edge("answer", "verify")
g.add_conditional_edges("verify", after_verify, {"retry": "text", "end": END})
fin_graph = g.compile()

def ask(question: str):
    return fin_graph.invoke({"question": question, "retries": 0})