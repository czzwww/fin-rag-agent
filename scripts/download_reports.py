"""从巨潮资讯网下载指定公司年报 PDF。
注意：接口可能调整，若失败用浏览器下载后放入 data/reports/ 亦可。"""
import os, time, requests

QUERY = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
SEARCH = "http://www.cninfo.com.cn/new/information/topSearch/query"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Referer": "http://www.cninfo.com.cn/new/commonUrl?url=disclosure/list/notice",
}

def resolve_org(code: str):
    """根据股票代码查 orgId（巨潮查询需要 code,orgId）"""
    r = requests.post(SEARCH, headers=HEADERS, data={"keyWord": code, "maxNum": 10}, timeout=15)
    for item in r.json():
        if item.get("code") == code:
            return item.get("orgId")
    return None


def list_annual_reports(code: str, start="2022-01-01", end="2024-12-31"):
    """根据股票代码查年报列表"""
    org = resolve_org(code)
    if not org:
        raise RuntimeError(f"未找到 {code} 的 orgId")
    data = {
        "pageNum": 1, "pageSize": 30, "column": "szse", "tabName": "fulltext",
        "stock": f"{code},{org}", "searchkey": "", "secid": "",
        "category": "category_ndbg_szsh", "trade": "", "seDate": f"{start}~{end}",
    }
    r = requests.post(QUERY, headers=HEADERS, data=data, timeout=20)
    return r.json().get("announcements") or []

def download(code: str, out_dir="data/reports"):
    os.makedirs(out_dir, exist_ok=True)
    for ann in list_annual_reports(code):
        title = ann["announcementTitle"]
        url = "http://static.cninfo.com.cn/" + ann["adjunctUrl"]
        name = f"{code}_{title}.pdf".replace("/", "_")
        path = os.path.join(out_dir, name)
        if os.path.exists(path):
            print("已存在，跳过", name); continue
        pdf = requests.get(url, headers=HEADERS, timeout=60).content
        with open(path, "wb") as f:
            f.write(pdf)
        print("已下载", name)
        time.sleep(1)   # 温和限速

if __name__ == "__main__":
    for c in ["600519", "000858"]:
        download(c)