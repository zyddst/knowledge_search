"""
知识库搜索 API
启动: python server.py [端口]
默认: http://localhost:8080

接口:
  GET  /search?q=关键词 → JSON
  POST /search  {"q": "关键词"} → JSON
  GET  /health → 健康检查

接入企业微信:
  POST /wechat  {"keyword": "..."} → {"reply": "..."}
"""

import sys
import re
import pickle
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json

from sklearn.metrics.pairwise import cosine_similarity
from config import VECTOR_DB_DIR, TOP_K


def load_index():
    db_dir = Path(VECTOR_DB_DIR)
    with open(db_dir / "chunks.pkl", "rb") as f:
        chunks = pickle.load(f)
    with open(db_dir / "vectorizer.pkl", "rb") as f:
        vectorizer = pickle.load(f)
    with open(db_dir / "tfidf_matrix.pkl", "rb") as f:
        tfidf_matrix = pickle.load(f)
    return chunks, vectorizer, tfidf_matrix


chunks, vectorizer, tfidf_matrix = load_index()


def do_search(query: str, top_k: int = TOP_K) -> list[dict]:
    query_vec = vectorizer.transform([query])
    tfidf_scores = cosine_similarity(query_vec, tfidf_matrix).flatten()

    keywords = set(re.findall(r"[一-鿿]+|\w+", query.lower()))
    combined = []
    for i, chunk in enumerate(chunks):
        content_lower = chunk["content"].lower()
        title_lower = chunk["title"].lower()
        hits = sum(1 for kw in keywords if kw in content_lower)
        title_hits = sum(1 for kw in keywords if kw in title_lower)
        score = tfidf_scores[i] + hits * 0.05 + title_hits * 0.2
        combined.append((score, chunk))

    combined.sort(key=lambda x: x[0], reverse=True)

    seen = set()
    results = []
    for score, chunk in combined:
        src = chunk["source"]
        if src not in seen:
            seen.add(src)
            results.append({
                "title": chunk["title"],
                "source": chunk["source"],
                "snippet": chunk["content"][:200],
                "score": round(float(score), 3),
            })
        if len(results) >= top_k:
            break
    return results


