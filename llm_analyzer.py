# -*- coding: utf-8 -*-
"""
LLM情感分析与摘要模块
读取 reviews_score/ 下的txt文件，调用DeepSeek LLM进行：
  1. 影评情感分析（正面/负面/中性 + 简短理由），批量处理
  2. 电影影评总结性摘要（约100字）
结果保存为 llm_results/<电影名>.json

依赖：apiget.py, defines.py（工具模块）
不依赖其他数据模块，仅读取txt数据文件。
"""
import os
import re
import json
import time
import apiget
from defines import (
	REVIEWS_DIR, LLM_RESULTS_DIR,
	DEEPSEEK_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS,
	LLM_MAX_RETRIES, LLM_REQUEST_INTERVAL,
	SENTIMENT_BATCH_SIZE,
)


# ==================== 数据解析 ====================

def parse_movie_txt(file_path):
	"""解析单个电影的txt文件，返回结构化数据"""
	with open(file_path, 'r', encoding='utf-8') as f:
		content = f.read()

	movie_info = {}
	reviews = []

	# 解析元信息
	for key in ["电影名称", "电影ID", "导演", "类型", "上映时间", "国家/地区", "主演"]:
		pattern = rf'^{re.escape(key)}:\s*(.+)$'
		match = re.search(pattern, content, re.MULTILINE)
		if match:
			movie_info[key] = match.group(1).strip()

	# 解析影评
	# 格式1: review_N:评分：X 内容：<text>
	# 格式2: review_N:内容：<text>（无评分）
	review_pattern = r'review_\d+:(?:评分：(\d+)\s+)?内容：(.+)'
	for match in re.finditer(review_pattern, content):
		score = int(match.group(1)) if match.group(1) else None
		text = match.group(2).strip()
		reviews.append({"text": text, "score": score})

	return movie_info, reviews


# ==================== LLM调用 ====================

def get_llm():
	"""获取LLM实例（ChatDeepSeek）"""
	from langchain_deepseek import ChatDeepSeek
	return ChatDeepSeek(
		model=DEEPSEEK_MODEL,
		temperature=LLM_TEMPERATURE,
		max_tokens=LLM_MAX_TOKENS,
		max_retries=LLM_MAX_RETRIES,
	)


def analyze_sentiment_batch(llm, reviews_batch):
	"""批量分析影评情感，返回每条影评的情感标签和理由"""
	review_list = "\n".join(
		f"{i+1}. {r['text']}" for i, r in enumerate(reviews_batch)
	)
	prompt = f"""请对以下影评进行情感分析，对每条影评判断为"正面"、"负面"或"中性"，并给出简短理由（不超过10个字）。
请严格按照以下格式输出，每条一行，不要输出其他内容：
1. 正面 - 理由
2. 负面 - 理由
3. 中性 - 理由

影评列表：
{review_list}"""

	try:
		response = llm.invoke(prompt)
		result_text = response.content
	except Exception as e:
		print(f"  [LLM错误] 情感分析失败: {e}")
		return [{"sentiment": "中性", "reason": "分析失败"} for _ in reviews_batch]

	# 解析LLM输出
	sentiments = []
	for line in result_text.strip().split('\n'):
		line = line.strip()
		if not line:
			continue
		# 匹配: "1. 正面 - 理由" 或 "1.正面-理由"
		match = re.match(r'\d+[.、]\s*(正面|负面|中性)\s*[-—]\s*(.+)', line)
		if match:
			sentiments.append({
				"sentiment": match.group(1),
				"reason": match.group(2).strip()
			})
		else:
			sentiments.append({"sentiment": "中性", "reason": "无法解析"})

	# 补齐缺失项
	while len(sentiments) < len(reviews_batch):
		sentiments.append({"sentiment": "中性", "reason": "未分析"})

	return sentiments[:len(reviews_batch)]


def generate_summary(llm, movie_name, reviews):
	"""为电影生成总结性摘要（约100字）"""
	# 选取代表性影评（最多30条）
	sample_reviews = reviews[:30]
	review_text = "\n".join(
		f"- {r['text']}" for r in sample_reviews
	)
	prompt = f"""请根据以下影评内容，为电影《{movie_name}》生成一段100字左右的总结性摘要，概括观众的主要观点和评价倾向。只输出摘要内容，不要其他内容。

影评摘录：
{review_text}"""

	try:
		response = llm.invoke(prompt)
		return response.content.strip()
	except Exception as e:
		print(f"  [LLM错误] 摘要生成失败: {e}")
		return "摘要生成失败"


