import pdfplumber  # 用于解析 PDF 表格
import os, glob, re
from app import store
from app.embedding import get_embedder
from app.extract import extract_metrics

def _table_to_markdown(table) -> str: 
    """将表格转换为 Markdown 格式"""
    rows = [[(c or "").replace("\n", " ").strip() for c in row] for row in table]
    if not rows:
        return ""
    header, body = rows[0], rows[1:]
    md = "| " + " | ".join(header) + " |\n"
    md += "| " + " | ".join(["---"] * len(header)) + " |\n"
    for r in body:
        md += "| " + " | ".join(r) + " |\n"
    return md

def parse_pdf(path: str):
    """返回 [(page_no, kind, text)]，kind ∈ {text, table}"""
    blocks = []
    with pdfplumber.open(path) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                blocks.append((page_no, "text", text))
            for t_idx, table in enumerate(page.extract_tables() or [], start=1):
                md = _table_to_markdown(table)
                if md.strip():
                    blocks.append((page_no, f"table{t_idx}", md))
    return blocks

INGEST_VERSION = "v1"   # 切分/schema 变更时递增

def _split(text, size=300, overlap=50):
    out, start = [], 0
    while start < len(text):
        end = start + size
        out.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
    return out

def ingest_file(path, embedder, index):
    doc_id = os.path.basename(path)
    fhash = store.file_hash(path)
    row = store.find_doc(doc_id)
    if row and row[0] == fhash and row[1] == embedder.model_name and row[2] == INGEST_VERSION:
        print("跳过（已入库且版本一致）", doc_id)
        return index
    blocks = parse_pdf(path)          # 来自 Step 2
    chunks, faiss_ids, vectors = [], [], []
    id_map = store.load_id_map()
    next_id = max([int(k) for k in id_map] or [0]) + 1
    for page, kind, text in blocks:
        for i, piece in enumerate(_split(text)):
            cid = f"{doc_id}:{page}:{kind}:{i}"
            chunks.append({"chunk_id": cid, "page": page, "kind": kind, "text": piece})
            vectors.append(piece)
            faiss_ids.append(next_id)
            id_map[str(next_id)] = cid
            next_id += 1
    vecs = embedder.embed(vectors)
    import numpy as np
    index.add_with_ids(np.array(vecs, dtype="float32"), np.array(faiss_ids, dtype="int64"))
    store.save_chunks(doc_id, chunks)
    store.save_id_map(id_map)
    store.save_index(index)
    # 结构化抽取
    company = "贵州茅台" if doc_id.startswith("600519") else "五粮液"
    m = re.search(r"(20\d{2})", doc_id)
    year = int(m.group(1)) if m else 2024
    data = extract_metrics(blocks, company, year)
    store.save_metrics(doc_id, company, f"{year}年报", data.get("metrics", []), source_page=0)
    store.register_document(doc_id, fhash, company, year, embedder.model_name, INGEST_VERSION)
    print("已入库", doc_id, f"chunks={len(chunks)}")
    return index

def ingest_all(report_dir="data/reports", rebuild=False):
    embedder = get_embedder()
    if rebuild:
        for f in ["storage/faiss.index", "storage/id_map.json", "storage/metrics.db"]:
            if os.path.exists(f):
                os.remove(f)
    index = store.load_index(embedder.dim)
    for path in sorted(glob.glob(os.path.join(report_dir, "*.pdf"))):
        index = ingest_file(path, embedder, index)
    return index

if __name__ == "__main__":
    import sys
    ingest_all(rebuild="--rebuild" in sys.argv)