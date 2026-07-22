# ETF Trader - 项目上下文（2026-07-22）

## 项目概述

ETF 交易决策系统，基于 Tkinter GUI，集成同花顺持仓读取、技术指标计算、LLM 决策。

**路径**：`E:\etf-trader`  
**入口**：`gui.py`，PyInstaller 打包为 `E:\etf-trader\dist\gui.exe`  
**桌面快捷方式**：`ETF Trader` → `E:\etf-trader\dist\gui.exe`

---

## 核心架构

| 模块 | 路径 | 职责 |
|------|------|------|
| GUI | `gui.py` | Tkinter 主界面，参数输入、持仓管理、分析触发、结果展示 |
| 行情 | `backend/data_fetcher.py` | baostock 历史日线 + akshare 实时行情补充 |
| 因子 | `backend/factor_engine.py` | 多因子技术指标计算流水线 |
| LLM 决策 | `backend/llm_decision.py` | 构造 prompt、调用 LLM、解析 JSON 结果 |
| 持仓读取 | `backend/position_fetcher.py` | 同花顺 easytrader 持仓 + 资金快照 |
| 配置 | `backend/config_manager.py` | JSON 配置读写，冻结模式自动迁到 %APPDATA%/etf-trader |
| 打包 | `gui.spec` | PyInstaller 规格文件，含 akshare file_fold 数据 |

## LLM 决策输入来源

分析时 `decide()` 接收以下信息：
- **技术面**：`factor_engine.run_factor_pipeline()` 输出的趋势/信号/因子数组
- **持仓**：同花顺实际持仓（代码、成本、数量），`position_fetcher.format_positions_for_prompt()`
- **资金**：同花顺账户余额，`position_fetcher.format_balance_for_prompt()`
- **板块舆情**：从 `gui.py` 中 `_load_sentiment()` 读取外部 txt 文件，作为 LLM 额外情绪参考
- **周期**：用户输入的 1-365 天
- **风险档位**：conservative / standard / aggressive

## 板块舆情联动

- GUI 顶部「舆情文件」输入框，可手动输入或点击「浏览...」选择 txt 文件
- 默认值 `E:/video2txt`（旧目录模式兼容：如果路径是目录，自动 glob 最新 `批次总结_*.txt`）
- 配置键：`sentiment_dir`，保存在 `settings.json`，失焦/回车/浏览自动保存
- LLM prompt 中已有 `{sentiment}` 占位符，为 emtpy 时显示"无板块舆情信息"

---

## 今天新增/修复清单

### 2026-07-22 下午

12. **GitHub 仓库创建**  
    提交 `2f1b10b`（以及前序若干）  
    - 仓库地址：`https://github.com/cementbarrier/ETF-Trader`
    - 13 个 commits 已全部推送
    - README.md、LICENSE (MIT)、.gitignore 已补充

### 2026-07-22 上午

1. **持仓读取增强**（之前已修，回补上下文）
   - 空仓时 `get_balance_from_ths()` 读取资金
   - `_normalize_balance()` 兼容 dict/DataFrame，字段映射 `可用金额` → `available`
   - GUI 新增可用资金/总资产输入框

2. **LLM 输出中文化**（之前已修）
   - buy→买入, sell→卖出, hold→观望
   - bullish→看涨, bearish→看跌, neutral→震荡

3. **LLM 决策输出增强**（之前已修）
   - 新增 `entry_zone`、`exit_zone`、`position_ratio`、`reasoning` 字段
   - GUI 树形分区展示（┌├│└ 制表符）

4. **reasoning 换行修复**（之前已修）
   - Prompt 层明确要求每条独占一行
   - GUI 正则兜底拆分编号文本

5. **周期改为输入天数**（之前已修）
   - `short`/`long` 下拉框 → Spinbox 1-365 天

6. **行情数据补充实时行情**（之前已修）
   - `_fetch_realtime_spot()` 用 akshare `fund_etf_spot_em()` 补充当日实时数据
   - baostock 缺今日数据时自动追加

7. **EXE 打包修复：akshare calendar.json 缺失**  
   提交 `6a9d68c`  
   - 根因：PyInstaller 未包含 `akshare/file_fold/calendar.json`
   - 修复：`gui.spec` 的 `datas` 中添加 akshare file_fold 目录

8. **EXE 打包修复：tqdm stderr NoneType 崩溃**  
   提交 `83f1a10`  
   - 根因：窗口化 EXE 中 `sys.stderr = None`，akshare 内 tqdm 写 stderr 抛异常
   - 修复：`data_fetcher.py` 首行 `os.environ.setdefault("TQDM_DISABLE", "1")`

9. **板块舆情联动**  
   提交 `6c10b18`  
   - 新增 `_load_sentiment()` 自动读取批次总结文件
   - 调用 `decide()` 时传入 `sentiment` 参数

10. **舆情目录改为可配置**  
    提交 `9336e28` / `ac7d0f2`  
    - GUI 新增输入框，手动输入或浏览选择文件夹

11. **改为直接选 txt 文件**  
    提交 `19c8a4e`  
    - 浏览按钮改用 `askopenfilename`，过滤 *.txt
    - `_load_sentiment()` 直接读文件路径，兼容旧目录模式

---

## 构建与部署

### 开发模式运行
```powershell
python E:\etf-trader\gui.py
```

### 构建 EXE
```powershell
cd E:\etf-trader
Get-Process -Name "gui" -ErrorAction SilentlyContinue | Stop-Process -Force
# 用 delete 工具清理 build 和 dist/gui.exe
python -m PyInstaller gui.spec --distpath dist --workpath build --clean --noconfirm
# 验证：exe 时间戳 > 源码时间戳
```

### EXE 输出
- 单文件：`E:\etf-trader\dist\gui.exe`（~50MB）
- 配置：冻结模式自动迁至 `%APPDATA%\etf-trader\settings.json`

### Python 环境
- 路径：`D:\Program Files\Tencent\Marvis\MarvisAgent\1.0.1100.349\runtime\python311\python.exe`
- PyInstaller：6.21.0（admin 模式运行会报 DEPRECATION 警告但构建正常）

---

## 已知问题 / 待办

1. ~~无远程 Git 仓库~~ — 已创建 `https://github.com/cementbarrier/ETF-Trader` 并推送 13 个 commits
2. **akshare 实时行情稳定性** — 依赖 akshare `fund_etf_spot_em()` 接口，外部依赖不可控
3. **同花顺 easytrader 依赖** — 需要同花顺客户端运行中才能读取持仓

---

## 相关项目

- `E:\stock-tool` — 股票分析工具，产出视频批次总结
- `E:\video2txt` — 批次总结输出目录
