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
    APP_NAME,
    SHOW_DETAIL
)

# 新增：随机延迟函数
async def random_delay():
    """生成随机延迟时间（3-10秒）"""
    delay = random.uniform(3, 100)
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
    
    # 检查重复IP
    ip_count = {}
    duplicate_ips = set()
    for node in result_data:
        ip = node.get('ipAddress')
        if ip:
            ip_count[ip] = ip_count.get(ip, 0) + 1
            if ip_count[ip] > 1:
                duplicate_ips.add(ip)
    
    # 在消息中添加重复IP警告
    if duplicate_ips:
        message_lines.extend([
            f"\n⚠️ 重复IP警告 ({len(duplicate_ips)}):"
        ])
        for ip in duplicate_ips:
            duplicate_nodes = [
                node for node in result_data 
                if node.get('ipAddress') == ip
            ]
            message_lines.append(f"  • IP: {ip}")
            for node in duplicate_nodes:
                message_lines.append(f"    设备ID: {node.get('deviceId')}")
    
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
                
                # 获取原始节点数据
                raw_nodes = data.get('result', {}).get('data', {}).get('data', [])
                if SHOW_DETAIL:
                    print(f"获取到的节点数量: {len(raw_nodes)}")
                    print(f"节点数据结构: {raw_nodes}")
                
                if raw_nodes:
                    try:
                        # 提取每个节点的关键信息
                        result_data = [extract_node_info(node) for node in raw_nodes]
                        
                        # 检查重复IP
                        ip_count = {}
                        duplicate_ips = set()
                        for node in result_data:
                            ip = node.get('ipAddress')
                            if ip:
                                ip_count[ip] = ip_count.get(ip, 0) + 1
                                if ip_count[ip] > 1:
                                    duplicate_ips.add(ip)
                        
                        # 如果发现重复IP，打印警告
                        if duplicate_ips:
                            print("\n⚠️ 发现重复IP:")
                            for ip in duplicate_ips:
                                duplicate_nodes = [
                                    node for node in result_data 
                                    if node.get('ipAddress') == ip
                                ]
                                print(f"IP {ip} 被以下设备使用:")
                                for node in duplicate_nodes:
                                    print(f"  - 设备ID: {node.get('deviceId')}")
                        
                        # 使用提取的数据计算统计信息
                        total_uptime = sum(node['totalUptime'] for node in result_data)
                        online_nodes = [node for node in result_data if node['ipScore'] > 0 and node['isConnected']]
                        offline_nodes = [node for node in result_data if node['ipScore'] == 0 or not node['isConnected']]
                        
                        print(f"\n总在线时间: {total_uptime}秒")
                        print(f"在线节点数量: {len(online_nodes)}")
                        print(f"离线节点数量: {len(offline_nodes)}")
                        
                        return result_data, total_uptime, len(online_nodes), len(offline_nodes)
                    except Exception as e:
                        print(f"处理数据时出错: {str(e)}")
                        raise
                else:
                    print("未获取到节点数据")
                    return None, 0, 0, 0
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

def format_timestamp(timestamp_str, time_offset=8):
    """
    将UTC时间戳转换为本地时间
    
    Args:
        timestamp_str: UTC时间字符串 (例如: '2024-12-02T03:19:01.000Z')
        time_offset: 时区偏移量,默认为东八区(+8)
    """
    if not timestamp_str:
        return "未知"
        
    try:
        # 解析UTC时间字符串
        utc_time = datetime.strptime(timestamp_str.replace('Z', ''), '%Y-%m-%dT%H:%M:%S.%f')
        # 添加时区偏移
        local_time = utc_time + timedelta(hours=time_offset)
        # 格式化输出
        return local_time.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        print(f"时间转换错误: {e}")
        return timestamp_str

def extract_node_info(node, time_offset=8):
    """提取节点的关键信息"""
    info = {
        # 基础信息
        'deviceId': node.get('deviceId'),
        'name': node.get('name'),
        'type': node.get('type'),
        
        # 状态信息
        'ipAddress': node.get('ipAddress'),
        'ipScore': node.get('ipScore', 0),
        'isConnected': node.get('isConnected', False),
        'totalUptime': node.get('totalUptime', 0),
        'lastConnectedAt': node.get('lastConnectedAt'),
        
        # 地理位置
        'countryCode': node.get('countryCode'),
        
        # 性能指标
        'multiplier': node.get('multiplier', 1),
        'totalPoints': node.get('totalPoints', 0)
    }
    
    # 格式化日志输出
    log_message = [
        f"节点信息摘要:",
        f"  设备ID: {info['deviceId'][:8]}...",
        f"  名称: {info['name']}",
        f"  状态: {'🟢 在线' if info['isConnected'] else '🔴 离线'}",
        f"  IP: {info['ipAddress']} (评分: {info['ipScore']}) {'' if info['ipScore'] == 100 else '🔴'}",
        f"  地区: {info['countryCode']}",
        f"  倍率: {info['multiplier']}x",
        f"  积分: {info['totalPoints']}",
        f"  运行时间: {info['totalUptime']}秒",
        f"  最后连接: {format_timestamp(info['lastConnectedAt'], time_offset)}"
    ]
    
    print("\n".join(log_message))
    return info

if __name__ == "__main__":
    asyncio.run(monitor_nodes(
        interval=INTERVAL,
        webhook_url=WEBHOOK_URL,
        use_proxy=USE_PROXY,
        proxy_url=PROXY_URL,
        always_notify=ALWAYS_NOTIFY  # 添加这个参数来启用始终通知
    ))
