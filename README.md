# 📚 知识库搜索系统

> 基于 TF-IDF 的轻量级内部知识库搜索引擎，支持本地 Markdown 文档 + 外部网页文档统一搜索。

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-v1.3-brightgreen.svg)](https://github.com/zyddst/knowledge_search)

---

## ✨ 特性

- 🔍 **关键词搜索** — TF-IDF 余弦相似度 + 关键词命中加权混合排序
- 🖥️ **CLI 工具** — 终端直接搜索：`python search.py "关键词"`
- 🌐 **Web 搜索页面** — 浏览器访问，输入框搜索，结果卡片展示
- 🔌 **RESTful API** — GET/POST `/search`，返回 JSON，支持跨域
- 🌍 **外部文档抓取** — 配置 URL 自动抓取网页 → 转为 Markdown → 纳入索引
- 💬 **企业微信预留** — `/wechat` 端点，待接入企业微信 Bot
- 🪟 **Windows 兼容** — GBK 编码终端下中文不乱码、不崩溃
- ⚡ **快速响应** — < 100 篇文档场景下搜索 < 200ms

## 🚀 快速开始

### 环境要求

- Python 3.8+
- 依赖见 `requirements.txt`

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

> ⚠️ **注意**：如果直接运行 `python server.py` 报错 `FileNotFoundError: vector_db\\chunks.pkl`，说明尚未构建索引，请先执行 `python index_docs.py`。

### 自定义端口

```bash
python server.py 9000    # 在 9000 端口启动
```

## 🌍 外部文档抓取

除了本地 `docs/` 下的 Markdown 文件，还可以抓取外部网页文档纳入搜索。

**1. 编辑 `config.py`，配置外部源：**

```python
EXTERNAL_SOURCES = [
    {
        "name": "Python 教程",
        "urls": [
            "https://docs.python.org/zh-cn/3/tutorial/introduction.html",
        ],
        "content_selector": "article",        # CSS 选择器，提取正文
        "exclude_selectors": [".sidebar"],    # 要排除的元素
    },
]
```

**2. 抓取并构建索引：**

```bash
python index_docs.py --fetch
```

**3. 搜索：** 跟本地文档完全一样，`python search.py "关键词"` 或 Web 页面搜索，结果同时包含本地文档和网页内容。

```bash
# 跳过抓取，只用缓存构建索引
python index_docs.py

# 重新抓取 + 索引
python index_docs.py --fetch
```

## 📂 项目结构

```
knowledge_search/
├── docs/                      # 📄 本地知识库文档
│   ├── 新人指南.md
│   └── API接口规范.md
├── fetched_docs/              # 🌍 外部文档缓存（fetcher.py 自动生成）
│   └── <source_name>/
├── specs/                     # 📋 项目规划文档
│   ├── 需求文档.md
│   └── 系统设计文档.md
├── vector_db/                 # 📊 索引文件（自动生成）
├── config.py                  # ⚙️  全局配置（含外部文档源）
├── fetcher.py                 # 🌍 网页抓取 + HTML→MD 转换
├── wechat.py                  # 💬 企业微信消息处理
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
# 搜索参数
CHUNK_SIZE = 500              # 文本块大小（字符数）
CHUNK_OVERLAP = 50            # 滑动窗口重叠量
TOP_K = 5                     # 搜索返回结果数

# 外部文档源
EXTERNAL_SOURCES = [
    {
        "name": "Python 教程",
        "urls": ["https://docs.python.org/zh-cn/3/tutorial/introduction.html"],
        "content_selector": "article",
        "exclude_selectors": [".sidebar"],
    },
]
```

修改配置后需重建索引：`python index_docs.py --fetch`

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
- [x] **v1.3** — 外部文档抓取 + 多源索引 + 企微加解密
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
2. 在 `config.py` 的 `EXTERNAL_SOURCES` 中配置外部文档 URL
3. 运行 `python index_docs.py --fetch` 重建索引
4. 如需修改搜索行为，编辑 `config.py` 调整参数

## 📄 License

MIT License

---

**维护者:** [zyddst](https://github.com/zyddst)
