# QQ Bot — 基于 Webhook 的 QQ 机器人

- QQ 官方 Webhook 机器人，运行在 127.0.0.1:4001（nginx 反代），接收消息并确定性强过滤后回复
- 模块化设计：core/chat/mc 包结构
- 内置 MC 服务器监控（状态/性能/TPS/内存/日志/备份）+ RCON + 自动备份
- 支持 Luna AI 聊天（DeepSeek，通过 ai-gateway），内联键盘交互
- 支持音乐搜索播放（Enhanced API + 语音上传）
- 安全：ed25519 签名 + msg_id 去重 + 滑动窗口频控 + 正则过滤器 + 50K 日配额
- 凭据全部通过环境变量注入（systemd EnvironmentFile → .env），源码零硬编码
- 开发环境：Python 3.12

## 项目简介

QQ Bot 后端服务。接收 QQ 官方 Webhook 回调，ed25519 验证后根据白名单指令分发到对应处理函数。MC 监控通过 RCON + systemctl 实现，零外部脚本依赖。聊天和音乐功能通过本地 API 转发。

## 技术栈

| 组件 | 选型 |
|------|------|
| 运行时 | Python 3.12 |
| HTTP 服务 | http.server (标准库) |
| 签名验证 | cryptography (ed25519) |
| RCON | socket + struct (标准库) |
| LLM | DeepSeek v4-flash (通过 ai-gateway) |

## 项目结构

```
qqbot/
├── src/
│   ├── main.py             #   入口：HTTP Handler + 告警线程
│   ├── daily_counter.py    #   日配额计数器
│   ├── core/
│   │   ├── config.py       #   配置 / 日志 / 频控 / _mc_cfg
│   │   ├── qq_client.py    #   QQ Bot API (token/消息/语音)
│   │   ├── security.py     #   过滤器 / 反注入 / URL 移除
│   │   └── handlers.py     #   指令分发
│   ├── chat/
│   │   ├── luna.py         #   AI 聊天
│   │   └── music.py        #   音乐搜索播放
│   └── mc/
│       └── server.py       #   MC 监控 / RCON / 备份
├── config/
│   └── bot_config.json     # 指令开关 + MC 服务器配置（不入库）
├── .env.example            # 环境变量模板，复制为 .env 填入凭据
├── README.md
└── .gitignore
```

## 编译和运行

```bash
pip install cryptography
cp .env.example .env        # 填入 QQ_APP_ID / QQ_APP_SECRET
python -m src.main
# Listening on http://127.0.0.1:4001
```

生产环境通过 systemd 启动（EnvironmentFile 指向 .env），nginx 将 Webhook 回调反代到 4001 端口。

## 配置

### 环境变量（.env）

| 变量 | 必填 | 说明 |
|------|------|------|
| `QQ_APP_ID` | 是 | QQ 开放平台机器人 AppID |
| `QQ_APP_SECRET` | 是 | QQ 开放平台机器人 AppSecret（webhook 签名 + 换取 access_token） |
| `DEEPSEEK_KEY` | 否 | DeepSeek 访问密钥（走 ai-gateway 时可留空） |
| `LISTEN_HOST` | 否 | 监听地址，默认 `127.0.0.1` |
| `LISTEN_PORT` | 否 | 监听端口，默认 `4001`（nginx 反代指向） |
| `DEEPSEEK_URL` | 否 | LLM 上游地址，默认 `http://127.0.0.1:4000/v1/chat/completions` |

⚠ 凭据只从环境变量读取，源码不包含任何密钥。`.env` 已被 .gitignore 忽略，严禁提交。

### config/bot_config.json
```json
{
  "commands": { "状态": true, "luna": true, ... },
  "mc_server": {
    "name": "MC Server",
    "service_name": "mcserver",
    "server_dir": "/home/ubuntu/minecraft",
    "rcon_password": ""
  }
}
```

| 字段 | 说明 |
|------|------|
| `commands.*` | 指令开关（true/false） |
| `mc_server.name` | 服务器显示名称 |
| `mc_server.service_name` | systemd 服务名 |
| `mc_server.server_dir` | 服务器根目录 |
| `mc_server.rcon_password` | RCON 密码（可选，从 server.properties 自动读取） |

## 指令

| 指令 | 功能 |
|------|------|
| 状态 / 性能 / TPS | 服务器运行状态 |
| 在线人数 / 内存 | 资源监控 |
| 日志 / 备份 | 日志和备份管理 |
| luna | AI 聊天（例: `luna 你好`） |
| 音乐 | 音乐搜索和播放 |
| 帮助 | 完整菜单 |
