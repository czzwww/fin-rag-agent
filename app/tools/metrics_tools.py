from app import store

def query_metrics(company=None, period=None, names=None):
    """查询归一化财务指标"""
    return store.query_metrics(company, period, names)

def compute(operation: str, values: list, **kwargs):
    """数值计算：yoy(同比)/cagr(复合增速)/ratio(比率)"""
    import pandas as pd
    s = pd.Series(values, dtype="float64")
    if operation == "yoy":
        return float((s.iloc[-1] - s.iloc[-2]) / s.iloc[-2])
    if operation == "cagr":
        n = len(s) - 1
        return float((s.iloc[-1] / s.iloc[0]) ** (1 / n) - 1)
    if operation == "ratio":
        return float(s.iloc[0] / s.iloc[1])
    raise ValueError(f"未知运算 {operation}")