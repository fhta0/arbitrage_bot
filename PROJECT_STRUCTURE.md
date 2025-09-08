# 多币种跨市场套利机器人项目结构

## 📁 目录结构

```
arbitrage_bot/
├── main.py                          # 主程序入口
├── bidirectional_arbitrage_strategy.py  # 双向套利策略实现
├── requirements.txt                 # Python依赖包列表
├── README.md                       # 项目说明文档
├── RELEASE_NOTES.md                # 版本发布说明
├── MVP_SUMMARY.md                  # MVP版本总结
├── PROJECT_STRUCTURE.md            # 项目结构说明
├── CLEANUP_PLAN.md                 # 清理计划文档
├── config/                         # 配置文件目录
│   └── config.yaml                 # 主配置文件
├── engine/                         # 交易引擎模块
│   └── trading_engine.py           # 模拟交易引擎实现
├── exchanges/                      # 交易所接口模块
│   ├── base.py                     # 交易所基类
│   ├── okx.py                      # OKX交易所模拟实现
│   └── xt.py                       # XT交易所模拟实现
├── strategies/                     # 交易策略模块
│   ├── multi_asset_strategy.py     # 多资产策略
│   └── spread.py                   # 价差策略
├── docs/                           # 项目文档目录
│   ├── DYNAMIC_PAIRS_IMPROVEMENT.md  # 动态交易对改进文档
│   └── FINAL_REPORT.md             # 最终报告
└── logs/                           # 日志文件目录
    └── arbitrage_bot.log           # 运行日志文件
```

## 📄 核心文件说明

### 主程序文件
- **main.py**: 程序主入口，包含机器人主类和运行逻辑
- **bidirectional_arbitrage_strategy.py**: 实现双向套利策略，支持两个方向的跨市场套利

### 配置文件
- **config/config.yaml**: 系统配置文件，包含交易所参数、交易参数、日志配置等

### 核心模块
- **engine/trading_engine.py**: 交易引擎，负责模拟交易执行和账户管理
- **exchanges/base.py**: 交易所接口基类
- **exchanges/okx.py**: OKX交易所模拟实现
- **exchanges/xt.py**: XT交易所模拟实现
- **strategies/multi_asset_strategy.py**: 多资产套利策略
- **strategies/spread.py**: 价差分析策略

### 文档文件
- **README.md**: 项目使用说明和功能介绍
- **RELEASE_NOTES.md**: 版本发布说明和功能详情
- **MVP_SUMMARY.md**: MVP版本开发总结
- **docs/DYNAMIC_PAIRS_IMPROVEMENT.md**: 动态交易对功能改进说明
- **docs/FINAL_REPORT.md**: 项目最终报告

## 🚀 运行说明

### 安装依赖
```bash
pip install -r requirements.txt
```

### 启动程序
```bash
python main.py
```

### 停止程序
按 `Ctrl+C` 组合键停止程序运行

## 📊 功能特性

1. **双向套利策略**: 支持OKX做空+XT做多和XT做空+OKX做多两个方向
2. **多币种支持**: 支持BTC/USDT、ETH/USDT、BNB/USDT、ADA/USDT、DOT/USDT等主流交易对
3. **实时监控**: 使用Rich库构建的现代化终端仪表盘，无闪烁显示
4. **动态交易对**: 自动检测交易所新增交易对并纳入套利范围
5. **风险管理**: 完善的账户管理和风险控制机制
6. **错误处理**: 增强的异常处理和实时错误监控
7. **日志记录**: 详细的交易和系统日志记录

## 🧪 测试验证

所有核心功能均已通过测试验证：
- ✅ 多币种套利功能测试
- ✅ 价格数据获取和价差计算准确性验证
- ✅ 交易执行和账户余额更新验证
- ✅ 双向套利策略完整测试
- ✅ 实时仪表盘显示效果测试

## 📝 注意事项

1. 当前版本为模拟交易版本，不涉及真实资金
2. 交易所API为模拟实现，不连接真实交易所
3. 所有交易记录和收益统计都保存在内存中
4. 这是一个教育和测试项目，请勿用于实际投资决策