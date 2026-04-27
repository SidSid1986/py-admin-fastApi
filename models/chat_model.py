from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from datetime import datetime
from database import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    visitor_id = Column(String(64), nullable=False, index=True, comment="访客ID")
    sender = Column(String(32), nullable=False, comment="发送者")
    content = Column(Text, nullable=False, comment="消息内容")
    touser = Column(String(64), nullable=True, index=True, comment="企业微信接收人ID")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")

    # 👇 只加这一行：未读标记（默认未读）
    is_read = Column(Boolean, default=False, nullable=False, comment="是否已读")

    def __repr__(self):
        return f"<ChatMessage(id={self.id})>"