import asyncio
import aiohttp
from datetime import datetime, timedelta
import random
import json

# 导入配置
from config import (
    API_URL,  # 节点列表API
    PROFILE_API_URL,  # 个人资料API
    TOKENS_CONFIG,
    WEBHOOK_URL, 
    PROXY_URL, 
    USE_PROXY, 
    INTERVAL, 
    TIME_OFFSET,
    ALWAYS_NOTIFY,
    APP_NAME
)

# 新增：随机延迟函数
async def random_delay():
    """生成随机延迟时间（3-10秒）"""
    delay = random.uniform(30, 100)
    print(f"等待 {delay:.2f} 秒...")
    await asyncio.sleep(delay)

async def monitor_single_token(session, token_config, webhook_url, use_proxy, proxy_url):
    """监控单个token的节点状态"""
    try:
        await random_delay()
        
        print(f"\n=== 检查Token: {token_config['name']} ===")
        
        # 获取用户资料
        profile_data = await fetch_profile_data(session, token_config['token'])
        username = profile_data.get('username', '未知用户')
        
        # 获取节点数据
        result_data, total_uptime, online_count, offline_count = await fetch_nodes_data(
            session=session,
            api_url=API_URL,
            api_token=token_config['token']
        )
        
        if not result_data:
            print(f"获取节点数据失败，跳过此token: {token_config['name']}")
            return
            
        # 构建统计消息
        message = build_node_stats_message(
            token_name=token_config['name'],
            username=username,
            result_data=result_data,
            total_uptime=total_uptime,
            online_count=online_count,
            offline_count=offline_count
        )
        
        # 发送消息
        if message:
            await send_message_async(webhook_url, message, use_proxy, proxy_url)
            
    except Exception as e:
        print(f"监控Token {token_config['name']} 时出错: {str(e)}")

def build_node_stats_message(token_name, username, result_data, total_uptime, online_count, offline_count):
    """构建节点统计消息"""
    adjusted_time = datetime.now() + timedelta(hours=TIME_OFFSET)
    timestamp = adjusted_time.strftime('%Y-%m-%d %H:%M:%S')
    
    # 获取异常节点
    offline_nodes = [node for node in result_data if node['ipScore'] == 0]
    abnormal_score_nodes = [node for node in result_data if node['ipScore'] != 100]
    
    message_lines = [
        f"🔍 【{APP_NAME}节点状态报告】",
        f"⏰ 时间: {timestamp}",
        f"👤 账户: {token_name} ({username})\n",
        f"📊 节点统计:",
        f"  • 总节点数: {len(result_data)}",
        f"  • 在线节点: {online_count}",
        f"  • 离线节点: {offline_count}",
        f"  • 总运行时间: {format_uptime(total_uptime)}"
    ]
    
    # 添加离线节点信息
    if offline_nodes:
        message_lines.extend([
            f"\n❌ 离线节点 ({len(offline_nodes)}):"
        ])
        for node in offline_nodes:
            message_lines.append(f"  • IP: {node['ipAddress']}")
            message_lines.append(f"    设备ID: {node['deviceId']}")
    
    # 添加IP分数异常节点信息
    abnormal_non_offline = [node for node in abnormal_score_nodes if node['ipScore'] != 0]
    if abnormal_non_offline:
        message_lines.extend([
            f"\n⚠️ IP分数异常节点 ({len(abnormal_non_offline)}):"
        ])
        for node in abnormal_non_offline:
            message_lines.append(f"  • IP: {node['ipAddress']}")
            message_lines.append(f"    设备ID: {node['deviceId']}")
            message_lines.append(f"    IP分数: {node['ipScore']}")
    
    return "\n".join(message_lines)

def format_uptime(seconds):
    """格式化运行时间"""
    days = seconds // (24 * 3600)
    hours = (seconds % (24 * 3600)) // 3600
    minutes = (seconds % 3600) // 60
    
    parts = []
    if days > 0:
        parts.append(f"{days}天")
    if hours > 0:
        parts.append(f"{hours}小时")
    if minutes > 0:
        parts.append(f"{minutes}分钟")
    
    return "".join(parts) if parts else "小于1分钟"

