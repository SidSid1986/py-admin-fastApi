from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from database import Base

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    visitor_id = Column(String(64), nullable=False, index=True, comment="访客ID")
    sender = Column(String(32), nullable=False, comment="发送者")
    content = Column(Text, nullable=False, comment="消息内容")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")

    def __repr__(self):
        return f"<ChatMessage(id={self.id})>"