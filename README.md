# A股智能分析助手

移动端A股分析网页应用。输入股票代码，AI自动结合实时行情、K线走势和全网资讯，预测3日/5日/7日/1个月内的看涨看跌趋势，并给出详细多维度分析依据。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 获取 DeepSeek API Key

1. 访问 [platform.deepseek.com](https://platform.deepseek.com) 注册账号
2. 在 API Keys 页面创建密钥
3. 复制密钥

### 3. 设置环境变量并启动

**Windows:**
```bash
set DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
python app.py
```

**Mac/Linux:**
```bash
export DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
python app.py
```

### 4. 打开浏览器

访问 `http://127.0.0.1:5050`

### 5. 登录

- 账户名：`zjjai1`
- 密码：`123456`

## 部署到公网（Railway）

1. 将项目上传到 GitHub
2. 注册 [railway.app](https://railway.app)（GitHub登录）
3. 新建项目 → Deploy from GitHub repo
4. 在 Settings → Variables 中添加：`DEEPSEEK_API_KEY` = 你的密钥
5. Railway 自动构建部署，获得公开URL

## 功能

- 📊 顶部滚动行情条：15只热门A股实时价格
- 🔍 股票分析：输入任意A股代码查询
- 🤖 AI深度分析：技术面/消息面/资金面/行业面/政策面
- 📈 K线走势图：90日日线 + MA5/MA10/MA20均线
- 📰 全网资讯：实时抓取相关新闻
- 📋 历史记录：localStorage自动保存最近查询

## 技术栈

- 后端：Python Flask
- 前端：HTML/CSS/JS（单文件）
- 数据：东方财富公开API
- AI：DeepSeek API

## 费用

DeepSeek API 约 ¥0.01/次查询，每月200次约 ¥2。

## 免责声明

本工具AI预测仅供参考，不构成任何投资建议。股市有风险，投资需谨慎。
