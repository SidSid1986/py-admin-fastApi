# models/news.py
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Date
from datetime import datetime
from database import Base


class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 标题
    title = Column(String(255), nullable=False, index=True)

    # 标题简介 (使用 Text 类型存储长文本)
    summary = Column(Text, nullable=True)

    # 富文本内容 (使用 Text 类型存储长 HTML)
    content = Column(Text, nullable=False)

    # 封面图路径 (存储相对路径或 URL)
    cover_image = Column(String(500), nullable=True)

    # 发布日期
    publish_date = Column(Date, nullable=False, default=datetime.now().date())

    # 是否置顶 (Boolean 或 Integer 0/1)
    is_top = Column(Boolean, default=False, index=True)

    # 创建时间 (用于内部排序参考)
    created_at = Column(DateTime, default=datetime.now())

    # 更新时间
    updated_at = Column(DateTime, default=datetime.now(), onupdate=datetime.now())

