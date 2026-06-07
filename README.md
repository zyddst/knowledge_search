# 📚 知识库搜索系统

> 基于 TF-IDF 的轻量级内部知识库搜索引擎，专为小团队（~20 人）设计，零外部依赖，Windows 开箱即用。

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-v1.2-brightgreen.svg)](https://github.com/zyddst/knowledge_search)

---

## ✨ 特性

- 🔍 **关键词搜索** — TF-IDF 余弦相似度 + 关键词命中加权混合排序
- 🖥️ **CLI 工具** — 终端直接搜索：`python search.py "关键词"`
- 🌐 **Web 搜索页面** — 浏览器访问，输入框搜索，结果卡片展示
- 🔌 **RESTful API** — GET/POST `/search`，返回 JSON，支持跨域
- 💬 **企业微信预留** — `/wechat` 端点，待接入企业微信 Bot
- 📦 **零外部依赖** — 仅需 Python 3.8+ 和 scikit-learn，不联网
- 🪟 **Windows 兼容** — GBK 编码终端下中文不乱码、不崩溃
- ⚡ **快速响应** — < 100 篇文档场景下搜索 < 200ms

## 🚀 快速开始

### 环境要求

- Python 3.8+
- scikit-learn >= 0.24

### 安装与运行

```bash
# 1. 克隆仓库
git clone https://github.com/zyddst/knowledge_search.git
cd knowledge_search

# 2. 安装依赖
pip install -r requirements.txt

# 3. 放入你的 Markdown 文档到 docs/ 目录
# （项目中已包含示例文档，可直接使用）

# 4. 构建索引
python index_docs.py

# 5. CLI 搜索
python search.py "报销流程"

# 6. 启动 Web 服务
python server.py
# 浏览器访问 http://localhost:8080
```

### 自定义端口

```bash
python server.py 9000    # 在 9000 端口启动
```

## 📂 项目结构

```
knowledge_search/
├── docs/                      # 📄 知识库文档（用户维护，被索引搜索）
│   ├── 新人指南.md
│   └── API接口规范.md
├── specs/                     # 📋 项目规划文档（不被索引）
│   ├── 需求文档.md
│   └── 系统设计文档.md
├── vector_db/                 # 📊 索引文件（自动生成，勿手动修改）
│   ├── chunks.pkl             # 文本块列表
│   ├── vectorizer.pkl         # TF-IDF 向量化器
│   ├── tfidf_matrix.pkl       # TF-IDF 稀疏矩阵
│   └── meta.txt               # 索引元信息
├── config.py                  # ⚙️  全局配置
├── index_docs.py              # 🔧 索引构建工具
├── search.py                  # 🔍 CLI 搜索工具
├── server.py                  # 🌐 Web 服务（API + 搜索页面）
├── requirements.txt           # 📋 Python 依赖
└── README.md                  # 📖 项目说明
```

## 🔌 API 接口

### 搜索 (GET)

```bash
curl "http://localhost:8080/search?q=报销流程"
```

响应：

```json
{
  "query": "报销流程",
  "results": [
    {
      "title": "新人指南",
      "source": "docs/新人指南.md",
      "snippet": "在 OA 系统 → 费用报销 → 新建报销单...",
      "score": 0.14
    }
  ]
}
```

### 搜索 (POST)

```bash
curl -X POST http://localhost:8080/search \
  -H "Content-Type: application/json" \
  -d '{"q": "开发环境搭建"}'
```

### 健康检查

```bash
curl http://localhost:8080/health
# → {"status": "ok"}
```

### 完整接口列表

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | Web 搜索页面 |
| GET | `/search?q=关键词` | 搜索 API (JSON) |
| POST | `/search` | 搜索 API (JSON body) |
| GET | `/health` | 健康检查 |
| POST | `/wechat` | 企业微信回调（预留） |
| GET | `/wechat?echostr=xxx` | 企业微信 URL 验证（预留） |

## ⚙️ 配置

编辑 `config.py` 调整参数：

```python
DOCS_DIR = "./docs"           # 文档目录路径
VECTOR_DB_DIR = "./vector_db" # 索引存储路径
CHUNK_SIZE = 500              # 文本块大小（字符数）
CHUNK_OVERLAP = 50            # 滑动窗口重叠量
TOP_K = 5                     # 搜索返回结果数
```

修改配置后需重建索引：`python index_docs.py`

## 🔬 搜索算法

```
score = TF-IDF 余弦相似度(query, chunk)
      + 关键词正文命中数 × 0.05
      + 关键词标题命中数 × 0.2
```

- **主信号**：TF-IDF 余弦相似度（char_wb 分析器，2-4 gram）
- **辅助信号**：关键词在正文和标题中的命中数加权
- **去重**：同一源文件只保留得分最高的结果

详细设计见 [系统设计文档](specs/系统设计文档.md)。

## 🗺️ 路线图

- [x] **v1.0** — CLI 搜索 + Web API + 企业微信端点
- [x] **v1.1** — Web 搜索页面
- [x] **v1.2** — Windows 编码兼容 + 完善文档
- [ ] **v2.0** — 向量嵌入语义搜索（ChromaDB / bge-large-zh）
- [ ] **v2.1** — 企业微信 Bot 接入
- [ ] **v3.0** — RAG 答案生成 + LLM 集成

## 📖 文档

- [需求文档](specs/需求文档.md)
- [系统设计文档](specs/系统设计文档.md)
- [API 接口规范](docs/API接口规范.md)
- [新人指南](docs/新人指南.md)

## 🤝 贡献指南

1. 将新的 Markdown 文档放入 `docs/` 目录
2. 运行 `python index_docs.py` 重建索引
3. 如需修改搜索行为，编辑 `config.py` 调整参数

## 📄 License

MIT License

---

**维护者:** [zyddst](https://github.com/zyddst)
