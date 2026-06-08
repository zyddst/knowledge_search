# 📚 知识库搜索系统

> 基于 TF-IDF + BM25 混合排序的轻量级知识库搜索引擎，支持本地 + 外部网页文档统一搜索，多层过滤防误报。

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-v1.4-brightgreen.svg)](https://github.com/zyddst/knowledge_search)

---

## ✨ 特性

- 🔍 **混合搜索** — TF-IDF + BM25 → RRF 融合排序，多层相关度过滤
- 🖥️ **CLI 工具** — `python search.py "关键词"`
- 🌐 **Web 搜索页面** — 浏览器搜索输入框 + 结果卡片
- 🔌 **RESTful API** — GET/POST `/search`，JSON + CORS
- 🌍 **外部文档抓取** — 配置 URL → 自动抓取网页 → 纳入索引
- 💬 **企业微信预留** — `/wechat` 端点（AES 加解密已就绪）
- 🎯 **智能过滤** — 自动拒绝无意义查询，相关度 0~1 直观展示
- ⚡ **快速响应** — < 200ms

## 🚀 快速开始

### 环境要求

- Python 3.8+
- 依赖见 `requirements.txt`

### 安装与运行

```bash
git clone https://github.com/zyddst/knowledge_search.git
cd knowledge_search
pip install -r requirements.txt

# 构建索引（含外部文档抓取）
python index_docs.py --fetch

# CLI 搜索
python search.py "报销流程"

# Web 服务
python server.py
# 浏览器访问 http://localhost:8080
```

> ⚠️ 如果 `python server.py` 报 `FileNotFoundError: vector_db\\chunks.pkl`，先执行 `python index_docs.py`。

## 🌍 外部文档抓取

编辑 `config.py` 的 `EXTERNAL_SOURCES`：

```python
EXTERNAL_SOURCES = [
    {
        "name": "Python 教程",
        "urls": ["https://docs.python.org/zh-cn/3/tutorial/introduction.html"],
        "content_selector": "article",
        "exclude_selectors": [".sidebar"],
    },
]
```

```bash
python index_docs.py --fetch    # 抓取 + 索引
python index_docs.py            # 跳过抓取，只用缓存
```

## 📂 项目结构

```
knowledge_search/
├── docs/                      # 本地知识库文档
├── fetched_docs/              # 外部文档缓存
├── specs/                     # 项目规划文档
├── vector_db/                 # 索引文件（TF-IDF + BM25）
│   ├── chunks.pkl             # 文本块
│   ├── vectorizer.pkl         # TF-IDF 向量化器
│   ├── tfidf_matrix.pkl       # TF-IDF 矩阵
│   └── bm25.pkl               # BM25 倒排索引
├── config.py                  # 全局配置（含搜索参数、阈值）
├── fetcher.py                 # 网页抓取 + HTML→MD
├── search.py                  # 混合搜索引擎（TF-IDF + BM25 + RRF）
├── index_docs.py              # 索引构建
├── server.py                  # Web 服务
├── wechat.py                  # 企业微信加解密
└── requirements.txt
```

## 🔌 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | Web 搜索页面 |
| GET | `/search?q=关键词` | 搜索 (JSON) |
| POST | `/search` | 搜索 (JSON body) |
| GET | `/health` | 健康检查 |

```bash
curl "http://localhost:8080/search?q=报销流程"
# → {"query":"报销流程", "results":[{"title":"新人指南","score":1.0,...}]}
```

## 🔬 搜索算法

```
TF-IDF(char_wb) 余弦相似度  →  rank_tfidf     ┐
                                                ├──→ RRF 融合 → 多层过滤 → Top-K
BM25 关键词匹配              →  rank_bm25     ┘

RRF: 1/(60 + rank_tfidf) + 1/(60 + rank_bm25)  → 归一化到 0~1
```

**多层过滤：** TF-IDF 阈值 → BM25 零检查 → 零分末位惩罚 → 相关度阈值

## ⚙️ 配置

```python
# 搜索参数
CHUNK_SIZE = 500       # 文本块大小
TOP_K = 5              # 返回结果数

# BM25 参数
BM25_K1 = 1.5          # 词频饱和
BM25_B = 0.75          # 长度归一化

# 相关度阈值
MIN_RELEVANCE = 0.80   # RRF 归一化最低分
MIN_TFIDF = 0.05       # TF-IDF 绝对底线
```

## 🗺️ 路线图

- [x] **v1.0** — CLI + Web API
- [x] **v1.1** — Web 搜索页面
- [x] **v1.2** — Windows 编码兼容
- [x] **v1.3** — 外部文档抓取 + 企微加解密
- [x] **v1.4** — 混合搜索（TF-IDF + BM25 + RRF）
- [ ] **v2.0** — 向量嵌入语义搜索
- [ ] **v3.0** — RAG 答案生成

## 📖 文档

- [需求文档](specs/需求文档.md)
- [系统设计文档](specs/系统设计文档.md)
- [API 接口规范](docs/API接口规范.md)
- [新人指南](docs/新人指南.md)

## 📄 License

MIT License

---

**维护者:** [zyddst](https://github.com/zyddst)
