"""
ETF 交易决策系统 - tkinter GUI
加持仓管理：自动读取同花顺 / 手动输入
"""
import sys
import os
import threading
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog

from backend.config_manager import get_setting, set_setting, get_risk_params
from backend.data_fetcher import fetch_etf_daily
from backend.factor_engine import run_factor_pipeline
from backend.llm_decision import decide
from backend.position_fetcher import get_account_snapshot, format_positions_for_prompt, format_balance_for_prompt


def _load_sentiment() -> str:
    """加载板块舆情总结文件，用于 LLM 决策的外部情绪参考"""
    file_path = get_setting("sentiment_dir", "E:/video2txt")
    if not file_path:
        return ""
    p = Path(file_path)
    # 若是目录则回退旧逻辑：glob 最新的批次总结
    if p.is_dir():
        candidates = sorted(p.glob("批次总结_*.txt"), reverse=True)
        if not candidates:
            return ""
        p = candidates[0]
    if not p.exists() or not p.is_file():
        return ""
    try:
        return p.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def _log(msg: str):
    if hasattr(_log, "widget") and _log.widget:
        _log.widget.insert(tk.END, msg + "\n")
        _log.widget.see(tk.END)


def _save_api_key(*_):
    key = api_var.get().strip()
    if key:
        set_setting("llm_api_key", key)
        status.config(text="API Key 已保存")
    else:
        status.config(text="请填写 API Key")


def _read_positions_from_ths():
    """弹出进度窗口，后台读取同花顺持仓"""
    btn_pos.config(state="disabled", text="读取中...")

    # ── 进度弹窗 ──
    popup = tk.Toplevel(root)
    popup.title("读取持仓")
    popup.geometry("320x120")
    popup.resizable(False, False)
    popup.transient(root)
    popup.grab_set()

    # 居中
    popup.update_idletasks()
    rx, ry = root.winfo_x(), root.winfo_y()
    rw, rh = root.winfo_width(), root.winfo_height()
    pw, ph = 320, 120
    popup.geometry(f"+{rx + (rw - pw) // 2}+{ry + (rh - ph) // 2}")

    frame = ttk.Frame(popup, padding=15)
    frame.pack(fill="both", expand=True)

    ttk.Label(frame, text="正在连接同花顺，请稍候...").pack(pady=(0, 10))

    bar = ttk.Progressbar(frame, mode="indeterminate", length=260)
    bar.pack()
    bar.start(15)

    detail_var = tk.StringVar(value="初始化连接...")
    ttk.Label(frame, textvariable=detail_var, foreground="gray").pack(pady=(8, 0))

    def _do():
        root.after(0, lambda: detail_var.set("连接同花顺，读取持仓与资金..."))
        result = get_account_snapshot()
        root.after(0, lambda: _on_done(result, popup))

    threading.Thread(target=_do, daemon=True).start()


def _on_done(result: dict, popup: tk.Toplevel):
    """读取完成，关闭弹窗并处理结果"""
    popup.grab_release()
    popup.destroy()
    btn_pos.config(state="normal", text="从同花顺读取")

    if not result.get("success"):
        messagebox.showerror("读取失败", result.get("error", "未知错误"))
        status.config(text="读取持仓失败")
        return

    positions = result.get("positions", [])
    balance = result.get("balance", {})

    # 填入持仓
    if positions:
        _fill_positions(positions)

    # 显示资金
    if balance:
        avail = balance.get("available", 0)
        total = balance.get("total_asset", 0)
        bal_var.set(f"{avail:.2f}" if avail else "")
        total_var.set(f"{total:.2f}" if total else "")

        parts = []
        if avail:
            parts.append(f"可用资金 {avail:.2f}")
        if total:
            parts.append(f"总资产 {total:.2f}")
        msg = "、".join(parts)
        if positions:
            status.config(text=f"已读取 {len(positions)} 条持仓 | {msg}")
        else:
            status.config(text=f"空仓 | {msg}")
            messagebox.showinfo("读取结果", f"未持有任何仓位。\n{msg}")
    else:
        if positions:
            status.config(text=f"已读取 {len(positions)} 条持仓")
        else:
            messagebox.showinfo("提示", "未读取到任何持仓数据。\n请确认同花顺账户中确实持有股票/基金。")
            status.config(text="未读取到持仓，请手动输入")