HOME_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>知识库搜索</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f5f5f5;min-height:100vh}
.header{background:#1890ff;padding:24px;text-align:center;color:#fff}
.header h1{font-size:24px;margin-bottom:8px;font-weight:500}
.header p{font-size:13px;opacity:.8}
.search-box{max-width:680px;margin:-20px auto 0;padding:0 20px}
.search-box form{display:flex;gap:8px;background:#fff;padding:8px;border-radius:8px;box-shadow:0 2px 12px rgba(0,0,0,.08)}
.search-box input{flex:1;border:none;outline:none;font-size:15px;padding:10px 12px;border-radius:6px;background:#fafafa}
.search-box input:focus{background:#f0f0f0}
.search-box button{border:none;background:#1890ff;color:#fff;padding:10px 28px;border-radius:6px;font-size:15px;cursor:pointer}
.search-box button:hover{background:#40a9ff}
.results{max-width:720px;margin:24px auto;padding:0 20px}
.result-item{background:#fff;padding:20px 24px;margin-bottom:12px;border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,.04);transition:box-shadow .2s}
.result-item:hover{box-shadow:0 2px 12px rgba(0,0,0,.1)}
.result-item .title{font-size:17px;font-weight:600;color:#1890ff;margin-bottom:6px}
.result-item .source{font-size:12px;color:#999;margin-bottom:8px}
.result-item .snippet{font-size:14px;color:#555;line-height:1.7;white-space:pre-wrap;word-break:break-all}
.result-item .score{display:inline-block;margin-top:8px;font-size:12px;color:#bbb;background:#fafafa;padding:2px 10px;border-radius:10px}
.empty{text-align:center;color:#999;padding:40px;font-size:15px}
.hint{text-align:center;color:#bbb;font-size:14px;padding:28px}
</style>
</head>
<body>
<div class="header">
  <h1>📚 知识库搜索</h1>
  <p>输入关键词，快速检索团队文档</p>
</div>
<div class="search-box">
  <form onsubmit="search(event)">
    <input id="q" type="text" placeholder="输入搜索关键词..." value="" autofocus>
    <button type="submit">搜索</button>
  </form>
</div>
<div id="results" class="results"><div class="hint">🔍 在上方输入关键词开始搜索</div></div>
<script>
async function search(e){
  e.preventDefault();
  const q = document.getElementById('q').value.trim();
  if(!q) return;
  const box = document.getElementById('results');
  box.innerHTML = '<div class="hint">搜索中...</div>';
  try {
    const resp = await fetch('/search?q=' + encodeURIComponent(q));
    const data = await resp.json();
    if(!data.results || data.results.length === 0){
      box.innerHTML = '<div class="empty">😕 未找到与「'+q+'」相关的文档</div>';
      return;
    }
    box.innerHTML = data.results.map((r,i) =>
      '<div class="result-item">'+
        '<div class="title">#'+(i+1)+' '+r.title+'</div>'+
        '<div class="source">📄 '+r.source+'</div>'+
        '<div class="snippet">'+r.snippet+'</div>'+
        '<span class="score">相关度: '+r.score+'</span>'+
      '</div>'
    ).join('');
  }catch(err){
    box.innerHTML = '<div class="empty">❌ 搜索出错: '+err.message+'</div>';
  }
}
</script>
</body>
</html>"""


class APIHandler(BaseHTTPRequestHandler):
    def _html(self, content: str, status: int = 200):
        body = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data: dict, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._json({})

    def do_GET(self):
        p = urlparse(self.path)
        if p.path == "/" or p.path == "/index.html":
            self._html(HOME_PAGE)
        elif p.path == "/search":
            q = parse_qs(p.query).get("q", [""])[0].strip()
            if not q:
                return self._json({"error": "缺少 q 参数"}, 400)
            self._json({"query": q, "results": do_search(q)})
        elif p.path == "/health":
            self._json({"status": "ok"})
        elif p.path == "/wechat":
            echostr = parse_qs(p.query).get("echostr", [""])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(echostr.encode())
        else:
            self._json({"error": "Not found"}, 404)

    def do_POST(self):
        p = urlparse(self.path)
        if p.path in ("/search", "/wechat"):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                return self._json({"error": "请求体不是合法 JSON"}, 400)

            q = data.get("q", data.get("keyword", "")).strip()
            if not q:
                return self._json({"error": "缺少 q 参数"}, 400)

            results = do_search(q)
            if p.path == "/wechat":
                if not results:
                    return self._json({"reply": f"未找到与「{q}」相关的文档"})
                lines = [f"【{r['title']}】{r['source']}" for r in results[:3]]
                return self._json({"reply": "找到相关文档:\n" + "\n".join(lines)})
            self._json({"query": q, "results": results})
        else:
            self._json({"error": "Not found"}, 404)

    def log_message(self, format, *args):
        try:
            print(f"[{self.log_date_time_string()}] {args[0]}")
        except UnicodeEncodeError:
            print(f"[{self.log_date_time_string()}] <request>")


def main():
    # 兼容 Windows 终端编码
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080

    banner = [
        "",
        "  ================================",
        "   知识库搜索服务已启动",
        f"   打开浏览器访问: http://localhost:{port}",
        "",
        f"   健康检查: http://localhost:{port}/health",
        f"   API搜索:  http://localhost:{port}/search?q=关键词",
        "  ================================",
        "",
        "  按 Ctrl+C 停止服务",
        "",
    ]
    for line in banner:
        print(line, flush=True)

    HTTPServer(("0.0.0.0", port), APIHandler).serve_forever()


if __name__ == "__main__":
    main()
