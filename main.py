# -*- coding: utf-8 -*-
"""
豆瓣影评LLM分析系统 - 主入口
整合各模块，提供统一的工作流：

  1. 爬取电影数据 (douban_crawler)
  2. LLM情感分析与摘要 (llm_analyzer)
  3. 构建本地知识库 (llm_knowledge_base)
  4. 电影推荐 (llm_recommender)
"""
import os
import sys
import apiget

# 确保工作目录为项目根目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def menu():
	print("\n" + "=" * 50)
	print("🎬 豆瓣影评LLM分析系统")
	print("=" * 50)
	print("  1. 爬取电影数据")
	print("  2. LLM情感分析与摘要")
	print("  3. 构建本地知识库")
	print("  4. 电影推荐")
	print("  5. 完整流程（1→2→3→4）")
	print("  0. 退出")
	print("=" * 50)


def step_crawl():
	"""步骤1：爬取电影数据"""
	from douban_crawler import run as crawl_run
	ids_input = input("请输入电影ID（多个用逗号分隔）: ").strip()
	if not ids_input:
		print("未输入电影ID，返回")
		return False
	movie_ids = [mid.strip() for mid in ids_input.split(',') if mid.strip()]
	crawl_run(movie_ids=movie_ids)
	return True


def step_analyze():
	"""步骤2：LLM情感分析"""
	from llm_analyzer import run as analyze_run
	analyze_run()
	return True


def step_build_kb():
	"""步骤3：构建知识库"""
	from llm_knowledge_base import run as kb_run
	kb_run()
	return True


def step_recommend():
	"""步骤4：电影推荐"""
	from llm_recommender import run as rec_run
	rec_run()
	return True


def step_full():
	"""完整流程"""
	# 步骤1：爬取
	print("\n" + "▶" * 20)
	print("步骤 1/4：爬取电影数据")
	print("▶" * 20)
	if not step_crawl():
		return

	# 步骤2：分析
	print("\n" + "▶" * 20)
	print("步骤 2/4：LLM情感分析与摘要")
	print("▶" * 20)
	step_analyze()

	# 步骤3：构建知识库
	print("\n" + "▶" * 20)
	print("步骤 3/4：构建本地知识库")
	print("▶" * 20)
	step_build_kb()

	# 步骤4：推荐
	print("\n" + "▶" * 20)
	print("步骤 4/4：电影推荐")
	print("▶" * 20)
	step_recommend()


def main():
	# 初始化API环境
	apiget.GetAPIMgr().SetAPIEnvironment()

	# 命令行模式
	if len(sys.argv) > 1:
		cmd = sys.argv[1]
		if cmd == "crawl":
			step_crawl()
		elif cmd == "analyze":
			step_analyze()
		elif cmd == "build-kb":
			step_build_kb()
		elif cmd == "recommend":
			step_recommend()
		elif cmd == "full":
			step_full()
		else:
			print(f"未知命令: {cmd}")
			print("可用命令: crawl, analyze, build-kb, recommend, full")
		return

	# 交互模式
	while True:
		menu()
		choice = input("\n请选择操作: ").strip()

		if choice == '1':
			step_crawl()
		elif choice == '2':
			step_analyze()
		elif choice == '3':
			step_build_kb()
		elif choice == '4':
			step_recommend()
		elif choice == '5':
			step_full()
		elif choice in ('0', 'q', 'Q'):
			print("再见！🎬")
			break
		else:
			print("无效选择，请重试")


if __name__ == "__main__":
	main()
