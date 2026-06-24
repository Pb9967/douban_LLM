# -*- coding: utf-8 -*-
"""
LLM电影推荐模块
基于本地向量知识库，通过RAG（检索增强生成）实现：
  1. 询问用户对电影的喜好
  2. 在本地知识库中搜索相关电影
  3. 调用LLM生成自然语言推荐理由

推荐流程：
  用户输入喜好 → 知识库检索 → LLM综合分析 → 输出推荐+理由

依赖：apiget.py, defines.py, llm_knowledge_base.py（工具模块，提供向量库加载/检索）
不依赖其他数据模块。
"""
import os
import json
import apiget
from defines import (
	REVIEWS_DIR, LLM_RESULTS_DIR, VECTOR_STORE_DIR,
	DEEPSEEK_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS,
	LLM_MAX_RETRIES, RETRIEVAL_TOP_K, OPENROUTER_GOOGLE
)


# ==================== LLM调用 ====================

def get_llm():
	"""获取LLM实例"""
	from langchain_deepseek import ChatDeepSeek
	return ChatDeepSeek(
		model=DEEPSEEK_MODEL,
		temperature=LLM_TEMPERATURE,
		max_tokens=LLM_MAX_TOKENS,
		max_retries=LLM_MAX_RETRIES,
	)


def generate_recommendation(llm, user_preference, retrieved_docs):
	"""基于检索结果和用户偏好，调用LLM生成推荐"""
	# 构建上下文
	context_parts = []
	for i, (doc, score) in enumerate(retrieved_docs, 1):
		meta = doc.metadata
		context_parts.append(
			f"【电影{i}】\n{doc.page_content}"
		)
	context = "\n\n".join(context_parts)

	prompt = f"""你是一位专业的电影推荐顾问。根据用户的喜好和以下电影知识库信息，为用户推荐最合适的电影。

用户喜好：{user_preference}

知识库中的相关电影信息：
{context}

请根据以上信息，为用户推荐最匹配的3部电影（如果可用电影不足3部则推荐全部），每部电影需要：
1. 电影名称
2. 推荐理由（结合用户喜好和电影特点，用自然语言描述，例如"因为您喜欢XX类型的电影，而《YY》同样是ZZ导演的作品，风格相似且口碑极佳……"）
3. 该电影的核心看点（一句话概括）

请按推荐优先级从高到低排列，格式如下：

推荐1：《电影名》
推荐理由：...
核心看点：...

推荐2：《电影名》
推荐理由：...
核心看点：...

推荐3：《电影名》
荐理由：...
核心看点：..."""

	try:
		response = llm.invoke(prompt)
		return response.content.strip()
	except Exception as e:
		return f"推荐生成失败: {e}"


def generate_followup_recommendation(llm, user_preference, movie_name, retrieved_docs):
	"""追问模式：基于用户对某部推荐电影的反馈，进一步推荐"""
	context_parts = []
	for i, (doc, score) in enumerate(retrieved_docs, 1):
		context_parts.append(f"【电影{i}】\n{doc.page_content}")
	context = "\n\n".join(context_parts)

	prompt = f"""你是一位专业的电影推荐顾问。用户之前表达了喜好"{user_preference}"，
现在对推荐电影《{movie_name}》感兴趣，希望找到更多类似的电影。

知识库中的相关电影信息：
{context}

请推荐3部与《{movie_name}》相似或相关的电影，每部给出：
1. 电影名称
2. 与《{movie_name}》的关联（如同一导演、相似题材、相似风格等）
3. 推荐理由

格式同上，用标记。"""

	try:
		response = llm.invoke(prompt)
		return response.content.strip()
	except Exception as e:
		return f"推荐生成失败: {e}"


# ==================== 交互逻辑 ====================

def get_user_preference():
	"""交互式获取用户偏好"""
	print("\n" + "=" * 50)
	print("🎬 豆瓣电影智能推荐系统")
	print("=" * 50)
	print("\n请告诉我您喜欢的电影类型/风格/导演，例如：")
	print("  - 我喜欢战争题材的深度电影")
	print("  - 想看新海诚的动画")
	print("  - 偏好悬疑推理类")
	print("  - 喜欢温情感人的故事")
	print()

	preference = input("您的喜好: ").strip()
	return preference


def load_reviews_for_movie(movie_name):
	"""加载某部电影的详细影评数据（用于追问）"""
	safe_name = movie_name.replace('/', '／').replace('\\', '＼')

	# 优先从LLM分析结果加载
	json_path = os.path.join(LLM_RESULTS_DIR, f'{safe_name}.json')
	if os.path.exists(json_path):
		with open(json_path, 'r', encoding='utf-8') as f:
			return json.load(f)

	# 回退到原始txt
	txt_path = os.path.join(REVIEWS_DIR, f'{safe_name}.txt')
	if os.path.exists(txt_path):
		from llm_knowledge_base import parse_movie_txt
		info, reviews = parse_movie_txt(txt_path)
		return {**info, "reviews": reviews}

	return None


# ==================== 主流程 ====================

def interactive_mode(vector_store=None):
	"""交互式推荐模式"""
	apiget.GetAPIMgr().SetAPIEnvironment()

	# 加载向量库
	if vector_store is None:
		from llm_knowledge_base import load_vector_store
		vector_store = load_vector_store()
		if vector_store is None:
			print("无法加载知识库，请先运行 llm_knowledge_base.py 构建知识库")
			return

	llm = get_llm()

	while True:
		# 获取用户偏好
		preference = get_user_preference()
		if not preference:
			print("请输入有效的喜好描述")
			continue

		# 检索相关电影
		print(f"\n正在搜索与“{preference}”相关的电影...")
		results = vector_store.similarity_search_with_score(preference, k=RETRIEVAL_TOP_K)

		if not results:
			print("未找到相关电影，请尝试其他关键词")
			continue

		# 生成推荐
		print("正在生成推荐...")
		recommendation = generate_recommendation(llm, preference, results)
		print(f"\n{recommendation}")

		# 追问循环
		while True:
			print("\n" + "-" * 40)
			print("操作选项:")
			print("  1. 输入电影名 → 查找更多类似电影")
			print("  2. 输入新的喜好 → 重新推荐")
			print("  3. 输入 q → 退出")
			choice = input("\n请选择: ").strip()

			if choice == 'q' or choice == 'Q':
				print("再见！🎬")
				return
			elif choice == '2' or choice == '':
				break
			elif choice.isdigit() and choice == '1':
				movie_name = input("请输入感兴趣的电影名: ").strip()
				if not movie_name:
					continue
				# 追问推荐
				followup_results = vector_store.similarity_search_with_score(
					movie_name, k=RETRIEVAL_TOP_K
				)
				followup = generate_followup_recommendation(
					llm, preference, movie_name, followup_results
				)
				print(f"\n{followup}")
			else:
				# 直接当作新的偏好/电影名
				if len(choice) > 2:
					# 当作电影名进行追问
					followup_results = vector_store.similarity_search_with_score(
						choice, k=RETRIEVAL_TOP_K
					)
					followup = generate_followup_recommendation(
						llm, preference, choice, followup_results
					)
					print(f"\n{followup}")
				else:
					break


def run():
	"""主入口"""
	interactive_mode()


if __name__ == "__main__":
	run()
