import logging
import os
from logging.handlers import RotatingFileHandler

log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
os.makedirs(log_dir, exist_ok=True)

logger = logging.getLogger("chat_messages")
logger.setLevel(logging.INFO)

file_handler = RotatingFileHandler(
    os.path.join(log_dir, "chat_messages.log"),
    maxBytes=10 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8",
)
file_handler.setFormatter(logging.Formatter(
    "%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
))

console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(
    "%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
))

logger.addHandler(file_handler)
logger.addHandler(console_handler)


def log_messages(messages):
    """遍历消息列表，按类型记录 HumanMessage、AIMessage、ToolMessage"""
    for msg in messages:
        msg_type = getattr(msg, "type", "unknown")
        if msg_type == "human":
            logger.info(f"[HumanMessage] {msg.content}")
        elif msg_type == "ai":
            content_preview = msg.content[:500] if msg.content else "(empty)"
            logger.info(f"[AIMessage] {content_preview}")
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    logger.info(f"[AIMessage ToolCall] name={tc['name']}, args={tc['args']}")
        elif msg_type == "tool":
            content_preview = msg.content[:500] if msg.content else "(empty)"
            logger.info(f"[ToolMessage] name={getattr(msg, 'name', 'unknown')}, content={content_preview}")
