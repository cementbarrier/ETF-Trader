"""
行情数据获取：akshare ETF 历史 K 线
"""
from typing import Optional
import pandas as pd


def _patch_requests_no_proxy():
    """强制 requests 直连，绕过系统代理"""
    import requests
    import os

    # 清除环境变量中的代理
    for k in list(os.environ):
        if k.upper().endswith('_PROXY') or k.upper() == 'NO_PROXY':
            os.environ.pop(k, None)

    # Monkey-patch Session.request，强制 proxies=None
    _orig_request = requests.Session.request

    def _request(self, method, url, **kwargs):
        self.trust_env = False
        kwargs["proxies"] = None
        return _orig_request(self, method, url, **kwargs)

    requests.Session.request = _request


def _ak_daily(symbol: str):
    _patch_requests_no_proxy()
    import akshare as ak
    return ak.fund_etf_hist_em(symbol=symbol, period="daily", adjust="qfq")


def _ak_minute(symbol: str, period: str):
    _patch_requests_no_proxy()
    import akshare as ak
    return ak.fund_etf_hist_em(symbol=symbol, period=period, adjust="qfq")


def fetch_etf_daily(symbol: str, count: int = 200) -> Optional[pd.DataFrame]:
    try:
        df = _ak_daily(symbol)
        if df.empty:
            return None
        df = df.rename(columns={
            "日期": "date", "开盘": "open", "最高": "high",
            "最低": "low", "收盘": "close", "成交量": "volume"
        })
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").tail(count).reset_index(drop=True)
        for col in ["open", "high", "low", "close"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["volume"] = pd.to_numeric(df.get("volume", 0), errors="coerce")
        return df.dropna(subset=["close"])
    except ImportError:
        raise ImportError("请先安装 akshare: pip install akshare")
    except Exception as e:
        raise RuntimeError(f"获取 {symbol} 行情失败: {e}")


def fetch_etf_minute(symbol: str, period: str = "60", count: int = 200) -> Optional[pd.DataFrame]:
    try:
        df = _ak_minute(symbol, period)
        if df.empty:
            return None
        df = df.rename(columns={
            "日期": "date", "开盘": "open", "最高": "high",
            "最低": "low", "收盘": "close", "成交量": "volume"
        })
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").tail(count).reset_index(drop=True)
        for col in ["open", "high", "low", "close"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["volume"] = pd.to_numeric(df.get("volume", 0), errors="coerce")
        return df.dropna(subset=["close"])
    except ImportError:
        raise ImportError("请先安装 akshare: pip install akshare")
    except Exception as e:
        raise RuntimeError(f"获取 {symbol} {period}分钟K线失败: {e}")
