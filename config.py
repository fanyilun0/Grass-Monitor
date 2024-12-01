# API配置
API_URL = "https://api.getgrass.io/activeDevices"
PROFILE_API_URL = "https://api.getgrass.io/retrieveUser"

# Token配置示例
TOKENS_CONFIG = [
    {
        'name': 'Token1',  # token标识名称
        'token': '' 
    },
    {
        'name': 'Token2',
        'token': ''
    },
    # 可以添加更多token配置...
]
# Webhook配置
WEBHOOK_URL = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key='

# 应用名称
APP_NAME = 'Grass'

# 代理配置
PROXY_URL = 'http://localhost:7890'
USE_PROXY = False
ALWAYS_NOTIFY = True
SHOW_DETAIL = True
# 时间配置
INTERVAL = 36000  # 10小时检查一次
TIME_OFFSET = 6  
