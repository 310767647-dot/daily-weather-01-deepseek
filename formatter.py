"""
消息格式化模块 — 将天气数据组装为飞书消息卡片
文档: https://open.feishu.cn/document/uAjLw4CM/ukzMukzMukzM/feishu-cards/card-components
"""

from datetime import datetime
from weather import CityWeather, DailyForecast

# 天气图标 → 飞书 compatible emoji
WEATHER_EMOJI: dict[str, str] = {
    "晴": "☀️",
    "多云": "⛅",
    "阴": "☁️",
    "小雨": "🌦️",
    "中雨": "🌧️",
    "大雨": "🌧️",
    "雷阵雨": "⛈️",
    "暴雨": "🌊",
    "小雪": "🌨️",
    "中雪": "❄️",
    "大雪": "❄️",
    "雾": "🌫️",
    "霾": "😶‍🌫️",
    "大风": "💨",
}

WIND_EMOJI = "💨"
HUMIDITY_EMOJI = "💧"
TEMP_EMOJI = "🌡️"


def _emoji_for(weather_text: str) -> str:
    """根据天气文字返回对应的 emoji"""
    for keyword, emoji in WEATHER_EMOJI.items():
        if keyword in weather_text:
            return emoji
    return "🌤️"


def _format_now_block(city: CityWeather) -> list[dict]:
    """格式化单个城市的实时天气信息块（用于分栏）"""
    n = city.now
    emoji = _emoji_for(n.text)
    return [
        {
            "tag": "markdown",
            "content": (
                f"**{city.city_name}**  {emoji} {n.text}\n"
                f"{TEMP_EMOJI}  {n.temp}℃（体感 {n.feels_like}℃）\n"
                f"{WIND_EMOJI}  {n.wind_dir} {n.wind_scale}级\n"
                f"{HUMIDITY_EMOJI}  湿度 {n.humidity}%　降水量 {n.precip}mm\n"
                f"👁️  能见度 {n.vis}km"
            ),
        }
    ]


def _format_forecast_row(forecast: DailyForecast) -> str:
    """格式化单日预报为一行文本"""
    emoji_day = _emoji_for(forecast.text_day)
    emoji_night = _emoji_for(forecast.text_night)

    from datetime import timedelta
    today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    day_after = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")

    if forecast.fx_date == today:
        date_label = "📌 今天"
    elif forecast.fx_date == tomorrow:
        date_label = "📅 明天"
    elif forecast.fx_date == day_after:
        date_label = "📆 后天"
    else:
        date_label = forecast.fx_date

    return (
        f"**{date_label}**  {emoji_day}{forecast.text_day}"
        f"  {forecast.temp_min}~{forecast.temp_max}℃"
        f"  {WIND_EMOJI}{forecast.wind_dir_day}{forecast.wind_scale_day}级"
    )


# ---------- Public API ----------

def build_weather_card(
    cities: list[CityWeather],
) -> dict:
    """构建飞书天气消息卡片

    Args:
        cities: 天气数据列表

    Returns:
        飞书 Card 结构 (JSON dict)
    """
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    weekday_map = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    weekday = weekday_map[now.weekday()]

    # 卡片头部
    header = {
        "title": {"tag": "plain_text", "content": f"🌤 每日天气简报 · {date_str} {weekday}"},
        "subtitle": {"tag": "plain_text", "content": f"苏州 · 江阴"},
    }

    # --- 实时天气（分栏并列展示每个城市）---
    columns: list[dict] = []
    for city in cities:
        columns.append({
            "tag": "column",
            "width": "weighted",
            "weight": 1,
            "vertical_align": "top",
            "elements": _format_now_block(city),
        })

    # 分隔线
    divider = {"tag": "hr"}

    # --- 未来预报 ---
    forecast_lines = ["**📋 未来几日预报**\n"]
    if cities:
        # 取第一个城市的预报作为展示（预报对两个城市类似，但各自展示）
        for city in cities:
            forecast_lines.append(f"\n**{city.city_name}**：")
            if city.forecast:
                for f in city.forecast[:3]:  # 最多3天
                    forecast_lines.append(_format_forecast_row(f))
            forecast_lines.append("")

    forecast_block = {
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": "\n".join(forecast_lines),
        },
    }

    # --- 天气查询按钮 ---
    query_button = {
        "tag": "action",
        "actions": [
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "🔍 天气查询  点击查任意城市天气"},
                "type": "default",
                "multi_url": {
                    "url": "https://wttr.in",
                    "pc_url": "",
                    "android_url": "",
                    "ios_url": "",
                },
            }
        ],
    }

    # --- 脚注 ---
    footer = {
        "tag": "note",
        "elements": [
            {
                "tag": "plain_text",
                "content": f"⏱ 数据更新于 {now.strftime('%H:%M')}  ·  数据来源：wttr.in",
            }
        ],
    }

    card = {
        "header": header,
        "elements": [
            {"tag": "column_set", "flex_mode": "none", "background_style": "default", "columns": columns},
            divider,
            forecast_block,
            query_button,
            footer,
        ],
    }

    return card
