# -*- coding: utf-8 -*-
"""
项目全局配置
包含数据路径、爬虫参数、LLM参数、知识库参数等
"""
import os

# ==================== 基础路径 ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REVIEWS_DIR = os.path.join(BASE_DIR, "reviews_score")
LLM_RESULTS_DIR = os.path.join(BASE_DIR, "llm_results")
VECTOR_STORE_DIR = os.path.join(BASE_DIR, "vector_store")

# ==================== LLM API 配置 ====================
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"
OPENROUTER_OPENAI = "openai/gpt-oss-120b:free"
OPENROUTER_GOOGLE = "google/gemma-4-31b-it:free"
LLM_TEMPERATURE = 0.3
LLM_MAX_TOKENS = 1024
LLM_MAX_RETRIES = 2
LLM_REQUEST_INTERVAL = 0.5  # LLM请求间隔（秒）

# ==================== 爬虫配置 ====================
COOKIE_FILE = os.path.join(BASE_DIR, "cookies.txt")
CRAWL_PAGES = 6  # 默认爬取页数（每页20条）

# UA轮换池
USER_AGENT_POOL = [
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
	"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
	"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
	"Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:126.0) Gecko/20100101 Firefox/126.0",
	"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
]

# 请求延迟（秒）
CRAWL_MIN_DELAY = 3.0
CRAWL_MAX_DELAY = 7.0
LONG_PAUSE_EVERY = 8
LONG_PAUSE_PROB = 0.4
LONG_PAUSE_MIN = 15.0
LONG_PAUSE_MAX = 30.0

# 限流处理
COOLDOWN_BASE = 60
COOLDOWN_MAX = 300
CRAWL_MAX_RETRIES = 3
CRAWL_BACKOFF_FACTOR = 2

# 通用请求头
COMMON_HEADERS = {
	'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
	'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
	'Accept-Encoding': 'gzip, deflate, br',
	'Connection': 'keep-alive',
	'Upgrade-Insecure-Requests': '1',
	'Sec-Fetch-Dest': 'document',
	'Sec-Fetch-Mode': 'navigate',
	'Sec-Fetch-Site': 'none',
	'Sec-Fetch-User': '?1',
	'Cache-Control': 'max-age=0',
}

# ==================== 知识库配置 ====================
EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
RETRIEVAL_TOP_K = 5

# ==================== 分析配置 ====================
SENTIMENT_BATCH_SIZE = 10  # 每次批量分析的影评数
