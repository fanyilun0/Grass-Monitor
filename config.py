import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# API配置
API_URL = "https://api.getgrass.io/devices?input=%7B%22limit%22:50%7D"
PROFILE_API_URL = "https://api.getgrass.io/retrieveUser"
EPOCH_EARNINGS_API_URL = "https://api.getgrass.io/epochEarnings?input={\"isLatestOnly\":false}"
# Token配置示例
TOKENS_CONFIG = [
    {
    'name': '1', 
    'token': os.getenv('USER1_TOKEN')
    },
    {
    'name': '2',
    'token': os.getenv('USER2_TOKEN')
    },
    {
    'name': '3', 
    'token': os.getenv('USER3_TOKEN')
    },
    {
    'name': '4', 
    'token': os.getenv('USER4_TOKEN')
    },
    {
    'name': '5',
    'token': os.getenv('USER5_TOKEN')
    },
    # 添加更多用户配置
]
# Webhook配置
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

# 应用名称
APP_NAME = 'Grass'

# 代理配置
PROXY_URL = 'http://localhost:7890'
USE_PROXY = False
ALWAYS_NOTIFY = True
SHOW_DETAIL = True
# 时间配置
INTERVAL = 10800  # 3小时检查一次
TIME_OFFSET = 0 

