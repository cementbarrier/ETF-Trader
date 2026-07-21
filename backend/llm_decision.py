"""
LLM 结构化决策模块：
构建固定模板 Prompt，调用 LLM，解析 JSON 返回。
"""
import json
import re
from backend.llm_client import chat
from backend.config_manager import get_risk_params, get_setting

_PROMPT_TEMPLATE = """你是一个量化交易辅助决策系统。请严格根据以下数据输出决策，不要输出任何主观观点。

【交易标的】{symbol}
【分析周期】{period_label}
【策略档位】{risk_label}

【当前行情】
- 最新价: {price}
- 趋势判定(本地因子): {trend}
- 本地信号: {signals}

【技术指标】
- MACD: DIF={dif}, DEA={dea}
- RSI(14): {rsi}
- BOLL: 上轨={boll_up}, 中轨={boll_mid}, 下轨={boll_dn}
- MA({ma_short}): {ma_short_val}
- MA({ma_long}): {ma_long_val}

【关键支撑位】{supports}
【关键压力位】{resistances}

【板块舆情】{sentiment}

【当前持仓】
{positions}

【账户资金】
{balance}

【当前风控】
- 止盈目标: +{take_profit}%
- 止损目标: -{stop_loss}%
- RSI超卖阈值: {rsi_oversold}
- RSI超买阈值: {rsi_overbought}

请严格按照以下 JSON 格式输出，不要加任何额外文字：
{{
  "trend": "bullish" | "bearish" | "neutral",
  "support_price": 数字(关键支撑价),
  "resistance_price": 数字(关键压力价),
  "stop_loss_price": 数字(离场止损价),
  "take_profit_price": 数字(止盈目标价),
  "action": "buy" | "sell" | "hold",
  "confidence": 0.0-1.0(置信度),
  "position_advice": "建议(如: 持有不动/逢低加仓/逐步减仓等, 无持仓则留空)"
}}"""


def _parse_json(text: str) -> dict:
    """从 LLM 回复中提取 JSON"""
    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 尝试提取 JSON 块
    m = re.search(r'\{[^{}]*\}', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return {"error": "JSON 解析失败", "raw": text[:200]}


def decide(
    symbol: str,
    factor_result: dict,
    sentiment: str = "",
    period: str = None,
    risk_profile: str = None,
    positions_text: str = "",
    balance_text: str = "",
) -> dict:
    """
    调用 LLM 做辅助决策。
    factor_result: factor_engine.run_factor_pipeline 的输出
    返回: 解析后的 JSON 字典
    """
    if risk_profile is None:
        risk_profile = get_setting("risk_profile", "standard")
    risk = get_risk_params(risk_profile)

    price = factor_result.get("price", "N/A")
    trend = factor_result.get("trend", "N/A")
    signals = ", ".join(factor_result.get("signals", [])) or "无"
    ind = factor_result.get("indicators", {})
    sr = factor_result.get("support_resistance", {})

    period_labels = {"short": "短线模式(60分钟趋势+30分钟操作)", "long": "长线模式(周线趋势+日线操作)"}
    risk_labels = {"conservative": "保守", "standard": "标准", "aggressive": "激进"}

    prompt = _PROMPT_TEMPLATE.format(
        symbol=symbol,
        period_label=period_labels.get(period or "short", "短线模式"),
        risk_label=risk_labels.get(risk_profile, "标准"),
        price=price,
        trend=trend,
        signals=signals,
        dif=ind.get("MACD_DIF", "N/A"),
        dea=ind.get("MACD_DEA", "N/A"),
        rsi=ind.get("RSI", "N/A"),
        boll_up=ind.get("BOLL_UP", "N/A"),
        boll_mid=ind.get("BOLL_MID", "N/A"),
        boll_dn=ind.get("BOLL_DN", "N/A"),
        ma_short=risk.get("ma_short", 10),
        ma_long=risk.get("ma_long", 30),
        ma_short_val=ind.get(f"MA{risk.get('ma_short', 10)}", "N/A"),
        ma_long_val=ind.get(f"MA{risk.get('ma_long', 30)}", "N/A"),
        supports=", ".join(str(s) for s in sr.get("supports", [])) or "无",
        resistances=", ".join(str(r) for r in sr.get("resistances", [])) or "无",
        sentiment=sentiment or "无板块舆情信息",
        positions=positions_text or "空仓",
        balance=balance_text or "无资金信息",
        take_profit=risk.get("take_profit_pct", 5),
        stop_loss=risk.get("stop_loss_pct", 3),
        rsi_oversold=risk.get("rsi_oversold", 25),
        rsi_overbought=risk.get("rsi_overbought", 75),
    )

    response = chat(prompt)
    return _parse_json(response)
