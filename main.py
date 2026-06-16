"""
主入口 — 抓取天气 → 格式化 → 推送到飞书

用法:
    python main.py              # 使用 .env 中配置的城市
    python main.py --dry-run    # 仅抓取并打印卡片 JSON，不推送
"""

import argparse
import logging
import sys
import os
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv

from weather import WttrClient, CITY_MAP
from formatter import build_weather_card
from notifier import FeishuNotifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")

# 默认城市列表 (wttr.in 城市英文名)
DEFAULT_CITIES = ["Suzhou", "Jiangyin"]


def load_config() -> dict:
    """加载配置（环境变量 / .env 文件）"""
    load_dotenv()

    webhook = os.getenv("FEISHU_WEBHOOK_URL", "").strip()
    # 城市列表：可从环境变量 CITIES 覆盖，逗号分隔
    cities_raw = os.getenv("CITIES", ",".join(DEFAULT_CITIES)).strip()
    city_ids = [c.strip() for c in cities_raw.split(",") if c.strip()]

    if not webhook:
        logger.error("FEISHU_WEBHOOK_URL 未设置，请在 .env 中配置")
        sys.exit(1)

    if not city_ids:
        logger.error("未配置任何城市")
        sys.exit(1)

    return {
        "webhook": webhook,
        "city_ids": city_ids,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="每日天气推送（免费版 · wttr.in）")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅抓取数据并打印卡片 JSON，不推送",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="忽略时间检查，强制推送（用于手动测试）",
    )
    args = parser.parse_args()

    config = load_config()

    # 时间检查：只在北京时间 08:00~09:00 之间运行（主窗口 08:30）
    # 避免每30分钟的 cron 在其他时间也发送
    if not args.dry_run and not args.force:
        from datetime import timezone, timedelta
        now_bj = datetime.now(timezone(timedelta(hours=8)))
        if not (8 <= now_bj.hour < 9):
            logger.info(f"当前北京时间 {now_bj.hour}:{now_bj.minute:02d}，非推送时段，自动跳过")
            return

    config = load_config()

    # 打印城市中文名
    city_names = [CITY_MAP.get(cid, cid) for cid in config["city_ids"]]
    logger.info(f"正在获取天气数据: {city_names}")

    client = WttrClient()
    cities = client.get_all(config["city_ids"])

    card = build_weather_card(cities)

    if args.dry_run:
        import json
        print(json.dumps(card, ensure_ascii=False, indent=2))
        logger.info("Dry-run 模式，未推送")
        return

    notifier = FeishuNotifier(config["webhook"])
    success = notifier.send_card(card)

    if success:
        logger.info("任务完成 ✅")
    else:
        logger.error("任务失败 ❌")
        sys.exit(1)


if __name__ == "__main__":
    main()
