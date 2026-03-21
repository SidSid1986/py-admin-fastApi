# models/about_model.py
from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from database import Base


class AboutUs(Base):
    __tablename__ = "about_us"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 封面图片地址 (存储相对路径，如 /static/uploads/about/cover_xxx.jpg)
    cover_image = Column(String(500), nullable=True, comment="封面图片URL")

    # 富文本内容 (存储完整的 HTML 字符串)
    content = Column(Text, nullable=True, comment="关于我们富文本内容")

    # 更新时间
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="最后更新时间")

    def __repr__(self):
        return f"<AboutUs(id={self.id}, update_time={self.update_time})>"