"""知识库配置"""

# 文档目录 — 把你的 Markdown 文件放在这里（支持子目录递归）
DOCS_DIR = "./docs"

# 向量数据库目录
VECTOR_DB_DIR = "./vector_db"

# 文档分块大小（字符数）
CHUNK_SIZE = 500

# 分块重叠
CHUNK_OVERLAP = 50

# 搜索结果返回条数
TOP_K = 5

# ────────────────────────────────────────────
# 企业微信配置
# 获取方式见 specs/系统设计文档.md 企业微信接入章节
# ────────────────────────────────────────────

# 企业 ID（管理后台 → 我的企业 → 企业 ID）
WECHAT_CORP_ID = "ww69af32d4be9ee42d"

# 回调 Token（应用 → 接收消息 → 自行填写，两边保持一致）
WECHAT_TOKEN = "knowledgesearch2024"

# 回调 EncodingAESKey（应用 → 接收消息 → 随机生成）
# 明文模式留空，加密模式填写
WECHAT_ENCODING_AES_KEY = "KVm76P1lI3VR7FkyvONbjB29VmhrKGbqLIXnIfJ3Vlj"

# ────────────────────────────────────────────
# 外部文档源配置
# ────────────────────────────────────────────

# 外部抓取文档的本地缓存目录
FETCHED_DOCS_DIR = "./fetched_docs"

# 外部文档源列表
# name:             来源名称，作为子目录名
# urls:             要抓取的页面 URL 列表
# content_selector: CSS 选择器，提取页面正文区域（可选，不填则自动提取 <body>）
# exclude_selectors: 要排除的 CSS 选择器列表（导航、侧栏等）
EXTERNAL_SOURCES = [
    {
        "name": "Python 教程",
        "urls": [
            "https://docs.python.org/zh-cn/3/tutorial/introduction.html",
        ],
        "content_selector": "article",
        "exclude_selectors": [".sidebar", ".headerlink", ".sphinxsidebar"],
    },
]
