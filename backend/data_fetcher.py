"""
行情数据获取：支持多数据源切换（baostock / akshare），可选 token 认证
"""
import os
os.environ.setdefault("TQDM_DISABLE", "1")
from typing import Optional
from datetime import datetime, timedelta
import pandas as pd


# ── 数据源配置 ──

DATA_SOURCES = {
    "baostock": {
        "label": "baostock (免费，偶有网络波动)",
        "needs_token": False,
    },
    "akshare": {
        "label": "akshare (免费，东方财富数据)",
        "needs_token": False,
    },
}

_DEFAULT_SOURCE = "baostock"


def get_data_source():
    """从配置文件读取当前数据源"""
    from backend.config_manager import get_setting
    src = get_setting("data_source", _DEFAULT_SOURCE)
    if src not in DATA_SOURCES:
        src = _DEFAULT_SOURCE
    return src


def get_data_source_token():
    """读取数据源 token（仅付费源需要）"""
    from backend.config_manager import get_setting
    return get_setting("data_source_token", "")


# ── baostock 实现 ──

def _ensure_baostock_login():
    import baostock as bs
    lg = bs.login()
    if lg.error_code != '0':
        raise RuntimeError(f"baostock 登录失败: {lg.error_msg}")


def _symbol_to_code(symbol: str) -> str:
    s = symbol.strip()
    if s.startswith("5") or s.startswith("6"):
        return f"sh.{s}"
    else:
        return f"sz.{s}"


def _fetch_baostock_daily(symbol: str, count: int = 200) -> Optional[pd.DataFrame]:
    """baostock 日 K 线"""
    import baostock as bs
    _ensure_baostock_login()
    code = _symbol_to_code(symbol)
    today = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=count * 2)).strftime("%Y-%m-%d")

    rs = bs.query_history_k_data_plus(
        code, "date,open,high,low,close,volume",
        start_date=start, end_date=today,
        frequency="d", adjustflag="2"
    )
    if rs.error_code != '0':
        raise RuntimeError(f"baostock 查询失败: {rs.error_msg}")

    rows = []
    while rs.next():
        rows.append(rs.get_row_data())
    if not rows:
        return None

    df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
    df["date"] = pd.to_datetime(df["date"])
    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["volume"] = pd.to_numeric(df.get("volume", 0), errors="coerce")
    return df.sort_values("date").tail(count).reset_index(drop=True).dropna(subset=["close"])


def _fetch_baostock_minute(symbol: str, period: str = "60", count: int = 200) -> Optional[pd.DataFrame]:
    """baostock 分钟 K 线"""
    import baostock as bs
    _ensure_baostock_login()
    code = _symbol_to_code(symbol)
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=count)).strftime("%Y-%m-%d")

    rs = bs.query_history_k_data_plus(
        code, "date,time,open,high,low,close,volume",
        start_date=start, end_date=end,
        frequency=period, adjustflag="2"
    )
    if rs.error_code != '0':
        raise RuntimeError(f"baostock 分钟查询失败: {rs.error_msg}")

    rows = []
    while rs.next():
        rows.append(rs.get_row_data())
    if not rows:
        return None

    df = pd.DataFrame(rows, columns=["date", "time", "open", "high", "low", "close", "volume"])
    df["date"] = pd.to_datetime(df["time"], format="%Y%m%d%H%M%S%f", errors="coerce")
    df = df.drop(columns=["time"]).sort_values("date").tail(count).reset_index(drop=True)
    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["volume"] = pd.to_numeric(df.get("volume", 0), errors="coerce")
    return df.dropna(subset=["close"])


# ── akshare 实现 ──

def _fetch_akshare_daily(symbol: str, count: int = 200) -> Optional[pd.DataFrame]:
    """akshare ETF 日 K 线"""
    import akshare as ak
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=count * 3)).strftime("%Y%m%d")

    df = ak.fund_etf_hist_em(symbol=symbol.strip(), period="daily",
                             start_date=start_date, end_date=end_date,
                             adjust="qfq")
    if df is None or df.empty:
        return None

    df = df.rename(columns={
        "日期": "date",
        "开盘": "open",
        "最高": "high",
        "最低": "low",
        "收盘": "close",
        "成交量": "volume",
    })
    df = df[["date", "open", "high", "low", "close", "volume"]]
    df["date"] = pd.to_datetime(df["date"])
    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["volume"] = pd.to_numeric(df.get("volume", 0), errors="coerce")
    return df.sort_values("date").tail(count).reset_index(drop=True).dropna(subset=["close"])


def _fetch_akshare_minute(symbol: str, period: str = "60", count: int = 200) -> Optional[pd.DataFrame]:
    """akshare ETF 分钟 K 线"""
    import akshare as ak
    freq = {"5": "5", "15": "15", "30": "30", "60": "60"}
    period_key = freq.get(period, "60")

    df = ak.fund_etf_hist_min_em(symbol=symbol.strip(), period=period_key)
    if df is None or df.empty:
        return None

    df = df.rename(columns={
        "时间": "date",
        "开盘": "open",
        "最高": "high",
        "最低": "low",
        "收盘": "close",
        "成交量": "volume",
    })
    df = df[["date", "open", "high", "low", "close", "volume"]]
    df["date"] = pd.to_datetime(df["date"])
    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["volume"] = pd.to_numeric(df.get("volume", 0), errors="coerce")
    return df.sort_values("date").tail(count).reset_index(drop=True).dropna(subset=["close"])


# ── 统一入口 ──

def fetch_etf_daily(symbol: str, count: int = 200) -> Optional[pd.DataFrame]:
    """获取 ETF 日 K 线（含今日实时行情），根据配置数据源路由"""
    source = get_data_source()

    if source == "akshare":
        return _fetch_akshare_daily(symbol, count)
    else:
        df = _fetch_baostock_daily(symbol, count)
        if df is not None:
            last_date = df["date"].max()
            today = datetime.now().strftime("%Y-%m-%d")
            if last_date.strftime("%Y-%m-%d") != today:
                spot = _fetch_realtime_spot(symbol)
                if spot and spot['close'] > 0:
                    new_row = pd.DataFrame([spot])
                    new_row["date"] = pd.to_datetime(new_row["date"])
                    df = pd.concat([df, new_row], ignore_index=True)
                    df = df.sort_values("date").tail(count).reset_index(drop=True)
        return df


def fetch_etf_minute(symbol: str, period: str = "60", count: int = 200) -> Optional[pd.DataFrame]:
    """获取 ETF 分钟 K 线，根据配置数据源路由"""
    source = get_data_source()

    if source == "akshare":
        return _fetch_akshare_minute(symbol, period, count)
    else:
        return _fetch_baostock_minute(symbol, period, count)


def _fetch_realtime_spot(symbol: str) -> Optional[dict]:
    """akshare 实时行情（仅 baostock 模式兜底用）"""
    try:
        import akshare as ak
        df = ak.fund_etf_spot_em()
        row = df[df['代码'] == symbol.strip()]
        if row.empty:
            return None
        r = row.iloc[0]
        today = datetime.now().strftime('%Y-%m-%d')
        return {
            'date': today,
            'open': float(r['开盘价']),
            'high': float(r['最高价']),
            'low': float(r['最低价']),
            'close': float(r['最新价']),
            'volume': int(r['成交量']),
        }
    except Exception as e:
        try:
            with open("E:\\etf-trader\\debug_akshare.log", "a", encoding="utf-8") as f:
                import traceback
                f.write(f"[{datetime.now()}] akshare failed: {e}\n{traceback.format_exc()}\n")
        except Exception:
            pass
        return None
