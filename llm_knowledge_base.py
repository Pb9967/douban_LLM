# -*- coding: utf-8 -*-
"""
本地知识库构建与检索模块
读取 reviews_score/ 下的txt文件（和 llm_results/ 下的JSON分析结果），
使用LangChain + FAISS构建本地向量知识库，提供语义检索能力。

两种模式：
  1. 有LLM分析结果时：使用分析摘要+情感分布+代表性影评构建文档
  2. 无分析结果时：使用原始txt元信息+影评构建文档

依赖：apiget.py, defines.py（工具模块）
不依赖其他数据模块，仅读取数据文件。
"""
import os
import re
import json
import apiget
from defines import (
	REVIEWS_DIR, LLM_RESULTS_DIR, VECTOR_STORE_DIR,
	EMBEDDING_MODEL, RETRIEVAL_TOP_K,
)


# ==================== 数据加载 ====================

def parse_movie_txt(file_path):
	"""解析单个电影的txt文件"""
	with open(file_path, 'r', encoding='utf-8') as f:
		content = f.read()

	movie_info = {}
	reviews = []

	for key in ["电影名称", "电影ID", "导演", "类型", "上映时间", "国家/地区", "主演"]:
		pattern = rf'^{re.escape(key)}:\s*(.+)$'
		match = re.search(pattern, content, re.MULTILINE)
		if match:
			movie_info[key] = match.group(1).strip()

	review_pattern = r'review_\d+:(?:评分：(\d+)\s+)?内容：(.+)'
	for match in re.finditer(review_pattern, content):
		score = int(match.group(1)) if match.group(1) else None
		text = match.group(2).strip()
		reviews.append({"text": text, "score": score})

	return movie_info, reviews


def load_llm_result(movie_name):
	"""尝试加载对应电影的LLM分析结果"""
	safe_name = movie_name.replace('/', '／').replace('\\', '＼')
	json_path = os.path.join(LLM_RESULTS_DIR, f'{safe_name}.json')
	if os.path.exists(json_path):
		with open(json_path, 'r', encoding='utf-8') as f:
			return json.load(f)
	return None


def load_all_movies(data_dir=None):
	"""加载所有电影数据，返回列表"""
	if data_dir is None:
		data_dir = REVIEWS_DIR

	movies = []
	if not os.path.exists(data_dir):
		print(f"数据目录不存在: {data_dir}")
		return movies

	txt_files = sorted(f for f in os.listdir(data_dir) if f.endswith('.txt'))
	print(f"发现 {len(txt_files)} 个电影数据文件")

	for txt_file in txt_files:
		file_path = os.path.join(data_dir, txt_file)
		movie_info, reviews = parse_movie_txt(file_path)
		movie_name = movie_info.get("电影名称", txt_file.replace('.txt', ''))

		# 尝试加载LLM分析结果
		llm_result = load_llm_result(movie_name)

		movies.append({
			"info": movie_info,
			"reviews": reviews,
			"llm_result": llm_result,
			"source_file": txt_file,
		})

	return movies


# ==================== 文档构建 ====================

def create_documents(movies):
	"""将电影数据构建为LangChain Document列表"""
	from langchain_core.documents import Document

	documents = []
	for movie in movies:
		info = movie["info"]
		reviews = movie["reviews"]
		llm_result = movie["llm_result"]
		movie_name = info.get("电影名称", "未知")

		if llm_result:
			# 有LLM分析结果：使用丰富的结构化信息
			sentiment_dist = llm_result.get("sentiment_distribution", {})
			summary = llm_result.get("summary", "")
			avg_score = llm_result.get("avg_score", 0)
			pos_samples = llm_result.get("positive_samples", [])
			neg_samples = llm_result.get("negative_samples", [])

			content_parts = [
				f"电影《{movie_name}》",
				f"导演: {info.get('导演', '未知')}",
				f"类型: {info.get('类型', '未知')}",
				f"国家/地区: {info.get('国家/地区', '未知')}",
				f"上映时间: {info.get('上映时间', '未知')}",
				f"主演: {info.get('主演', '未知')}",
				f"平均评分: {avg_score}/5",
				f"影评数: {llm_result.get('review_count', len(reviews))}",
				f"情感分布: 正面{sentiment_dist.get('正面', 0)}条, "
				f"负面{sentiment_dist.get('负面', 0)}条, "
				f"中性{sentiment_dist.get('中性', 0)}条",
			]
			if summary:
				content_parts.append(f"影评摘要: {summary}")
			if pos_samples:
				content_parts.append("正面评价示例: " + " | ".join(pos_samples[:3]))
			if neg_samples:
				content_parts.append("负面评价示例: " + " | ".join(neg_samples[:3]))

			page_content = "\n".join(content_parts)
			metadata = {
				"movie_name": movie_name,
				"director": info.get('导演', '未知'),
				"genre": info.get('类型', '未知'),
				"country": info.get('国家/地区', '未知'),
				"avg_score": avg_score,
				"source_file": movie["source_file"],
			}
		else:
			# 无LLM分析结果：使用原始txt信息
			scores = [r["score"] for r in reviews if r.get("score") is not None]
			avg_score = sum(scores) / len(scores) if scores else 0

			content_parts = [
				f"电影《{movie_name}》",
				f"导演: {info.get('导演', '未知')}",
				f"类型: {info.get('类型', '未知')}",
				f"国家/地区: {info.get('国家/地区', '未知')}",
				f"上映时间: {info.get('上映时间', '未知')}",
				f"主演: {info.get('主演', '未知')}",
				f"平均评分: {round(avg_score, 2)}/5",
				f"影评数: {len(reviews)}",
				"部分影评: " + " | ".join(r["text"][:80] for r in reviews[:10]),
			]

			page_content = "\n".join(content_parts)
			metadata = {
				"movie_name": movie_name,
				"director": info.get('导演', '未知'),
				"genre": info.get('类型', '未知'),
				"country": info.get('国家/地区', '未知'),
				"avg_score": round(avg_score, 2),
				"source_file": movie["source_file"],
			}

		doc = Document(page_content=page_content, metadata=metadata)
		documents.append(doc)

	return documents


