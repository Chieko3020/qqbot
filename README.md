# QQ Bot — 基于 Webhook 的 QQ 机器人

- QQ 官方 Webhook 机器人，运行在 127.0.0.1:3005，接收 QQ 消息并返回回复
- 确定性强过滤：白名单指令 + 正则匹配，不使用 LLM 做安全约束
- 内置 MC 服务器监控（状态/性能/TPS/内存/日志/备份）
- 支持 Luna AI 聊天（通过 DeepSeek API），内联键盘交互
- 支持语音消息上传、音乐搜索播放（通过 Enhanced API）
- 安全：ed25519 签名验证 + msg_id 去重 + 50K token 日配额 + 频控
- 开发环境：Python 3.12

## 项目简介

接收 QQ 官方 Webhook 回调，解析用户消息，根据白名单指令匹配分发到对应的处理函数。消息处理全部本地完成（不依赖 LLM），仅 Luna 聊天功能调用 DeepSeek API。音乐功能通过本地 Enhanced API（:3000）获取。

## 技术栈

| 组件 | 选型 |
|------|------|
| 运行时 | Python 3.12 |
| HTTP 服务 | http.server (标准库) |
| 签名验证 | cryptography (ed25519) |
| LLM 后端 | DeepSeek API (可通过 ai-gateway) |

## 项目结构

```
qqbot/
├── filter-proxy.py      # 主程序（893 行）
├── daily_counter.py     # 日配额计数器
├── bot_config.json      # 配置（本地，不提交）
├── document/            # QQ API 文档（本地）
└── .env                 # 环境变量（本地）
```

## 配置

| 项 | 位置 | 说明 |
|----|------|------|
| APP_ID / APP_SECRET | filter-proxy.py | QQ Bot 凭证 |
| DEEPSEEK_KEY / DEEPSEEK_URL | filter-proxy.py | LLM API |
| LISTEN_PORT | filter-proxy.py | 监听端口 (3005) |

## 指令

| 指令 | 功能 |
|------|------|
| 状态 / 性能 / TPS | MC 服务器实时状态 |
| 在线人数 / 内存 | 服务器资源监控 |
| 日志 / 备份 | 日志查看和备份管理 |
| luna | AI 聊天（调用 DeepSeek） |
| 音乐 | 音乐搜索和播放 |
| 帮助 | 显示所有指令 |
