# 自动化投资系统

基于 React + FastAPI + SQLite 的个人投资管理系统。

## 功能特性

- **资产管理**: 支持股票、基金、加密货币等多资产类型管理
- **交易记录**: 记录买入/卖出交易，自动计算持仓成本和盈亏
- **市场数据**: 集成akshare获取A股实时行情和历史K线数据
- **策略引擎**: 支持均线交叉、RSI、MACD、布林带、KDJ等技术指标策略
- **信号审批**: 策略生成交易信号后需用户审批，审批通过自动记录交易
- **策略回测**: 基于历史数据模拟策略表现，输出回测报告
- **仪表盘**: 可视化展示总资产、持仓分布、盈亏情况

## 项目结构

```
autoInst/
├── backend/                 # Python后端
│   ├── database/           # 数据库模块
│   │   ├── models.py       # 数据模型定义
│   │   └── init_db.py      # 数据库初始化
│   ├── routers/            # API路由
│   │   ├── assets.py       # 资产管理API
│   │   ├── transactions.py # 交易记录API
│   │   ├── market.py       # 市场数据API
│   │   ├── strategies.py   # 策略管理API
│   │   ├── portfolio.py    # 投资组合API
│   │   ├── accounts.py     # 账户管理API
│   │   └── backtest.py     # 回测API
│   ├── services/           # 业务逻辑
│   │   ├── market_service.py    # 市场数据服务
│   │   ├── strategy_service.py  # 策略引擎服务
│   │   └── backtest_service.py  # 回测服务
│   └── main.py             # FastAPI应用入口
├── frontend/               # React前端
│   └── src/
│       ├── api/            # API调用封装
│       ├── pages/          # 页面组件
│       │   ├── Dashboard.jsx   # 仪表盘
│       │   ├── Assets.jsx      # 资产管理
│       │   ├── Transactions.jsx # 交易记录
│       │   ├── Strategies.jsx  # 策略管理
│       │   ├── Backtest.jsx    # 策略回测
│       │   └── Accounts.jsx    # 账户管理
│       ├── App.jsx         # 主应用
│       └── main.jsx        # 入口文件
├── data/                   # 数据存储目录
├── requirements.txt        # Python依赖
├── package.json            # Node依赖
├── vite.config.js          # Vite配置
└── start.ps1               # 一键启动脚本

```

## 环境要求

- Python 3.8+
- Node.js 18+
- conda环境: virtua

## 快速开始

### 方式一：一键启动（推荐）

```powershell
# 在项目根目录运行
.\start.ps1
```

### 方式二：手动启动

1. **安装Python依赖**
```bash
conda activate virtua
pip install -r requirements.txt
```

2. **安装Node依赖**
```bash
cd frontend
npm install
```

3. **启动后端服务**
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

4. **启动前端服务**
```bash
cd frontend
npm run dev
```

## 访问地址

- 前端界面: http://localhost:3000
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs

## 使用说明

### 1. 添加资产
- 进入"资产管理"页面
- 点击"搜索添加"通过关键词搜索A股股票
- 或点击"手动添加"直接输入资产信息
- 点击"更新数据"获取历史K线数据

### 2. 记录交易
- 进入"交易记录"页面
- 点击"添加交易"
- 选择资产、交易类型、日期、数量、价格等信息

### 3. 配置策略
- 进入"策略管理"页面
- 点击"添加策略"
- 选择策略类型并配置参数
- 点击"执行"运行策略生成信号

### 4. 审批信号
- 策略执行后会生成交易信号
- 在信号列表中点击"同意"或"拒绝"
- 同意后会自动创建交易记录

### 5. 策略回测
- 进入"策略回测"页面
- 选择资产、策略、时间段
- 点击"开始回测"查看回测报告

## 数据库表结构

- `assets`: 资产基本信息
- `transactions`: 交易记录
- `market_data`: 行情数据
- `strategies`: 策略配置
- `signals`: 交易信号
- `portfolios`: 组合快照
- `accounts`: 账户信息

## 技术栈

**后端**
- FastAPI: 高性能Web框架
- SQLAlchemy: ORM
- akshare: A股数据接口
- pandas/numpy: 数据处理

**前端**
- React 18: UI框架
- Ant Design: UI组件库
- Recharts: 图表库
- Axios: HTTP客户端
- Vite: 构建工具

## 注意事项

1. 首次运行会自动创建SQLite数据库
2. akshare接口有调用频率限制，请勿频繁请求
3. 数据库文件存储在 `data/investment.db`
4. 所有数据本地存储，注意定期备份
