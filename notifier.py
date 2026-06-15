"""
飞书消息推送模块 — 群机器人 Webhook
文档: https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot
"""

import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

RETRY_TIMES = 2


class FeishuNotifier:
    """飞书群机器人消息推送"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_card(self, card: dict) -> bool:
        """发送消息卡片

        Args:
            card: 飞书消息卡片 JSON 结构 (见 formatter.py)

        Returns:
            是否成功
        """
        payload = {
            "msg_type": "interactive",
            "card": card,
        }

        last_error: Optional[Exception] = None
        for attempt in range(1 + RETRY_TIMES):
            try:
                resp = requests.post(
                    self.webhook_url,
                    json=payload,
                    timeout=15,
                )
                resp.raise_for_status()
                result = resp.json()
                if result.get("code") != 0:
                    raise RuntimeError(
                        f"Feishu API error [code={result.get('code')}]: "
                        f"{result.get('msg', '')}"
                    )
                logger.info("飞书卡片发送成功")
                return True
            except requests.RequestException as e:
                last_error = e
                logger.warning(
                    f"飞书推送失败 (第 {attempt + 1} 次尝试): {e}"
                )
                if attempt < RETRY_TIMES:
                    import time
                    time.sleep(2)

        logger.error(f"飞书推送最终失败: {last_error}")
        return False

    def send_text(self, text: str) -> bool:
        """发送纯文本消息（简单通知用）"""
        payload = {
            "msg_type": "text",
            "content": {"text": text},
        }
        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=15)
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") != 0:
                raise RuntimeError(
                    f"Feishu text error [code={result.get('code')}]"
                )
            logger.info("飞书文本消息发送成功")
            return True
        except Exception as e:
            logger.error(f"飞书文本消息发送失败: {e}")
            return False
