# -*- coding: utf-8 -*-
"""
豆瓣电影数据爬虫模块
整合原始项目的F0（主演）+ F1（详情+影评），输出为 reviews_score/<电影名>.txt 格式

输出格式与已有数据一致：
	电影名称: xxx
	电影ID: xxx
	导演: xxx
	类型: xxx
	上映时间: xxx
	国家/地区: xxx
	主演: xxx

	影评:

	review_1:评分：5 内容：xxx
	review_2:评分：4 内容：xxx
	...

依赖：defines.py, douban_request.py（工具模块）
不依赖其他数据模块。
"""
import os
import re
from lxml import html
from parsel import Selector

from defines import REVIEWS_DIR, CRAWL_PAGES
from douban_request import get_manager


def crawl_movie_details(movie_id):
	"""爬取电影详情：名称、导演、类型、上映时间、国家/地区、主演"""
	detail_url = f'https://movie.douban.com/subject/{movie_id}'
	manager = get_manager()
	response = manager.get(detail_url, referer='https://movie.douban.com/')

	default_info = {
		"电影名称": "未知电影", "电影ID": str(movie_id),
		"导演": "未知导演", "类型": "未知类型",
		"上映时间": "未知", "国家/地区": "未知",
		"主演": "未知主演"
	}
	if response is None:
		print(f"  获取电影 {movie_id} 详情页失败")
		return default_info

	try:
		doc = html.fromstring(response.content.decode('utf-8'))

		movie_name = doc.xpath('//span[@property="v:itemreviewed"]/text()')
		movie_name = movie_name[0].strip() if movie_name else "未知电影"

		director = doc.xpath('//a[@rel="v:directedBy"]/text()')
		director = director[0].strip() if director else "未知导演"

		genres = doc.xpath('//span[@property="v:genre"]/text()')
		genres = ", ".join(g.strip() for g in genres) if genres else "未知类型"

		release_date = doc.xpath('//span[@property="v:initialReleaseDate"]/text()')
		release_date = release_date[0].strip() if release_date else "未知"

		country = doc.xpath(
			'//span[@class="pl"][text()="制片国家/地区:"]/following-sibling::text()[1]')
		country = country[0].strip() if country else "未知"

		cast = doc.xpath('//a[@rel="v:starring"]/text()')
		cast = ", ".join(c.strip() for c in cast) if cast else "未知主演"

		return {
			"电影名称": movie_name, "电影ID": str(movie_id),
			"导演": director, "类型": genres,
			"上映时间": release_date, "国家/地区": country,
			"主演": cast
		}
	except Exception as e:
		print(f"  解析电影详情页错误: {e}")
		return default_info