def _fill_positions(positions: list):
    """将持仓数据填入 GUI 输入框"""
    for row_vars in pos_rows:
        for var in row_vars:
            var.set("")

    for i, p in enumerate(positions[:4]):
        if i < len(pos_rows):
            pos_rows[i][0].set(p.get("code", ""))
            pos_rows[i][1].set(str(p.get("cost", "")))
            pos_rows[i][2].set(str(int(p.get("qty", 0))))

    status.config(text=f"已读取 {len(positions)} 条持仓")


def _get_manual_account() -> tuple[list[dict], dict]:
    """从 GUI 输入框获取手动输入的持仓和资金。
    返回 (positions, balance)
    """
    positions = []
    for row_vars in pos_rows:
        code = row_vars[0].get().strip()
        if not code:
            continue
        try:
            cost = float(row_vars[1].get().strip() or 0)
            qty = int(float(row_vars[2].get().strip() or 0))
        except ValueError:
            continue
        if qty <= 0:
            continue
        positions.append({"code": code, "cost": cost, "qty": qty, "name": ""})

    balance = {}
    try:
        v = bal_var.get().strip()
        if v:
            balance["available"] = float(v)
    except ValueError:
        pass
    try:
        v = total_var.get().strip()
        if v:
            balance["total_asset"] = float(v)
    except ValueError:
        pass

    return positions, balance


def _run_analysis():
    btn.config(state="disabled", text="分析中...")

    symbol = etf_var.get().strip()
    days = days_var.get()
    risk = risk_var.get()
    use_positions = pos_var.get() == "1"

    _save_api_key()

    try:
        _log(f"=== {symbol} {days}天 {risk} ===")

        # 持仓 + 资金
        positions = []
        account_balance = {}
        if use_positions:
            positions, account_balance = _get_manual_account()
            if not positions and not account_balance:
                _log("[账户] 尝试从同花顺自动读取...")
                result = get_account_snapshot()
                if result.get("success"):
                    positions = result.get("positions", [])
                    account_balance = result.get("balance", {})
                else:
                    _log(f"[账户] 读取失败: {result.get('error', '')}")
            if positions:
                _log(f"[持仓] 共 {len(positions)} 条: {', '.join(p['code'] for p in positions)}")
            else:
                _log("[持仓] 空仓")
            if account_balance:
                avail = account_balance.get("available")
                total = account_balance.get("total_asset")
                parts = []
                if avail:
                    parts.append(f"可用 {avail:.2f}")
                if total:
                    parts.append(f"总资产 {total:.2f}")
                _log(f"[资金] {', '.join(parts)}")
            else:
                _log("[资金] 无数据，将仅基于行情分析")
        else:
            _log("[账户] 未纳入决策，仅基于行情分析")

        _log("[1/3] 获取行情...")

        max_bars = max(days, 30)
        df = fetch_etf_daily(symbol, count=max_bars)
        if df is None or df.empty:
            _log(f"错误: 无法获取 {symbol} 行情数据")
            return

        _log(f"  获取 {len(df)} 条数据, 最新 {df['date'].iloc[-1].strftime('%Y-%m-%d')}")

        _log("[2/3] 计算技术指标...")
        risk_params = get_risk_params(risk)
        factor = run_factor_pipeline(df, risk_params)
        _log(f"  价格: {factor['price']}  趋势: {factor['trend']}")
        _log(f"  信号: {', '.join(factor['signals']) or '无'}")

        # 加载板块舆情
        sentiment = _load_sentiment()
        if sentiment:
            _log(f"  板块舆情: 已加载 ({len(sentiment)} 字)")
        else:
            _log("  板块舆情: 无外部数据，纯技术面分析")

        _log("[3/3] LLM 决策...")

        # 格式化持仓和资金为 prompt 文本
        pos_text = format_positions_for_prompt(positions) if positions else ""
        bal_text = format_balance_for_prompt(account_balance) if account_balance else ""
        result = decide(symbol, factor, days=days, risk_profile=risk, positions_text=pos_text, balance_text=bal_text, sentiment=sentiment)

        if "error" in result:
            _log(f"错误: {result['error']}")
            return

        action_en = result.get("action", "hold")
        action_map = {"buy": "买入", "sell": "卖出", "hold": "观望"}
        trend_en = result.get("trend", "neutral")
        trend_map = {"bullish": "看涨", "bearish": "看跌", "neutral": "震荡"}

        # ── 概览 ──
        _log("")
        _log("┌─ 决策概览")
        _log(f"│  方向: {action_map.get(action_en, action_en)}　趋势: {trend_map.get(trend_en, trend_en)}　置信度: {result.get('confidence', 'N/A')}　当前价: {factor['price']}")

        # ── 操作区间 ──
        if result.get("entry_zone") or result.get("exit_zone") or result.get("position_ratio"):
            _log("├─ 操作建议")
            if result.get("entry_zone"):
                _log(f"│  买入区间: {result['entry_zone']}")
            if result.get("exit_zone"):
                _log(f"│  卖出区间: {result['exit_zone']}")
            if result.get("position_ratio"):
                _log(f"│  仓位建议: {result['position_ratio']}")

        # ── 风控 ──
        _log("├─ 风控参数")
        _log(f"│  止损: {result.get('stop_loss_price')}　止盈: {result.get('take_profit_price')}")

        # ── 依据（多行） ──
        if result.get("reasoning"):
            _log("├─ 决策依据")
            raw = result["reasoning"].replace("\r", "")
            lines = [l.strip() for l in raw.split("\n") if l.strip()]
            # 如果只有一行且包含编号模式（1. 2. 或 - 开头），智能拆分
            if len(lines) == 1:
                import re
                parts = re.split(r'(?<!\d)(?=\d+\.\s|-\s)', lines[0])
                lines = [p.strip() for p in parts if p.strip()]
            for line in lines:
                _log(f"│  {line}")

        # ── 总建议 ──
        if result.get("position_advice"):
            _log("└─ " + result["position_advice"])
        else:
            _log("└─" + "─" * 3)

        _log("─" * 40)

    except Exception as e:
        _log(f"异常: {e}")
    finally:
        btn.config(state="normal", text="开始分析")


