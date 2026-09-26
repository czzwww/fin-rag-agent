import time
from app.tools import metrics_tools

REGISTRY = {
    "query_metrics": metrics_tools.query_metrics,
    "compute": metrics_tools.compute,
}
SCHEMA = {
    "query_metrics": [],
    "compute": ["operation", "values"],
}

def run_tool(name: str, args: dict, max_retry: int = 2):
    if name not in REGISTRY:
        return f"错误：未知工具 {name}"
    for required in SCHEMA.get(name, []):
        if required not in args:
            return f"参数错误：缺少 {required}"
    for attempt in range(1, max_retry + 1):
        try:
            return REGISTRY[name](**args)
        except Exception as e:
            if attempt == max_retry:
                return f"[失败] {name}: {e}"
            time.sleep(0.5 * attempt)