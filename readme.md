# Grass-Monitor

一个用于监控 Grass 节点状态的自动化工具。

## 功能特点

- 🔄 自动监控多个账号的节点状态
- 📊 统计节点在线情况和运行时间
- 🚨 检测异常节点和 IP 分数
- 📱 企业微信机器人通知
- 🌐 支持代理配置
- ⏰ 可配置检查间隔
- 🔒 安全的 token 管理

## 安装

1. 克隆仓库:
```bash
git clone https://github.com/yourusername/grass-monitor.git
cd grass-monitor
```

2. 安装依赖:
```bash
pip install -r requirements.txt
```

3. 编辑 `config.py` 文件，配置以下参数:
- `TOKENS_CONFIG`: 添加你的账号 token 和名称
- `WEBHOOK_URL`: 企业微信机器人 webhook 地址
- `PROXY_URL`: 代理服务器地址（可选）
- `USE_PROXY`: 是否启用代理
- `INTERVAL`: 检查间隔时间（秒）
- `TIME_OFFSET`: 时区偏移（小时）
- `ALWAYS_NOTIFY`: 是否始终发送通知

## 使用方法

运行监控程序:
```bash
python main.py
```

## 通知示例

监控程序会通过企业微信机器人发送如下格式的通知:
```
🔍 【Grass节点状态报告】
⏰ 时间: 2024-03-21 10:00:00
👤 账户: MyNode (username)
📊 节点统计:
• 总节点数: 10
• 在线节点: 8
• 离线节点: 2
• 总运行时间: 5天3小时20分钟
❌ 离线节点 (2):
• IP: 1.2.3.4
设备ID: device_1
• IP: 5.6.7.8
设备ID: device_2
⚠️ IP分数异常节点 (1):
• IP: 9.10.11.12
设备ID: device_3
IP分数: 85
```

## 注意事项

- 请妥善保管你的 token，不要泄露给他人
- 建议使用代理以提高连接稳定性
- 可以根据需要调整检查间隔时间
- 如遇到问题，请查看程序输出的日志信息

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