def get_random_user_agent():
    """获取随机User-Agent"""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0"
    ]
    return random.choice(user_agents)


async def send_message_async(webhook_url, message_content, use_proxy, proxy_url):
    headers = {'Content-Type': 'application/json'}
    
    payload = {
        "msgtype": "text",
        "text": {
            "content": message_content
        }
    }
    
    proxy = proxy_url if use_proxy else None
    async with aiohttp.ClientSession() as session:
        async with session.post(webhook_url, json=payload, headers=headers, proxy=proxy) as response:
            if response.status == 200:
                print("Message sent successfully!")
            else:
                print(f"Failed to send message: {response.status}, {await response.text()}")


async def fetch_nodes_data(session, api_url, api_token):
    """获取节点数据"""
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
        "authorization": f"{api_token}",
        "content-type": "application/json",
        "user-agent": get_random_user_agent()
    }
    
    try:
        async with session.get(api_url, headers=headers, timeout=30, ssl=False) as response:
            print(f"响应状态码: {response.status}")
            
            if response.status == 403:
                print(f"Token认证失败，请检查token是否有效: {api_token}")
                return None, 0, 0, 0
            elif response.status == 200:
                data = await response.json()
                
                # 直接获取 result.data 数组
                result_data = data.get('result', {}).get('data', [])
                print(f"获取到的节点数量: {len(result_data)}")
                
                # 统计数据
                total_uptime = sum(node['aggUptime'] for node in result_data)
                online_nodes = [node for node in result_data if node['ipScore'] > 0]
                offline_nodes = [node for node in result_data if node['ipScore'] == 0]
                abnormal_score_nodes = [node for node in result_data if node['ipScore'] != 100]
                
                print(f"\n总在线时间: {total_uptime}秒")
                print(f"在线节点数量: {len(online_nodes)}")
                print(f"离线节点数量: {len(offline_nodes)}")
                
                # 打印离线节点的IP地址
                if offline_nodes:
                    print("\n离线节点IP列表:")
                    for node in offline_nodes:
                        print(f"- IP: {node['ipAddress']}, 设备ID: {node['deviceId']}")
                
                # 打印IP分数异常的节点
                if abnormal_score_nodes:
                    print("\nIP分数异常节点列表:")
                    for node in abnormal_score_nodes:
                        print(f"- IP: {node['ipAddress']}, 设备ID: {node['deviceId']}, IP分数: {node['ipScore']}")
                
                return result_data, total_uptime, len(online_nodes), len(offline_nodes)
            else:
                print(f"API请求失败: {response.status}")
                return None, 0, 0, 0
                
    except Exception as e:
        print(f"获取数据失败: {str(e)}")
        return None, 0, 0, 0