def on_run():
    threading.Thread(target=_run_analysis, daemon=True).start()


def _clear_positions():
    for row_vars in pos_rows:
        for var in row_vars:
            var.set("")
    status.config(text="持仓已清空")


# ── 界面 ──
root = tk.Tk()
root.title("ETF 交易决策")
root.geometry("700x750")
root.resizable(True, True)

bal_var = tk.StringVar()
total_var = tk.StringVar()

top = ttk.Frame(root, padding=10)
top.pack(fill="x")

# Row 0: API Key
ttk.Label(top, text="API Key:").grid(row=0, column=0, sticky="w", padx=(0, 5))
api_var = tk.StringVar(value=get_setting("llm_api_key", ""))
api_entry = ttk.Entry(top, textvariable=api_var, width=55, show="*")
api_entry.grid(row=0, column=1, columnspan=6, sticky="ew")
api_entry.bind("<FocusOut>", _save_api_key)
api_entry.bind("<Return>", _save_api_key)

# Row 1: 参数
ttk.Label(top, text="ETF代码:").grid(row=1, column=0, sticky="w", padx=(0, 5), pady=(8, 0))
etf_var = tk.StringVar(value=get_setting("default_etf", "510050"))
etf_entry = ttk.Entry(top, textvariable=etf_var, width=10)
etf_entry.grid(row=1, column=1, sticky="w", pady=(8, 0))

ttk.Label(top, text="天数:").grid(row=1, column=2, sticky="w", padx=(15, 5), pady=(8, 0))
days_var = tk.IntVar(value=int(get_setting("default_days", 60)))
days_sb = ttk.Spinbox(top, textvariable=days_var, from_=1, to=365, width=6)
days_sb.grid(row=1, column=3, sticky="w", pady=(8, 0))

ttk.Label(top, text="档位:").grid(row=1, column=4, sticky="w", padx=(15, 5), pady=(8, 0))
risk_var = tk.StringVar(value=get_setting("risk_profile", "standard"))
risk_cb = ttk.Combobox(top, textvariable=risk_var, values=["conservative", "standard", "aggressive"], state="readonly", width=10)
risk_cb.grid(row=1, column=5, sticky="w", pady=(8, 0))

btn = ttk.Button(top, text="开始分析", command=on_run)
btn.grid(row=1, column=6, padx=(15, 0), sticky="w", pady=(8, 0))

