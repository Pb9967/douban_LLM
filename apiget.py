# -*- coding: utf-8 -*-
# Ciallo～(∠・ω< )⌒☆
"""
API管理工具模块
使用方式：
	import apiget
	apiget.GetAPIMgr().SetAPIEnvironment()  # 初始化，载入.env
	# 之后 os.environ.get('DEEPSEEK_API_KEY') 或 GetAPIMgr().GetAPI("DeepSeek") 即可获取Key
"""
API_MGR = None


def GetAPIMgr():
	global API_MGR
	if API_MGR is None:
		API_MGR = CAgentAPI()
	return API_MGR


class CAgentAPI(object):
	def __init__(self):
		self.dctAPI = {}

	def GetAPI(self, _key="OPENROUTER_API_KEY")->str:
		"""显式获取APIKEY"""
		if not self.dctAPI:
			if not self.CheckAPIKeys():
				return ""
		apikey = self.dctAPI.get(_key)
		if not apikey:
			print("未找到对应模型的API，配置.env文件")
			return ""
		return apikey

	def CheckAPIKeys(self)->bool:
		"""从.env中获取APIKEY"""
		from pathlib import Path
		env_path = Path.cwd() / ".env"
		if not env_path.exists():
			print(f"错误：未找到 .env 文件 ({env_path})，请创建并配置 API_KEY。")
			return False

		try:
			with open(env_path, "r", encoding="utf-8") as f:
				lines = f.readlines()
		except Exception as e:
			print(f"错误：无法读取 .env 文件 ({env_path})，原因：{e}")
			return False

		valid_keys = {}
		for line in lines:
			line = line.strip()
			# 跳过空行和注释行
			if not line or line.startswith("#"):
				continue
			# 匹配变量定义行：VAR_NAME=value （value 可能被引号包裹）
			if "=" not in line:
				continue
			var_name, _, value = line.partition("=")
			var_name = var_name.strip()
			value = value.strip()

			# 只关心 *_API_KEY 变量（不区分大小写保险）
			if not var_name.upper().endswith("_API_KEY"):
				continue

			# 去掉可能存在的引号（单引号或双引号）
			if (value.startswith('"') and value.endswith('"')) or \
					(value.startswith("'") and value.endswith("'")):
				value = value[1:-1]

			# 排除明显的占位符或空值
			if not value or value.lower() in ["your-api-key", "your_api_key"]:
				continue

			valid_keys[var_name] = value

		self.dctAPI = valid_keys

		if self.dctAPI:
			return True
		else:
			print("获取API失败：.env 文件中没有任何有效的 API_KEY。请至少配置一个有效的 Key。")
			return False

	@staticmethod
	def SetAPIEnvironment():
		"""从.env文件加载环境变量"""
		from dotenv import load_dotenv
		load_dotenv()

if __name__ == "__main__":
	apiMgr = GetAPIMgr()
	apiMgr.SetAPIEnvironment()
	print("APIKEYS: ", apiMgr.CheckAPIKeys())
	print("API get: ", apiMgr.GetAPI("DEEPSEEK_API_KEY"))
