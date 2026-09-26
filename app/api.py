from fastapi import FastAPI
from pydantic import BaseModel
from app.agent import ask
from app import store

app = FastAPI(title="财报结构化问答 Agent")

class AskRequest(BaseModel):
    question: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/ask")
def ask_api(req: AskRequest):
    result = ask(req.question)
    return {"answer": result.get("answer"), "citations": result.get("citations", []),
            "metrics": result.get("metrics", [])}

@app.get("/metrics")
def metrics(company: str = None, period: str = None):
    return store.query_metrics(company, period)