async def fetch_profile_data(session, api_token):
    """获取用户资料数据"""
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
        "authorization": f"{api_token}",
        "content-type": "application/json",
        "user-agent": get_random_user_agent()
    }
    
    try:
        async with session.get(PROFILE_API_URL, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return data.get('result', {}).get('data', {})  # 直接返回 result.data 内容
            else:
                error_text = await response.text()
                raise Exception(f"获取个人资料失败: {response.status}, 错误信息: {error_text}")
    except Exception as e:
        print(f"获取个人资料失败: {str(e)}")
        raise

def compare_states(previous, current):
    """比较两个状态的差异"""
    changes = []
    
    for node in current:
        node_id = node['_id']
        prev_node = next((n for n in previous if n['_id'] == node_id), None)
        
        if not prev_node:
            changes.append(f"新增节点: {node['pubKey']}")
            continue
            
        # 检查连接状态变化
        if node['isConnected'] != prev_node['isConnected']:
            status = "上线" if node['isConnected'] else "离线"
            changes.append(f"节点 {node['pubKey']} {status}")
            
        # 检查奖励变化
        if node['totalReward'] != prev_node['totalReward']:
            reward_diff = node['totalReward'] - prev_node['totalReward']
            changes.append(f"节点 {node['pubKey']} 总奖励变化: +{reward_diff}")
            
        if node['todayReward'] != prev_node['todayReward']:
            reward_diff = node['todayReward'] - prev_node['todayReward']
            changes.append(f"节点 {node['pubKey']} 今日奖励变化: +{reward_diff}")
            
        # 检查sessions变化
        if len(node['sessions']) != len(prev_node['sessions']):
            changes.append(f"节点 {node['pubKey']} sessions数量变化: {len(prev_node['sessions'])} -> {len(node['sessions'])}")
    
    return changes

async def monitor_nodes(interval, webhook_url, use_proxy, proxy_url, always_notify=False):
    """监控节点状态"""
    while True:
        try:
            # 为每个token创建独立的监控任务，每个任务使用独立的session
            tasks = []
            for token_config in TOKENS_CONFIG:
                task = monitor_token_with_session(
                    token_config=token_config,
                    webhook_url=webhook_url,
                    use_proxy=use_proxy,
                    proxy_url=proxy_url
                )
                tasks.append(task)
            
            # 并发执行所有token的监控任务
            await asyncio.gather(*tasks)
            
        except Exception as e:
            print(f"监控过程出错: {str(e)}")
            await asyncio.sleep(5)
            continue
            
        await asyncio.sleep(interval)

async def monitor_token_with_session(token_config, webhook_url, use_proxy, proxy_url):
    """为每个token创建独立的session进行监控"""
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        await monitor_single_token(
            session=session,
            token_config=token_config,
            webhook_url=webhook_url,
            use_proxy=use_proxy,
            proxy_url=proxy_url
        )

def format_point(point_value):
    """将积分格式化为 x,xxx.x pt 格式"""
    point = float(point_value) / 100000  # 转换为pt单位
    return f"{point:,.1f} pt"

def build_status_message(current_state, profile_data, show_detail, online_nodes, expected_online):
    """构建状态消息"""
    adjusted_time = datetime.now() + timedelta(hours=TIME_OFFSET)
    timestamp = adjusted_time.strftime('%Y-%m-%d %H:%M:%S')
    
    total_today = sum(node['today'] for node in current_state)
    
    # 获取积分信息
    point_data = profile_data.get('point', {})
    total_point = format_point(point_data.get('total', 0))
    balance_point = format_point(point_data.get('balance', 0))
    referral_point = format_point(point_data.get('referral', 0))
    
    # 获取节点信息
    node_data = profile_data.get('node', {})
    
    # 添加节点状态警告
    status_emoji = "✅" if online_nodes >= expected_online else "⚠️"
    
    message_lines = [
        f"{status_emoji} 【Gradient状态报告】",
        f"时间: {timestamp}\n",
        f"💎 积分统计:",
        f"  • 账号: {profile_data.get('name')}",
        f"  • 总积分: {total_point}",
        f"  • 可用积分: {balance_point}",
        f"  • 推荐奖励: {referral_point}",
        f"\n🖥️ 节点统计:",
        f"  • 预期活跃: {expected_online}",
        f"  • 在线节点: {online_nodes}",
        f"  • 今日积分: {format_point(total_today)}"
    ]
    
    if show_detail:
        message_lines.extend(["\n📝 节点详情:"])
        for node in current_state:
            status_emoji = "✅" if node['connect'] else "❌"
            message_lines.extend([
                f"  • {node['name']} {status_emoji}",
                f"    积分: {format_point(node['point'])} / 今日: {format_point(node['today'])}",
                f"    延迟: {node['latency']}ms / 位置: {node['location']['country']}-{node['location']['place']}"
            ])
    
    return "\n".join(message_lines)

if __name__ == "__main__":
    asyncio.run(monitor_nodes(
        interval=INTERVAL,
        webhook_url=WEBHOOK_URL,
        use_proxy=USE_PROXY,
        proxy_url=PROXY_URL,
        always_notify=ALWAYS_NOTIFY  # 添加这个参数来启用始终通知
    ))
