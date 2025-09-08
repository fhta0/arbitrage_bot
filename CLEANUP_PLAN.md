# 项目清理和整理计划

## 需要保留的核心文件

### 主程序文件
- `main.py` - 主程序入口
- `bidirectional_arbitrage_strategy.py` - 双向套利策略
- `requirements.txt` - 依赖包列表
- `README.md` - 项目说明文档
- `RELEASE_NOTES.md` - 发布说明
- `MVP_SUMMARY.md` - MVP总结

### 配置文件
- `config/config.yaml` - 配置文件

### 核心模块
- `engine/trading_engine.py` - 交易引擎
- `exchanges/base.py` - 交易所基类
- `exchanges/okx.py` - OKX交易所实现
- `exchanges/xt.py` - XT交易所实现
- `strategies/multi_asset_strategy.py` - 多资产策略
- `strategies/spread.py` - 价差策略

## 需要删除的测试文件

### 单功能测试脚本
- `test_bidirectional_strategy.py`
- `test_complete_bidirectional.py`
- `test_dynamic_pairs.py`
- `test_multi_asset.py`
- `test_multi_positions_display.py`
- `test_new_listings.py`
- `test_position_closing.py`
- `test_price_data.py`
- `test_rich_dashboard.py`
- `test_sol_trading.py`
- `test_trade_execution.py`
- `test_xt_short_okx_long.py`
- `comprehensive_health_check.py`
- `system_health_check.py`
- `explain_arbitrage_logic.py`
- `verify_arbitrage_logic.py`
- `demo_dynamic_pairs.py`

### 临时文件和备份
- `main.py.backup`
- `main.py.working`
- `*.pyc` files (Python编译缓存)
- `__pycache__` directories

## 需要归档的文档文件
- `DYNAMIC_PAIRS_IMPROVEMENT.md`
- `FINAL_REPORT.md`
- `MVP_COMPLETE`
- `TODO.md`

## 整理后的目录结构
```
arbitrage_bot/
├── README.md
├── RELEASE_NOTES.md
├── MVP_SUMMARY.md
├── requirements.txt
├── main.py
├── bidirectional_arbitrage_strategy.py
├── config/
│   └── config.yaml
├── engine/
│   └── trading_engine.py
├── exchanges/
│   ├── base.py
│   ├── okx.py
│   └── xt.py
├── strategies/
│   ├── multi_asset_strategy.py
│   └── spread.py
├── docs/
│   ├── DYNAMIC_PAIRS_IMPROVEMENT.md
│   └── FINAL_REPORT.md
└── logs/
    └── arbitrage_bot.log
```