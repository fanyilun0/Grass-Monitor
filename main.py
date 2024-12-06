import asyncio
import aiohttp
from datetime import datetime, timedelta
import random
import json
import logging

# 导入配置
from config import (
    API_URL,  # 节点列表API
    PROFILE_API_URL,  # 个人资料API
    EPOCH_EARNINGS_API_URL,  # 收益API
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

# 配置logging
def setup_logging():
    """配置日志格式和级别"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)

# 获取logger实例
logger = setup_logging()

# 全局字典用于缓存上次的epoch收益数据
previous_epoch_data_cache = {}

# 新增：随机延迟函数
async def random_delay():
    """生成随机延迟时间（10-20秒）"""
    delay = random.uniform(10, 20)
    logger.info(f"等待 {delay:.2f} 秒...")
    await asyncio.sleep(delay)

async def monitor_single_token(session, token_config, webhook_url, use_proxy, proxy_url):
    """监控单个token的节点状态和epoch收益"""
    try:
        logger.info(f"{'='*50}")
        logger.info(f"开始检查Token: {token_config['name']}")
        logger.info(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 获取用户资料
        logger.info("正在获取用户资料...")
        profile_data = await fetch_profile_data(session, token_config['token'])
        username = profile_data.get('username', '未知用户')
        logger.info(f"用户名: {username}")
        
        # 获取当前Epoch收益数据
        logger.info("正在获取Epoch收益数据...")
        current_epoch_data = await fetch_epoch_earnings(session, token_config['token'])
        
        # 获取上次的Epoch收益数据
        previous_epoch_data = previous_epoch_data_cache.get(token_config['token'], [])
        
        # 更新缓存为当前查询结果
        previous_epoch_data_cache[token_config['token']] = current_epoch_data
        
        # 按epoch分组统计数据
        current_epoch_stats = group_epoch_data(current_epoch_data)
        previous_epoch_stats = group_epoch_data(previous_epoch_data)
        
        # 检查是否有收益变化
        has_earnings_changed = should_send_epoch_notification(current_epoch_stats, previous_epoch_stats)
        if has_earnings_changed:
            logger.info("\n检测到Epoch收益变化!")
        
        # 获取节点数据
        logger.info("正在获取节点状态...")
        result_data, total_uptime, online_count, offline_count = await fetch_nodes_data(
            session=session,
            api_url=API_URL,
            api_token=token_config['token']
        )
        
        if not result_data:
            logger.error(f"获取节点数据失败，跳过此token: {token_config['name']}")
            return
            
        # 判断是否需要发送通知
        should_notify = ALWAYS_NOTIFY or has_earnings_changed
        
        if should_notify:
            logger.info("构建通知消息...")
            message = build_combined_message(
                token_name=token_config['name'],
                username=username,
                current_epoch_stats=current_epoch_stats,
                previous_epoch_stats=previous_epoch_stats,
                result_data=result_data,
                total_uptime=total_uptime,
                online_count=online_count,
                offline_count=offline_count,
                has_earnings_changed=has_earnings_changed
            )
            
            if message:
                logger.info(" 发送通知消息...")
                await send_message_async(webhook_url, message, use_proxy, proxy_url)
                logger.info("✅ 消息发送成功")
        else:
            logger.info("无变化，跳过通知")
            
    except Exception as e:
        logger.error(f"❌ 监控Token {token_config['name']} 时出错: {str(e)}")
        
    finally:
        logger.info(f"检查完成: {token_config['name']}")
        logger.info('='*50 + '\n')

def group_epoch_data(epoch_data):
    """按epoch分组统计数据"""
    epoch_stats = {}
    for entry in epoch_data:
        epoch_stats[entry['epochName']] = {
            'totalPoints': entry['totalPoints'],
            'rewardPoints': entry['rewardPoints'],
            'referralPoints': entry['referralPoints'],
            'totalUptime': entry['totalUptime'],
            'modified': entry['modified']
        }
    return epoch_stats

def should_send_epoch_notification(current_stats, previous_stats):
    """判断是否需要发送epoch收益通知"""
    for epoch_name, current in current_stats.items():
        previous = previous_stats.get(epoch_name, {})
        if current.get('modified') != previous.get('modified'):
            return True
    return False

def build_combined_message(token_name, username, current_epoch_stats, previous_epoch_stats, 
                         result_data, total_uptime, online_count, offline_count, has_earnings_changed):
    """构建合并后的用户信息消息"""
    adjusted_time = datetime.now() + timedelta(hours=TIME_OFFSET)
    timestamp = adjusted_time.strftime('%Y-%m-%d %H:%M:%S')
    
    # 基础信息
    message_lines = [
        f"🔍 【{APP_NAME} 状态报告】",
        f"⏰ 时间: {timestamp}",
        f"👤 账户: {token_name} ({username})",
        
        # 节点状态摘要
        f"\n📡 节点状态:",
        f"  • 总节点数: {len(result_data)}",
        f"  • 在线节点: {online_count}",
        f"  • 离线节点: {offline_count}",
        f"  • 总运行时间: {format_uptime(total_uptime)}"
    ]
    
    # 只在有收益变化时显示详细的收益信息
    if has_earnings_changed:
        message_lines.append("\n💰 收益变化:")
        for epoch_name, stats in current_epoch_stats.items():
            # 计算当前的总积分
            current_epoch_points = stats['totalPoints'] + stats['rewardPoints']
            current_referral_points = stats['referralPoints']
            
            # 获取上一次的数据
            previous_stats = previous_epoch_stats.get(epoch_name, {})
            previous_epoch_points = previous_stats.get('totalPoints', 0) + previous_stats.get('rewardPoints', 0)
            previous_referral_points = previous_stats.get('referralPoints', 0)
            
            # 计算增量
            epoch_points_increase = current_epoch_points - previous_epoch_points
            referral_points_increase = current_referral_points - previous_referral_points
            
            if epoch_points_increase > 0 or referral_points_increase > 0:
                message_lines.extend([
                    f"\n{epoch_name}:",
                    f"  • 总积分: {current_epoch_points:,} (+{epoch_points_increase:,})",
                    f"  • 推荐奖励: {current_referral_points:,} (+{referral_points_increase:,})",
                    f"  • 运行时间: {format_uptime(stats['totalUptime'])}"
                ])
    else:
        message_lines.append("\n💡 无收益变化")
    
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
                logger.info("Message sent successfully!")
            else:
                logger.error(f"Failed to send message: {response.status}, {await response.text()}")


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
            logger.info(f"响应状态码: {response.status}")
            
            if response.status == 403:
                logger.error(f"Token认证失败，请检查token是否有效: {api_token}")
                return None, 0, 0, 0
            elif response.status == 200:
                data = await response.json()
                
                # 获取原始节点数据
                raw_nodes = data.get('result', {}).get('data', {}).get('data', [])
                if SHOW_DETAIL:
                    logger.info(f"获取到的节点数量: {len(raw_nodes)}")
                
                if raw_nodes:
                    try:
                        # 提取每个节点的关键信息并排序
                        result_data = [extract_node_info(node) for node in raw_nodes]
                        
                        # 按状态和IP分数排序
                        result_data.sort(key=lambda x: (-x['isConnected'], -x['ipScore'], x['ipAddress']))
                        
                        # 打印排序后的节点信息
                        logger.info("\n节点状态列表:")
                        for node in result_data:
                            log_message = (
                                f"{'🟢' if node['isConnected'] else '🔴'} "
                                f"{node['ipAddress']}({node['ipScore']}分) "
                                f"{node['countryCode']} {node['multiplier']}x "
                                f"节点 {node['deviceId'][:8]}..."
                            )
                            logger.info(log_message)
                        
                        # 检查在线节点的重复IP
                        online_nodes = [
                            node for node in result_data 
                            if node['ipScore'] > 0 and node['isConnected']
                        ]
                        
                        ip_count = {}
                        duplicate_ips = set()
                        for node in online_nodes:
                            ip = node.get('ipAddress')
                            if ip:
                                ip_count[ip] = ip_count.get(ip, 0) + 1
                                if ip_count[ip] > 1:
                                    duplicate_ips.add(ip)
                        
                        # 如果发现重复IP，打印警告
                        if duplicate_ips:
                            logger.warning("\n⚠️ 发现在线节点重复IP:")
                            for ip in duplicate_ips:
                                duplicate_nodes = [
                                    node for node in online_nodes 
                                    if node.get('ipAddress') == ip
                                ]
                                logger.warning(f"IP {ip} 被以下在线设备使用:")
                                for node in duplicate_nodes:
                                    logger.warning(f"  - 设备ID: {node.get('deviceId')}")
                        
                        # 计算统计信息
                        total_uptime = sum(node['totalUptime'] for node in result_data)
                        online_count = len(online_nodes)
                        offline_count = len(result_data) - online_count
                        
                        logger.info(f"节点统计:")
                        logger.info(f"• 总在线时间: {format_uptime(total_uptime)}")
                        logger.info(f"• 在线节点数: {online_count}")
                        logger.info(f"• 离线节点数: {offline_count}")
                        
                        return result_data, total_uptime, online_count, offline_count
                        
                    except Exception as e:
                        logger.error(f"处理数据时出错: {str(e)}")
                        raise
                else:
                    logger.error("未获取到节点数据")
                    return None, 0, 0, 0
            else:
                logger.error(f"API请求失败: {response.status}")
                return None, 0, 0, 0
                
    except Exception as e:
        logger.error(f"获取数据失败: {str(e)}")
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
        logger.error(f"获取个人资料失败: {str(e)}")
        raise

async def fetch_epoch_earnings(session, api_token):
    """获取epoch收益数据"""
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
        "authorization": f"{api_token}",
        "content-type": "application/json",
        "user-agent": get_random_user_agent()
    }
    
    try:
        async with session.get(EPOCH_EARNINGS_API_URL, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return data.get('result', {}).get('data', {}).get('data', [])
            else:
                error_text = await response.text()
                raise Exception(f"获取Epoch收益数据失败: {response.status}, 错误信息: {error_text}")
    except Exception as e:
        logger.error(f"获取Epoch收益数据失败: {str(e)}")
        raise

def build_epoch_stats_message(epoch_data, username):
    """构建epoch统计消息"""
    adjusted_time = datetime.now() + timedelta(hours=TIME_OFFSET)
    timestamp = adjusted_time.strftime('%Y-%m-%d %H:%M:%S')
    
    message_lines = [
        f"🏆 【{APP_NAME} Epoch收益报告】",
        f"⏰ 时间: {timestamp}",
        f"👤 账户: {username}\n",
        f"📊 收益统计:"
    ]
    
    for epoch_name, stats in epoch_data.items():
        total_points = stats['totalPoints'] + stats['rewardPoints']
        message_lines.extend([
            f"\n{epoch_name}:",
            f"  • 总积分: {total_points:,}",
            f"  • 推荐奖励: {stats['referralPoints']:,}",
            f"  • 运行时间: {format_uptime(stats['totalUptime'])}"
        ])
    
    return "\n".join(message_lines)

async def monitor_nodes(interval, webhook_url, use_proxy, proxy_url, always_notify=False):
    """监控节点状态"""
    iteration = 1
    while True:
        try:
            print(f"\n开始第 {iteration} 轮检查...")
            
            # 串行执行每个token的监控
            for token_config in TOKENS_CONFIG:
                await monitor_token_with_session(
                    token_config=token_config,
                    webhook_url=webhook_url,
                    use_proxy=use_proxy,
                    proxy_url=proxy_url
                )
                # 在每个token检查之间添加随机延迟
                await random_delay()
                
            print(f"第 {iteration} 轮检查完成\n")
            iteration += 1
            
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

def extract_node_info(node):
    """提取节点的关键信息"""
    return {
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

if __name__ == "__main__":
    asyncio.run(monitor_nodes(
        interval=INTERVAL,
        webhook_url=WEBHOOK_URL,
        use_proxy=USE_PROXY,
        proxy_url=PROXY_URL,
        always_notify=ALWAYS_NOTIFY  # 添加这个参数来启用始终通知
    ))

