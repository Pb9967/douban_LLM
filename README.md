# 豆瓣影评LLM分析系统

基于LLM技术的豆瓣影评分析系统，通过本地知识库实现智能电影推荐。

## 项目架构

```
douban_llm2/
├── apiget.py              # API管理工具（加载.env，提供API Key）
├── config.py              # 全局配置
├── douban_request.py      # 反反爬请求管理器（工具类）
├── douban_crawler.py      # 爬虫模块（输出txt到reviews_score/）
├── llm_analyzer.py        # LLM情感分析+摘要（输出JSON到llm_results/）
├── llm_knowledge_base.py  # 本地知识库构建与检索（FAISS向量库）
├── llm_recommender.py     # LLM电影推荐（RAG）
├── main.py                # 主入口
├── requirements.txt       # 依赖
├── .env                   # 环境变量（DEEPSEEK_API_KEY）
├── cookies.txt            # 豆瓣Cookie配置
├── reviews_score/         # 爬取的影评数据（txt格式）
├── llm_results/           # LLM分析结果（JSON格式）
└── vector_store/          # FAISS向量知识库
```

## 模块说明

| 模块 | 类型 | 说明 |
|------|------|------|
| `apiget.py` | 工具 | API管理，`SetAPIEnvironment()`加载.env |
| `config.py` | 工具 | 全局配置参数 |
| `douban_request.py` | 工具 | 反反爬HTTP请求管理器 |
| `douban_crawler.py` | 数据 | 爬取电影详情+影评，输出txt |
| `llm_analyzer.py` | 数据 | LLM情感分析+摘要生成，输出JSON |
| `llm_knowledge_base.py` | 数据 | 构建FAISS向量知识库 |
| `llm_recommender.py` | 数据 | RAG电影推荐交互系统 |
| `main.py` | 入口 | 统一工作流入口 |

### 模块解耦设计

- **工具模块**（apiget/config/douban_request）：可被其他模块import
- **数据模块**（crawler/analyzer/kb/recommender）：仅依赖数据文件，不互相import
- 每个数据模块都有 `if __name__ == "__main__"` 可独立测试

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

> 首次运行知识库构建时，会自动下载嵌入模型 `BAAI/bge-small-zh-v1.5`（约95MB）

### 2. 配置API Key

编辑 `.env` 文件：

```
DEEPSEEK_API_KEY=your_deepseek_api_key
```

获取API Key：https://platform.deepseek.com/api_keys

### 3. 配置Cookie（爬虫功能需要）

编辑 `cookies.txt`，填入豆瓣Cookie。参考文件内说明。

### 4. 运行

**交互模式：**

```bash
python main.py
```

**命令行模式：**

```bash
# 单独运行各模块
python douban_crawler.py          # 爬取数据
python llm_analyzer.py            # LLM分析
python llm_knowledge_base.py      # 构建知识库
python llm_recommender.py         # 推荐系统

# 通过main.py指定步骤
python main.py crawl              # 爬取
python main.py analyze            # 分析
python main.py build-kb           # 构建知识库
python main.py recommend          # 推荐
python main.py full               # 完整流程
```

## 数据格式

### 影评txt格式（reviews_score/）

```
电影名称: 我们的父辈 Unsere Mütter, unsere Väter
电影ID: 22623816
导演: 菲利普·卡德尔巴赫
类型: 剧情, 动作, 历史, 战争
上映时间: 2013-03-17(德国)
国家/地区: 德国
主演: 沃尔克·布鲁赫, 汤姆·希林

影评:

review_1:评分：5 内容：几乎完美的电影...
review_2:评分：4 内容：对普通人来说，战争无胜者...
```

### LLM分析结果（llm_results/）

JSON格式，包含：
- 电影元信息
- 平均评分、影评数量
- 情感分布（正面/负面/中性）
- LLM生成的总结摘要
- 正面/负面代表性影评
- 每条影评的情感标签和理由

## 推荐流程

```
用户输入喜好 → FAISS语义检索 → 召回相关电影 → LLM生成推荐理由
```

示例交互：

```
您的喜好: 我喜欢战争题材的深度电影

🔍 正在搜索与"战争题材的深度电影"相关的电影...
🤖 正在生成推荐...

🎬 推荐1：《我们的父辈 Unsere Mütter, unsere Väter》
📌 推荐理由：因为您喜欢战争题材的深度电影，而本片是罕见的德国视角二战反思作品...
✨ 核心看点：五线叙事展现战争对人性的摧毁
```

## 已有数据使用

如果您已有 `reviews_score/` 目录下的影评txt文件，可以直接从步骤2（LLM分析）开始，无需重新爬取。
