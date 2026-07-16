# -*- coding: utf-8 -*-
"""
豆瓣请求管理器 - 反反爬核心模块（工具类）
应对豆瓣2024-2026年更新的反爬机制：
  - Cookie校验、UA模式检测、频率/模式识别、403/418限流、TLS指纹

策略：Cookie + UA轮换 + 智能延迟 + Session复用 + 重试退避
"""
import os
import time
import random
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from defines import (
	COOKIE_FILE, USER_AGENT_POOL, COMMON_HEADERS,
	CRAWL_MIN_DELAY, CRAWL_MAX_DELAY,
	LONG_PAUSE_EVERY, LONG_PAUSE_PROB,
	LONG_PAUSE_MIN, LONG_PAUSE_MAX,
	COOLDOWN_BASE, COOLDOWN_MAX,
	CRAWL_MAX_RETRIES, CRAWL_BACKOFF_FACTOR,
)


def load_cookies_from_file(cookie_file=None):
	"""
	从文件加载Cookie
	支持格式：
	  1. 每行 key=value
	  2. Netscape格式（wget/curl的cookies.txt）
	  3. 浏览器完整Cookie字符串（分号分隔）
	"""
	if cookie_file is None:
		cookie_file = COOKIE_FILE
	cookies = {}
	if not os.path.exists(cookie_file):
		print(f"[警告] Cookie文件不存在: {cookie_file}")
		print("  请从浏览器登录豆瓣后，导出Cookie到此文件")
		print("  格式: 每行一个 key=value，如: bid=xxxxx")
		return cookies

	with open(cookie_file, 'r', encoding='utf-8') as f:
		for line in f:
			line = line.strip()
			if not line or line.startswith('#'):
				continue
			# Netscape格式
			if line.count('\t') >= 6:
				parts = line.split('\t')
				name = parts[-2].strip()
				value = parts[-1].strip()
				if name:
					cookies[name] = value
			# key=value 或 分号分隔的Cookie字符串
			elif '=' in line:
				for pair in line.split(';'):
					pair = pair.strip()
					if '=' in pair:
						key, val = pair.split('=', 1)
						cookies[key.strip()] = val.strip()
	if cookies:
		print(f"[Cookie] 已加载 {len(cookies)} 个Cookie项")
	return cookies


class DoubanRequestManager:
	"""豆瓣请求管理器，封装反反爬策略"""

	def __init__(self, cookie_file=None):
		self.session = self._create_session()
		self.cookies = load_cookies_from_file(cookie_file)
		self.request_count = 0
		self.last_request_time = 0
		self._403_count = 0

		for name, value in self.cookies.items():
			self.session.cookies.set(name, value, domain='.douban.com')

	@staticmethod
	def _create_session():
		session = requests.Session()
		retry_strategy = Retry(
			total=CRAWL_MAX_RETRIES,
			backoff_factor=CRAWL_BACKOFF_FACTOR,
			status_forcelist=[500, 502, 503, 504],
			allowed_methods=["GET"],
		)
		adapter = HTTPAdapter(max_retries=retry_strategy)
		session.mount("http://", adapter)
		session.mount("https://", adapter)
		return session

	@staticmethod
	def _get_random_headers():
		headers = dict(COMMON_HEADERS)
		headers['User-Agent'] = random.choice(USER_AGENT_POOL)
		return headers

	def _smart_delay(self):
		delay = random.uniform(CRAWL_MIN_DELAY, CRAWL_MAX_DELAY)
		if self.request_count > 0 and self.request_count % LONG_PAUSE_EVERY == 0:
			if random.random() < LONG_PAUSE_PROB:
				long_pause = random.uniform(LONG_PAUSE_MIN, LONG_PAUSE_MAX)
				print(f"  [休息] 模拟阅读停顿 {long_pause:.0f}秒...")
				time.sleep(long_pause)
				return
		jitter = random.uniform(-0.5, 1.0)
		actual_delay = max(1.0, delay + jitter)
		time.sleep(actual_delay)

	def _handle_rate_limit(self, response, url) -> bool:
		if response.status_code in (403, 418):
			self._403_count += 1
			cooldown = min(COOLDOWN_BASE * (2 ** (self._403_count - 1)), COOLDOWN_MAX)
			print(f"  [限流] HTTP {response.status_code}，冷却 {cooldown:.0f}秒...")
			time.sleep(cooldown)
			return True
		if response.status_code == 200:
			self._403_count = 0
		return False

	def get(self, url, referer=None, max_retries=None):
		"""带完整反反爬策略的GET请求"""
		if max_retries is None:
			max_retries = CRAWL_MAX_RETRIES + 2

		for attempt in range(max_retries):
			try:
				self._smart_delay()
				headers = self._get_random_headers()
				if referer:
					headers['Referer'] = referer

				response = self.session.get(url, headers=headers, timeout=15)
				self.request_count += 1

				if self._handle_rate_limit(response, url):
					continue

				if 'accounts.douban.com' in response.url:
					print("  [重定向] 被跳转到登录页，Cookie可能已过期")
					if attempt < max_retries - 1:
						time.sleep(random.uniform(10, 20))
						continue
					return None

				if 'captcha' in response.text.lower() and response.status_code == 200:
					print("  [验证码] 触发了验证码，建议降低频率或更新Cookie")
					time.sleep(random.uniform(30, 60))
					continue

				return response

			except requests.exceptions.Timeout:
				print(f"  [超时] 第{attempt + 1}次尝试")
				time.sleep(random.uniform(5, 10))
			except requests.exceptions.ConnectionError as e:
				print(f"  [连接错误] 第{attempt + 1}次: {e}")
				time.sleep(random.uniform(10, 20))
			except Exception as e:
				print(f"  [未知错误] 第{attempt + 1}次: {e}")
				time.sleep(random.uniform(5, 10))

		print(f"  [失败] 达到最大重试次数: {url}")
		return None


# 模块级便捷函数
_manager = None


def get_manager(cookie_file=None):
	"""获取全局请求管理器单例"""
	global _manager
	if _manager is None:
		_manager = DoubanRequestManager(cookie_file)
	return _manager


def douban_get(url, referer=None):
	"""便捷函数：使用全局管理器发起请求"""
	return get_manager().get(url, referer=referer)


if __name__ == "__main__":
	# 测试：访问豆瓣首页，验证Cookie和请求是否正常
	print("测试豆瓣请求管理器...")
	mgr = DoubanRequestManager()
	resp = mgr.get("https://movie.douban.com/", referer="https://www.douban.com/")
	if resp and resp.status_code == 200:
		print(f"请求成功！状态码: {resp.status_code}，内容长度: {len(resp.text)}")
	else:
		print(f"请求失败: {resp}")