# ==================== 向量库构建 ====================

def build_vector_store(documents, save_path=None):
	"""构建FAISS向量库并保存到本地"""
	from langchain_community.vectorstores import FAISS
	from langchain_huggingface import HuggingFaceEmbeddings

	if save_path is None:
		save_path = VECTOR_STORE_DIR

	if not documents:
		print("无文档数据，无法构建知识库")
		return None

	print(f"正在加载嵌入模型: {EMBEDDING_MODEL}")
	print("首次运行需下载模型，请耐心等待...")
	embeddings = HuggingFaceEmbeddings(
		model_name=EMBEDDING_MODEL,
		model_kwargs={"device": "cpu"},
		encode_kwargs={"normalize_embeddings": True},
	)

	print(f"正在构建向量索引，共 {len(documents)} 个文档...")
	vector_store = FAISS.from_documents(documents, embeddings)

	# 保存到本地
	if not os.path.exists(save_path):
		os.makedirs(save_path)
	vector_store.save_local(save_path)
	print(f"向量知识库已保存至: {save_path}")

	return vector_store


def load_vector_store(load_path=None):
	"""加载本地FAISS向量库"""
	from langchain_community.vectorstores import FAISS
	from langchain_huggingface import HuggingFaceEmbeddings

	if load_path is None:
		load_path = VECTOR_STORE_DIR

	if not os.path.exists(load_path):
		print(f"向量库不存在: {load_path}")
		print("请先运行 llm_knowledge_base.py 构建知识库")
		return None

	embeddings = HuggingFaceEmbeddings(
		model_name=EMBEDDING_MODEL,
		model_kwargs={"device": "cpu"},
		encode_kwargs={"normalize_embeddings": True},
	)

	vector_store = FAISS.load_local(
		load_path, embeddings,
		allow_dangerous_deserialization=True
	)
	print(f"已加载向量知识库: {load_path}")
	return vector_store


def search(query, vector_store, top_k=None):
	"""在知识库中搜索相关电影"""
	if top_k is None:
		top_k = RETRIEVAL_TOP_K

	results = vector_store.similarity_search_with_score(query, k=top_k)
	return results


# ==================== 主流程 ====================

def run(data_dir=None, save_path=None):
	"""主流程：构建本地知识库"""
	apiget.GetAPIMgr().SetAPIEnvironment()

	# 加载数据
	movies = load_all_movies(data_dir)
	if not movies:
		print("未找到电影数据，请先运行 douban_crawler.py 爬取数据")
		return

	# 构建文档
	documents = create_documents(movies)
	print(f"已构建 {len(documents)} 个电影文档")

	# 构建向量库
	vector_store = build_vector_store(documents, save_path)
	if vector_store:
		# 测试检索
		print("\n测试检索...")
		test_queries = ["战争片", "爱情电影", "科幻"]
		for q in test_queries:
			results = search(q, vector_store, top_k=3)
			print(f'\n查询: "{q}"')
			for doc, score in results:
				print(f'  [{score:.4f}] {doc.metadata["movie_name"]} - {doc.metadata.get("genre", "")}')


if __name__ == "__main__":
	# 测试：构建知识库
	import sys
	if len(sys.argv) > 1:
		data_dir = sys.argv[1]
	else:
		data_dir = None
	run(data_dir=data_dir)