def crawl_movie_reviews(movie_id, pages=None):
	"""爬取指定电影的影评和评分，返回 (影评列表, 评分列表)"""
	if pages is None:
		pages = CRAWL_PAGES

	manager = get_manager()
	base_url = f'https://movie.douban.com/subject/{movie_id}/comments'
	reviews = []
	scores = []

	for page in range(0, pages):
		url = f'{base_url}?start={page * 20}&limit=20&status=P&sort=new_score'
		referer = f'https://movie.douban.com/subject/{movie_id}/'

		print(f'  正在爬取第 {page + 1}/{pages} 页评论...')
		response = manager.get(url, referer=referer)

		if response is None:
			print(f'  第 {page + 1} 页获取失败，跳过')
			continue

		if response.status_code != 200:
			print(f'  第 {page + 1} 页返回 HTTP {response.status_code}，跳过')
			continue

		try:
			selector = Selector(text=response.content.decode('utf-8'))
			comments = selector.css('.comment-item')

			if not comments:
				print(f'  第 {page + 1} 页未找到评论，可能已无更多数据')
				if page == 0:
					page_text = response.text
					if '检查浏览器' in page_text or '禁止访问' in page_text:
						print("  [提示] 检测到反爬拦截，请更新 cookies.txt")
					elif '登录' in page_text and '评论' not in page_text:
						print("  [提示] 需要登录才能查看评论，请提供有效Cookie")
				break

			for comment in comments:
				# 提取评分（1-5星）
				score_class = comment.css('.comment-info .rating::attr(class)').get()
				score_value = None
				if score_class:
					match = re.search(r'allstar(\d+)', score_class)
					if match:
						sv = int(match.group(1))
						if 10 <= sv <= 50:
							score_value = sv // 10  # 转为1-5
				scores.append(score_value)

				# 提取影评文本
				short = comment.css('.short::text').get()
				if short:
					short = short.strip()
					if short not in reviews:
						reviews.append(short)

		except Exception as e:
			print(f'  第 {page + 1} 页解析错误: {e}")
			continue

	print(f'  共爬取到 {len(reviews)} 条影评')
	return reviews, scores


def save_reviews_txt(movie_data, reviews, scores, output_dir=None):
	"""将爬取结果保存为txt文件，格式与已有数据一致"""
	if output_dir is None:
		output_dir = REVIEWS_DIR
	if not os.path.exists(output_dir):
		os.makedirs(output_dir)

	movie_name = movie_data["电影名称"]
	# 文件名中的/替换为全角，避免路径问题
	safe_name = movie_name.replace('/', '／').replace('\\', '＼')
	file_path = os.path.join(output_dir, f'{safe_name}.txt')

	with open(file_path, 'w', encoding='utf-8', errors='ignore') as f:
		# 电影元信息
		f.write(f'电影名称: {movie_data["电影名称"]}\n')
		f.write(f'电影ID: {movie_data["电影ID"]}\n')
		f.write(f'导演: {movie_data["导演"]}\n')
		f.write(f'类型: {movie_data["类型"]}\n')
		f.write(f'上映时间: {movie_data["上映时间"]}\n')
		f.write(f'国家/地区: {movie_data["国家/地区"]}\n')
		f.write(f'主演: {movie_data["主演"]}\n')
		f.write('\n影评:\n')

		# 影评列表
		for i, (review, score) in enumerate(zip(reviews, scores), 1):
			f.write(f'\nreview_{i}:')
			if score is not None:
				f.write(f'评分：{score}')
			f.write(f' 内容：{review}\n')

	print(f'  影评数据已保存至: {file_path}')
	return file_path


def run(movie_ids=None, pages=None):
	"""主流程：爬取电影数据并保存为txt"""
	if movie_ids is None:
		ids_input = input("请输入电影ID（多个用逗号分隔）: ")
		movie_ids = [mid.strip() for mid in ids_input.split(',') if mid.strip()]

	if pages is None:
		pages = CRAWL_PAGES

	success_count = 0
	for movie_id in movie_ids:
		print(f'\n{"="*50}')
		print(f'正在处理电影ID: {movie_id}')
		print(f'{"="*50}')

		# 1. 爬取详情+主演
		print('  [1/2] 爬取电影详情...')
		movie_data = crawl_movie_details(movie_id)
		print(f'  电影名称: {movie_data["电影名称"]}')
		print(f'  导演: {movie_data["导演"]}')
		print(f'  类型: {movie_data["类型"]}')

		# 2. 爬取影评+评分
		print('  [2/2] 爬取影评数据...')
		reviews, scores = crawl_movie_reviews(movie_id, pages)

		# 3. 保存
		if reviews:
			save_reviews_txt(movie_data, reviews, scores)
			success_count += 1
		else:
			print(f'  电影 {movie_id} 未获取到任何影评数据')

	print(f'\n完成！成功爬取 {success_count}/{len(movie_ids)} 部电影')


if __name__ == "__main__":
	# 测试：爬取指定电影
	test_ids = input("请输入电影ID（多个用逗号分隔，回车使用默认）: ").strip()
	if test_ids:
		movie_ids = [mid.strip() for mid in test_ids.split(',')]
	else:
		# 默认测试：我们的父辈
		movie_ids = ["22623816"]
	run(movie_ids=movie_ids)
