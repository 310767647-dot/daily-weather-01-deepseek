"""
天气数据抓取模块 — wttr.in（免费，无需注册）
文档: https://github.com/chubin/wttr.in
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# 城市名称（wttr.in 支持英文城市名）
CITY_MAP: dict[str, str] = {
    "Suzhou": "苏州",
    "Jiangyin": "江阴",
}

# wttr.in 天气描述 → 中文翻译
WEATHER_ZH: dict[str, str] = {
    "Sunny": "晴",
    "Clear": "晴",
    "Partly cloudy": "多云",
    "Cloudy": "阴",
    "Overcast": "阴",
    "Mist": "雾",
    "Fog": "雾",
    "Patc": "零星",     # Patchy / Patches of
    "Patchy rain nearby": "零星小雨",
    "Patchy rain possible": "零星小雨",
    "Light rain": "小雨",
    "Moderate rain": "中雨",
    "Heavy rain": "大雨",
    "Light drizzle": "毛毛雨",
    "Light rain shower": "小阵雨",
    "Moderate or heavy rain shower": "中到大阵雨",
    "Torrential rain shower": "大暴雨",
    "Light snow": "小雪",
    "Moderate snow": "中雪",
    "Heavy snow": "大雪",
    "Light sleet": "小冻雨",
    "Moderate or heavy sleet": "中到大冻雨",
    "Thundery outbreaks": "雷阵雨",
    "Thunderstorm": "雷暴",
    "Light thunderstorm": "小雷暴",
    "Moderate or heavy thunderstorm": "强雷暴",
    "Haze": "霾",
    "Smoke": "烟霾",
    "Dust": "扬尘",
    "Blowing snow": "吹雪",
    "Freezing fog": "冻雾",
    "Ice pellets": "冰雹",
}


def _translate_weather(desc_en: str) -> str:
    """将英文天气描述翻译为中文"""
    # 精确匹配优先
    if desc_en in WEATHER_ZH:
        return WEATHER_ZH[desc_en]
    # 模糊匹配
    for en, zh in WEATHER_ZH.items():
        if en in desc_en or desc_en in en:
            return zh
    # 未匹配则原样返回
    return desc_en

WTTR_URL = "https://wttr.in"


def _beaufort_scale(kmh: float) -> int:
    """将风速(km/h)转换为蒲福风力等级 (0-12)"""
    thresholds = [1, 6, 12, 20, 29, 39, 50, 62, 75, 89, 103, 118]
    for level, thresh in enumerate(thresholds):
        if kmh < thresh:
            return level
    return 12


def _wind_dir_emoji(degree_16: str) -> str:
    """将16方位风向转为箭头 emoji"""
    mapping = {
        "N": "⬆️", "NNE": "↗️", "NE": "↗️", "ENE": "↗️",
        "E": "➡️", "ESE": "↘️", "SE": "↘️", "SSE": "↘️",
        "S": "⬇️", "SSW": "↙️", "SW": "↙️", "WSW": "↙️",
        "W": "⬅️", "WNW": "↖️", "NW": "↖️", "NNW": "↖️",
    }
    return mapping.get(degree_16.upper().strip(), "🌀")


@dataclass
class NowWeather:
    """实时天气"""
    temp: str            # 温度，℃
    feels_like: str      # 体感温度，℃
    icon: str            # 天气图标代码 (weatherCode)
    text: str            # 天气状况文字
    wind_dir: str        # 风向 (16方位)
    wind_scale: str      # 风力等级 (蒲福)
    humidity: str        # 湿度，%
    precip: str          # 降水量，mm
    pressure: str        # 大气压强，hPa
    vis: str             # 能见度，km
    obs_time: str        # 观测时间


@dataclass
class DailyForecast:
    """逐天预报"""
    fx_date: str         # 预报日期
    sunrise: str         # 日出时间
    sunset: str          # 日落时间
    moon_phase: str      # 月相
    temp_max: str        # 最高温
    temp_min: str        # 最低温
    icon_day: str        # 白天天气图标
    text_day: str        # 白天天气状况 (取中午时段的 desc)
    icon_night: str      # 夜间天气图标
    text_night: str      # 夜间天气状况
    wind_dir_day: str    # 白天风向
    wind_scale_day: str  # 白天风力
    humidity: str        # 湿度
    precip: str          # 降水量
    uv_index: str        # 紫外线指数
    vis: str             # 能见度


@dataclass
class CityWeather:
    """一个城市的完整天气数据"""
    city_id: str
    city_name: str
    now: NowWeather
    forecast: list[DailyForecast] = field(default_factory=list)
    fetched_at: str = field(default_factory=lambda: datetime.now().isoformat())


class WttrClient:
    """wttr.in 天气客户端（无需 API Key）"""

    def _get_json(self, city: str) -> dict:
        """获取城市天气 JSON"""
        url = f"{WTTR_URL}/{city}"
        resp = requests.get(
            url,
            params={"format": "j1"},
            timeout=30,
            headers={"User-Agent": "curl/8.0"},
        )
        resp.raise_for_status()
        return resp.json()

    def get_city_weather(self, city_id: str) -> CityWeather:
        """
        获取一个城市的完整天气数据

        Args:
            city_id: 城市英文名，如 "Suzhou", "Jiangyin"
        """
        data = self._get_json(city_id)
        cc = data["current_condition"][0]
        weather_days = data.get("weather", [])

        # --- 实时天气 ---
        weather_desc = cc["weatherDesc"][0]["value"] if isinstance(cc["weatherDesc"], list) and cc["weatherDesc"] else ""
        wind_kmh = float(cc.get("windspeedKmph", 0))
        wind_scale = _beaufort_scale(wind_kmh)

        now = NowWeather(
            temp=cc["temp_C"],
            feels_like=cc["FeelsLikeC"],
            icon=cc.get("weatherCode", ""),
            text=_translate_weather(weather_desc),
            wind_dir=cc.get("winddir16Point", ""),
            wind_scale=str(wind_scale),
            humidity=cc.get("humidity", ""),
            precip=cc.get("precipMM", "0"),
            pressure=cc.get("pressure", ""),
            vis=cc.get("visibility", ""),
            obs_time=cc.get("observation_time", ""),
        )

        # --- 逐天预报 (最多3天) ---
        forecasts: list[DailyForecast] = []
        for d in weather_days[:3]:
            astro = d.get("astronomy", [{}])[0] if d.get("astronomy") else {}

            # 用中午 12:00 的数据代表"白天"状况
            noon_data = None
            night_data = None
            for h in d.get("hourly", []):
                time_str = h.get("time", "0").zfill(4)
                hour = int(time_str[:2])
                if hour == 12:
                    noon_data = h
                elif hour == 21:
                    night_data = h
            day_h = noon_data or d["hourly"][0] if d.get("hourly") else {}
            night_h = night_data or day_h

            day_desc = day_h.get("weatherDesc", [{}])[0].get("value", "") if isinstance(day_h.get("weatherDesc"), list) else ""
            night_desc = night_h.get("weatherDesc", [{}])[0].get("value", "") if isinstance(night_h.get("weatherDesc"), list) else ""

            day_wind_kmh = float(day_h.get("windspeedKmph", 0))
            day_wind_scale = _beaufort_scale(day_wind_kmh)

            forecast = DailyForecast(
                fx_date=d["date"],
                sunrise=astro.get("sunrise", ""),
                sunset=astro.get("sunset", ""),
                moon_phase=astro.get("moon_phase", ""),
                temp_max=d.get("maxtempC", ""),
                temp_min=d.get("mintempC", ""),
                icon_day=str(day_h.get("weatherCode", "")),
                text_day=_translate_weather(day_desc),
                icon_night=str(night_h.get("weatherCode", "")),
                text_night=_translate_weather(night_desc),
                wind_dir_day=day_h.get("winddir16Point", ""),
                wind_scale_day=str(day_wind_scale),
                humidity=day_h.get("humidity", ""),
                precip=day_h.get("precipMM", "0"),
                uv_index=d.get("uvIndex", ""),
                vis=day_h.get("visibility", ""),
            )
            forecasts.append(forecast)

        city_name = CITY_MAP.get(city_id, city_id)
        logger.info(f"已获取 {city_name} 天气数据")
        return CityWeather(
            city_id=city_id,
            city_name=city_name,
            now=now,
            forecast=forecasts,
        )

    def get_all(self, city_ids: list[str]) -> list[CityWeather]:
        """批量获取多个城市的天气"""
        return [self.get_city_weather(cid) for cid in city_ids]
