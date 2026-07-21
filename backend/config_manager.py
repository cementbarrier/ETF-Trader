"""
配置管理器：JSON 读写 + 档位参数查询
开发模式读写项目内 config/，冻结模式自动迁移到 %APPDATA%/etf-trader/
"""
import json
import os
import shutil
import sys

# 冻结模式下的可写配置目录
_IS_FROZEN = getattr(sys, "frozen", False)
if _IS_FROZEN:
    CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "etf-trader")
    _BUNDLE_CONFIG = os.path.join(sys._MEIPASS, "config", "settings.json")
    # 首次运行：从 bundle 复制默认配置到用户目录
    os.makedirs(CONFIG_DIR, exist_ok=True)
    _TARGET = os.path.join(CONFIG_DIR, "settings.json")
    if os.path.exists(_BUNDLE_CONFIG) and not os.path.exists(_TARGET):
        shutil.copy2(_BUNDLE_CONFIG, _TARGET)
else:
    CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "config")

CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")


def _read() -> dict:
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def _write(data: dict):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_setting(key: str, default=None):
    return _read().get(key, default)


def set_setting(key: str, value):
    data = _read()
    data[key] = value
    _write(data)


def get_risk_params(profile: str = None) -> dict:
    if profile is None:
        profile = get_setting("risk_profile", "standard")
    risk_map = get_setting("risk_params", {})
    return risk_map.get(profile, risk_map.get("standard", {}))