# ==================== 主流程 ====================

def analyze_movie(file_path, output_dir=None):
	"""对单个电影进行完整LLM分析"""
	if output_dir is None:
		output_dir = LLM_RESULTS_DIR

	movie_info, reviews = parse_movie_txt(file_path)
	movie_name = movie_info.get("电影名称", "未知")

	if not reviews:
		print(f"  电影《{movie_name}》无影评数据，跳过")
		return None

	print(f'  分析电影《{movie_name}》，共 {len(reviews)} 条影评')

	llm = get_llm()

	# 1. 批量情感分析
	print(f'  [1/2] 情感分析中...')
	all_sentiments = []
	for i in range(0, len(reviews), SENTIMENT_BATCH_SIZE):
		batch = reviews[i:i + SENTIMENT_BATCH_SIZE]
		sentiments = analyze_sentiment_batch(llm, batch)
		all_sentiments.extend(sentiments)
		print(f'    已分析 {min(i + SENTIMENT_BATCH_SIZE, len(reviews))}/{len(reviews)} 条')
		time.sleep(LLM_REQUEST_INTERVAL)

	# 合并情感结果到reviews
	for i, sentiment in enumerate(all_sentiments):
		if i < len(reviews):
			reviews[i]["sentiment"] = sentiment["sentiment"]
			reviews[i]["reason"] = sentiment["reason"]

	# 2. 生成摘要
	print(f'  [2/2] 生成摘要...')
	summary = generate_summary(llm, movie_name, reviews)
	time.sleep(LLM_REQUEST_INTERVAL)

	# 3. 统计情感分布
	sentiment_dist = {"正面": 0, "负面": 0, "中性": 0}
	for r in reviews:
		s = r.get("sentiment", "中性")
		sentiment_dist[s] = sentiment_dist.get(s, 0) + 1

	# 4. 计算平均评分
	scores = [r["score"] for r in reviews if r.get("score") is not None]
	avg_score = sum(scores) / len(scores) if scores else 0

	# 5. 提取代表性影评
	positive_samples = [r["text"] for r in reviews if r.get("sentiment") == "正面"][:5]
	negative_samples = [r["text"] for r in reviews if r.get("sentiment") == "负面"][:5]

	# 6. 组装结果
	result = {
		**movie_info,
		"avg_score": round(avg_score, 2),
		"review_count": len(reviews),
		"sentiment_distribution": sentiment_dist,
		"summary": summary,
		"positive_samples": positive_samples,
		"negative_samples": negative_samples,
		"reviews": reviews,
	}

	# 7. 保存
	if not os.path.exists(output_dir):
		os.makedirs(output_dir)
	safe_name = movie_name.replace('/', '／').replace('\\', '＼')
	out_path = os.path.join(output_dir, f'{safe_name}.json')
	with open(out_path, 'w', encoding='utf-8') as f:
		json.dump(result, f, ensure_ascii=False, indent=2)
	print(f'  分析结果已保存至: {out_path}')

	return result


def run(data_dir=None, output_dir=None):
	"""主流程：分析 reviews_score/ 下所有txt文件"""
	apiget.GetAPIMgr().SetAPIEnvironment()

	if data_dir is None:
		data_dir = REVIEWS_DIR
	if output_dir is None:
		output_dir = LLM_RESULTS_DIR

	if not os.path.exists(data_dir):
		print(f"数据目录不存在: {data_dir}")
		print("请先运行 douban_crawler.py 爬取数据")
		return

	txt_files = [f for f in os.listdir(data_dir) if f.endswith('.txt')]
	if not txt_files:
		print(f"数据目录中无txt文件: {data_dir}")
		return

	print(f"找到 {len(txt_files)} 个电影数据文件")
	for i, txt_file in enumerate(txt_files, 1):
		print(f'\n{"="*50}')
		print(f'[{i}/{len(txt_files)}] 正在分析: {txt_file}')
		print(f'{"="*50}')
		file_path = os.path.join(data_dir, txt_file)
		analyze_movie(file_path, output_dir)

	print(f'\n全部分析完成！结果保存在 {output_dir}')


if __name__ == "__main__":
	# 测试：分析指定目录下的影评数据
	import sys
	if len(sys.argv) > 1:
		data_dir = sys.argv[1]
	else:
		data_dir = None
	run(data_dir=data_dir)
