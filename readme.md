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
- 🐳 支持 Docker 部署

## 安装

### 方法一: 本地部署

1. 克隆仓库:
    ```bash
    git clone https://github.com/yourusername/grass-monitor.git
    cd grass-monitor
    ```

2. 安装依赖:
    ```bash
    pip install -r requirements.txt
    ```

3. 创建并配置 `.env` 文件:
    ```
    # 用户Token配置
    USER1_TOKEN=your_token_1
    USER2_TOKEN=your_token_2
    USER3_TOKEN=your_token_3
    USER4_TOKEN=your_token_4
    USER5_TOKEN=your_token_5

    # 企业微信机器人配置
    WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=

    ```

4. 编辑 `config.py` 文件，根据需要修改以下参数:
    - `PROXY_URL`: 代理服务器地址（可选）
    - `USE_PROXY`: 是否启用代理
    - `INTERVAL`: 检查间隔时间（秒）
    - `TIME_OFFSET`: 时区偏移（小时）
    - `ALWAYS_NOTIFY`: 是否始终发送通知
    - `SHOW_DETAIL`: 是否显示详细日志

### 方法二: Docker 部署

1. 创建并配置 `.env` 文件（同上）

2. 使用 Docker Compose 启动:
    ```bash
    docker-compose up -d
    ```

Docker 环境变量说明:
- `TZ`: 时区设置，默认为 Asia/Shanghai
- `PYTHONUNBUFFERED`: Python 输出不缓冲
- `IS_DOCKER`: Docker 环境标识
- `HTTP_PROXY/HTTPS_PROXY`: 代理服务器配置

## 使用方法

### 本地运行:
```bash
python main.py
```

### Docker 运行:
```bash
# 查看日志
docker logs -f grass-monitor

# 重启服务
docker-compose restart

# 停止服务
docker-compose down
```

## 通知示例

监控程序会通过企业微信机器人发送如下格式的通知:
```
🔍 【Grass 用户报告】
⏰ 时间: 2024-03-21 10:00:00
👤 账户: MyNode (username)
📊 节点统计:
• 总节点数: 10
• 在线节点: 8
• 离线节点: 2
• 总运行时间: 5天3小时20分钟
📊 当前收益统计:
Epoch 12:
• 总积分: 15,000(+500)
• 推荐奖励: 1,000(+100)
• 运行时间: 2天5小时30分钟
Epoch 11:
• 总积分: 12,000
• 推荐奖励: 800
• 运行时间: 1天20小时45分钟
📊 上次收益统计:
Epoch 12:
• 总积分: 14,500
• 推荐奖励: 900
• 运行时间: 2天1小时15分钟
Epoch 11:
• 总积分: 12,000
• 推荐奖励: 800
• 运行时间: 1天20小时45分钟
```

## 日志输出示例

程序运行时会在控制台输出详细的节点状态日志:

```
响应状态码: 200
获取到的节点数量: 20

🟢 1.2.3.4(100分) JP 2x 节点 477f6fd0... | 
🟢 1.2.3.4(0分) NZ 1x 节点 22a1f34a... | 
🔴 1.2.3.4(0分) JP 1x 节点 ea23c494... | 
```

日志说明:
- 🟢: 在线节点
- 🔴: 离线节点
- IP分数: 括号内的数字(0-100)
- 地区: 国家/地区代码
- 倍率: 1x/2x等
- 节点ID: 节点的唯一标识符(已省略部分)

## 配置说明

### 环境变量 (.env)

- `USERx_TOKEN`: Grass 账号的 token
- `WEBHOOK_URL`: 企业微信机器人的 webhook 地址

### 应用配置 (config.py)

- `PROXY_URL`: 代理服务器地址，默认为 http://localhost:7890
- `USE_PROXY`: 是否启用代理，默认为 False
- `INTERVAL`: 检查间隔时间（秒），默认为 86400（24小时）
- `TIME_OFFSET`: 时区偏移（小时），默认为 0
- `ALWAYS_NOTIFY`: 是否始终发送通知，默认为 True
- `SHOW_DETAIL`: 是否显示详细日志，默认为 True

## 注意事项

- 请妥善保管你的 token，不要泄露给他人
- 建议使用代理以提高连接稳定性
- 可以根据需要调整检查间隔时间
- 如遇到问题，请查看程序输出的日志信息
- Docker 部署时注意配置正确的时区和代理设置

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 更新日志

### v1.0.0
- 初始版本发布
- 支持多账号监控
- 添加 Docker 部署支持
- 企业微信机器人通知集成
