from dataclasses import dataclass


@dataclass
class TelegramMessage:
    chat_id: int
    text: str
    command: str = ""


@dataclass
class TelegramWebhook:
    update_id: int
    message: dict
