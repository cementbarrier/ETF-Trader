# ETF Trader

基于多因子技术分析 + LLM 大模型决策的 ETF 交易辅助系统，支持同花顺持仓联动和板块舆情注入。

## 功能

- **多因子技术分析**：MA / RSI / MACD / 布林带 / 量价背离等因子流水线
- **LLM 智能决策**：接入大模型，综合技术面、持仓、资金、板块舆情输出买入/卖出/观望建议
- **同花顺联动**：自动读取同花顺真实持仓和账户资金
- **板块舆情注入**：支持外部 txt 文件作为 LLM 情绪参考
- **结果自动保存**：每次分析结果自动落盘为 txt 文件

## 界面

![GUI](docs/screenshot.png)

## 安装

```bash
git clone https://github.com/cementbarrier/ETF-Trader.git
cd ETF-Trader
pip install -r requirements.txt
```

额外依赖（GUI 模式）：
```bash
pip install easytrader pywinauto baostock akshare Pillow
```

## 使用

### GUI 模式（推荐）

```bash
python gui.py
```

填入 LLM API Key，输入 ETF 代码和分析参数，点击「开始分析」。

### 命令行模式

```bash
python run.py 510050 60 standard
```

参数：`ETF代码 周期天数 风险档位(conservative/standard/aggressive)`

## 项目结构

```
ETF-Trader/
├── gui.py                    # Tkinter 主界面
├── run.py                    # 命令行入口
├── requirements.txt          # 核心依赖
├── gui.spec                  # PyInstaller 打包配置
├── backend/
│   ├── config_manager.py     # JSON 配置读写
│   ├── data_fetcher.py       # baostock + akshare 行情获取
│   ├── factor_engine.py      # 多因子技术指标计算
│   ├── llm_client.py         # LLM API 客户端
│   ├── llm_decision.py       # LLM 决策 prompt 与解析
│   └── position_fetcher.py   # 同花顺持仓读取
├── config/
│   └── settings.json          # 用户配置（API Key、参数等）
└── docs/
    └── screenshot.png
```

## 配置

首次运行会自动创建 `config/settings.json`：

| 键 | 说明 | 默认值 |
|---|---|---|
| `llm_api_key` | LLM API Key | — |
| `default_etf` | 默认 ETF 代码 | 510050 |
| `default_days` | 默认分析周期（天） | 60 |
| `risk_profile` | 风险档位 | standard |
| `sentiment_dir` | 板块舆情文件路径 | E:/video2txt |
| `output_dir` | 结果保存目录 | E:/etf-trader/output |

## 打包为 EXE

```bash
pip install pyinstaller
pyinstaller gui.spec --clean --noconfirm
```

输出：`dist/gui.exe`（单文件，约 50MB）

## 依赖

- Python 3.10+
- [akshare](https://github.com/akfamily/akshare) — 实时行情
- [baostock](http://baostock.com/) — 历史日线
- [easytrader](https://github.com/shidenggui/easytrader) — 同花顺自动化
- [PyInstaller](https://pyinstaller.org/) — EXE 打包

## License

MIT
