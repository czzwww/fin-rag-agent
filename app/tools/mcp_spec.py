MCP_TOOLS = {
    "query_metrics": {
        "name": "query_metrics",
        "description": "查询归一化财务指标（营收/净利润/毛利率/ROE/负债率/经营现金流）",
        "inputSchema": {"type": "object", "properties": {
            "company": {"type": "string"}, "period": {"type": "string"},
            "names": {"type": "array", "items": {"type": "string"}}}, "required": []},
    },
    "compute": {
        "name": "compute",
        "description": "数值计算：yoy 同比 / cagr 复合增速 / ratio 比率",
        "inputSchema": {"type": "object", "properties": {
            "operation": {"type": "string", "enum": ["yoy", "cagr", "ratio"]},
            "values": {"type": "array", "items": {"type": "number"}}},
            "required": ["operation", "values"]},
    },
}