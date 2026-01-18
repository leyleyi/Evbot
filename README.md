# Evbot - Python 版本

## 功能特性

- 支持抖音视频/图集解析
- 支持快手视频/图集解析
- 自动去除水印
- 支持私聊和群组使用
- 智能处理大文件（超过50MB自动发送封面+直链）
- 图集自动分批发送（每批最多10张）

## 安装步骤

### 1. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 2. 配置文件

编辑 `config.toml` 文件，填入你的 Telegram Bot Token：

```toml
[telegram]
api_token = "YOUR_BOT_TOKEN_HERE"
```

### 3. 运行程序

```bash
python main.py
```

## 使用方法

### 私聊使用

直接发送视频链接给机器人即可

### 群组使用

1. 将机器人添加到群组
2. 在群组中发送视频链接

## 支持的平台

- 抖音 (douyin)
- 快手 (kuaishou)

## 主要功能

### 视频处理

-发送封面图+下载链接

### 图集处理

- 自动识别图集类型
- 每批最多发送10张图片
- 多批次自动间隔1秒发送
- 发送失败的图片会提供URL链接

## 技术特点

- 异步处理，支持并发请求
- 用户级别的任务锁，防止重复请求
- 完善的错误处理和日志记录
- 自动日志轮转（基于文件大小）

## 注意事项

1. 请确保 Bot Token 的安全性，不要泄露
2. 日志文件会自动管理，无需手动清理
3. 确保网络连接稳定，以便访问视频平台

## 依赖说明

- `python-telegram-bot`: Telegram Bot API 封装库
- `requests`: HTTP 请求库
- `toml`: TOML 配置文件解析库