# Row 2: 舆情文件
ttk.Label(top, text="舆情文件:").grid(row=2, column=0, sticky="w", padx=(0, 5), pady=(6, 0))
sent_var = tk.StringVar(value=get_setting("sentiment_dir", "E:/video2txt"))
sent_frame = ttk.Frame(top)
sent_frame.grid(row=2, column=1, columnspan=6, sticky="ew", pady=(6, 0))
sent_entry = ttk.Entry(sent_frame, textvariable=sent_var)
sent_entry.pack(side="left", fill="x", expand=True)
sent_entry.bind("<FocusOut>", lambda e: set_setting("sentiment_dir", sent_var.get().strip()))
sent_entry.bind("<Return>", lambda e: set_setting("sentiment_dir", sent_var.get().strip()))


def _browse_sentiment_file():
    f = filedialog.askopenfilename(
        initialdir=str(Path(sent_var.get()).parent) if sent_var.get() else "E:/",
        title="选择舆情总结文件",
        filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
    )
    if f:
        sent_var.set(f)
        set_setting("sentiment_dir", f)


sent_btn = ttk.Button(sent_frame, text="浏览...", command=_browse_sentiment_file, width=6)
sent_btn.pack(side="left", padx=(5, 0))

# ── 持仓区 ──
pos_frame = ttk.LabelFrame(root, text="持仓管理", padding=8)
pos_frame.pack(fill="x", padx=10, pady=(5, 0))

# 开关 + 按钮
pos_bar = ttk.Frame(pos_frame)
pos_bar.pack(fill="x")

pos_var = tk.StringVar(value="1")
pos_cb = ttk.Checkbutton(pos_bar, text="纳入决策", variable=pos_var, onvalue="1", offvalue="0")
pos_cb.pack(side="left")

btn_pos = ttk.Button(pos_bar, text="从同花顺读取", command=_read_positions_from_ths)
btn_pos.pack(side="left", padx=(10, 0))

btn_clear = ttk.Button(pos_bar, text="清空", command=_clear_positions, width=5)
btn_clear.pack(side="left", padx=(5, 0))

ttk.Label(pos_bar, text="（或手动输入下方表格）", foreground="gray").pack(side="left", padx=(10, 0))

# 持仓表格头
col_frame = ttk.Frame(pos_frame)
col_frame.pack(fill="x", pady=(8, 0))
ttk.Label(col_frame, text="ETF代码", width=12).grid(row=0, column=0)
ttk.Label(col_frame, text="成本价", width=12).grid(row=0, column=1)
ttk.Label(col_frame, text="持有数量(份)", width=16).grid(row=0, column=2)

# 4 行持仓输入
pos_rows = []
for i in range(4):
    row_frame = ttk.Frame(pos_frame)
    row_frame.pack(fill="x", pady=(2, 0))
    code_var = tk.StringVar()
    cost_var = tk.StringVar()
    qty_var = tk.StringVar()
    ttk.Entry(row_frame, textvariable=code_var, width=12).grid(row=0, column=0, padx=(0, 4))
    ttk.Entry(row_frame, textvariable=cost_var, width=12).grid(row=0, column=1, padx=(0, 4))
    ttk.Entry(row_frame, textvariable=qty_var, width=16).grid(row=0, column=2)
    pos_rows.append((code_var, cost_var, qty_var))

# 资金输入行
bal_row = ttk.Frame(pos_frame)
bal_row.pack(fill="x", pady=(8, 0))
ttk.Label(bal_row, text="可用资金:").pack(side="left")
ttk.Entry(bal_row, textvariable=bal_var, width=14).pack(side="left", padx=(5, 0))
ttk.Label(bal_row, text="总资产:").pack(side="left", padx=(20, 0))
ttk.Entry(bal_row, textvariable=total_var, width=14).pack(side="left", padx=(5, 0))
ttk.Label(bal_row, text='（手动填写或点击"从同花顺读取"自动获取）', foreground="gray").pack(side="left", padx=(10, 0))

# 输出区
output = scrolledtext.ScrolledText(root, font=("Consolas", 10), wrap="word", state="normal")
output.pack(fill="both", expand=True, padx=10, pady=(8, 10))
_log.widget = output

# 状态栏
status_text = "API Key 已就绪" if get_setting("llm_api_key", "") else "请填写 API Key"
status = ttk.Label(root, text=status_text, relief="sunken", anchor="w", padding=(5, 2))
status.pack(fill="x", side="bottom")

if __name__ == "__main__":
    root.mainloop()
