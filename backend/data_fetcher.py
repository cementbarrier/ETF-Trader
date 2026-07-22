"""
行情数据获取：baostock ETF 历史 K 线 + akshare 实时行情补充
"""
from typing import Optional
from datetime import datetime, timedelta
import pandas as pd
import baostock as bs


def _ensure_login():
    """确保 baostock 已登录（幂等）"""
    lg = bs.login()
    if lg.error_code != '0':
        raise RuntimeError(f"baostock 登录失败: {lg.error_msg}")


def _symbol_to_code(symbol: str) -> str:
    """ETF 代码转为 baostock 格式：510050 -> sh.510050"""
    s = symbol.strip()
    if s.startswith("5") or s.startswith("6"):
        return f"sh.{s}"
    else:
        return f"sz.{s}"


def _fetch_realtime_spot(symbol: str) -> Optional[dict]:
    """用 akshare 获取 ETF 实时行情，返回 {open,high,low,close,volume,date} 或 None"""
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
    except Exception:
        return None


def fetch_etf_daily(symbol: str, count: int = 200) -> Optional[pd.DataFrame]:
    """获取 ETF 日 K 线（含今日实时行情），返回最近 count 条"""
    _ensure_login()
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

    # 检查最新数据是否含今日，无则用 akshare 实时行情补充
    last_date = df["date"].max()
    if last_date.strftime("%Y-%m-%d") != today:
        spot = _fetch_realtime_spot(symbol)
        if spot and spot['close'] > 0:
            new_row = pd.DataFrame([spot])
            new_row["date"] = pd.to_datetime(new_row["date"])
            df = pd.concat([df, new_row], ignore_index=True)

    df = df.sort_values("date").tail(count).reset_index(drop=True)
    return df.dropna(subset=["close"])


def fetch_etf_minute(symbol: str, period: str = "60", count: int = 200) -> Optional[pd.DataFrame]:
    """获取 ETF 分钟 K 线（baostock 支持 5/15/30/60）"""
    _ensure_login()
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
    # baostock 分钟线 time 字段格式为 YYYYMMDDHHMMSSmmm，直接解析
    df["date"] = pd.to_datetime(df["time"], format="%Y%m%d%H%M%S%f", errors="coerce")
    df = df.drop(columns=["time"]).sort_values("date").tail(count).reset_index(drop=True)
    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["volume"] = pd.to_numeric(df.get("volume", 0), errors="coerce")
    return df.dropna(subset=["close"])
