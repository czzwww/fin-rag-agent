import os, json, sqlite3, hashlib, datetime 
import numpy as np  
import faiss    # 用于向量数据库和索引

STORAGE = "storage"
DB_PATH = os.path.join(STORAGE, "metrics.db")
INDEX_PATH = os.path.join(STORAGE, "faiss.index")
IDMAP_PATH = os.path.join(STORAGE, "id_map.json")

def file_hash(path: str) -> str:
    """计算文件的 MD5 哈希值"""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def _conn():
    """创建数据库连接"""
    os.makedirs(STORAGE, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS documents(
        doc_id TEXT PRIMARY KEY, file_hash TEXT, company TEXT, year INTEGER,
        report_type TEXT, status TEXT, embed_model TEXT, ingest_version TEXT,
        ingested_at TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS chunks(
        chunk_id TEXT PRIMARY KEY, doc_id TEXT, page INTEGER, kind TEXT, text TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS metrics(
        doc_id TEXT, company TEXT, period TEXT, name TEXT, value REAL, unit TEXT,
        source_page INTEGER, PRIMARY KEY(doc_id, name))""")
    return conn

# ---- FAISS ----
def load_index(dim: int):
    """加载 FAISS 索引"""
    if os.path.exists(INDEX_PATH):
        return faiss.read_index(INDEX_PATH)
    return faiss.IndexIDMap(faiss.IndexFlatL2(dim))

def save_index(index):
    """保存 FAISS 索引"""
    os.makedirs(STORAGE, exist_ok=True)
    faiss.write_index(index, INDEX_PATH)

def save_id_map(id_map: dict):
    """保存 ID 映射"""
    with open(IDMAP_PATH, "w", encoding="utf-8") as f:
        json.dump(id_map, f, ensure_ascii=False)

def load_id_map() -> dict:
    """加载 ID 映射"""
    if os.path.exists(IDMAP_PATH):
        with open(IDMAP_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}

# ---- 查询 ----
def find_doc(doc_id: str):
    """根据文档 ID 查询文档信息"""
    conn = _conn()  # 创建数据库连接
    row = conn.execute("SELECT file_hash, embed_model, ingest_version FROM documents WHERE doc_id=?",
                       (doc_id,)).fetchone()
    conn.close()
    return row

def save_chunks(doc_id, chunks):
    """保存文档块"""
    conn = _conn()
    conn.executemany("INSERT OR REPLACE INTO chunks(chunk_id,doc_id,page,kind,text) VALUES(?,?,?,?,?)",
                     [(c["chunk_id"], doc_id, c["page"], c["kind"], c["text"]) for c in chunks])
    conn.commit(); conn.close()

def get_chunks(ids):
    """根据块 ID 查询文档块"""
    conn = _conn()
    qs = ",".join("?" * len(ids))
    rows = conn.execute(f"SELECT chunk_id,doc_id,page,kind,text FROM chunks WHERE chunk_id IN ({qs})", ids).fetchall()
    conn.close()
    return {r[0]: {"doc_id": r[1], "page": r[2], "kind": r[3], "text": r[4]} for r in rows}

def save_metrics(doc_id, company, period, metrics, source_page):
    """保存财务指标"""
    conn = _conn()
    conn.executemany(
        "INSERT OR REPLACE INTO metrics(doc_id,company,period,name,value,unit,source_page) VALUES(?,?,?,?,?,?,?)",
        [(doc_id, company, period, m["name"], m.get("value"), m.get("unit"), source_page) for m in metrics])
    conn.commit(); conn.close()

def query_metrics(company=None, period=None, names=None):
    """根据财务指标查询"""
    conn = _conn()
    sql, args = "SELECT company,period,name,value,unit,source_page FROM metrics WHERE 1=1", []
    if company: sql += " AND company=?"; args.append(company)
    if period:  sql += " AND period=?";  args.append(period)
    if names:   sql += f" AND name IN ({','.join('?'*len(names))})"; args += names
    rows = conn.execute(sql, args).fetchall()
    conn.close()
    return [dict(zip(["company", "period", "name", "value", "unit", "source_page"], r)) for r in rows]

def register_document(doc_id, fhash, company, year, embed_model, ingest_version):
    """注册文档"""
    conn = _conn()
    conn.execute("INSERT OR REPLACE INTO documents VALUES(?,?,?,?,?,?,?,?,?)",
                 (doc_id, fhash, company, year, "annual", "done", embed_model, ingest_version,
                  datetime.datetime.now().isoformat()))
    conn.commit(); conn.close()