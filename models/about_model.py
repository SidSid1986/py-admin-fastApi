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


class Banner(Base):
    __tablename__ = "about_banner"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 图片地址 ( 存储相对路径，如 /static/uploads/banner/xxx.jpg)
    img_url = Column(String(500), nullable=False, comment="轮播图图片URL")

    # 排序权重
    sort_order = Column(Integer, default=0, comment="排序权重")

    # 创建时间
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")

    # 更新时间
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="最后更新时间")

    def __repr__(self):
        return f"<Banner(id={self.id}, img_url={self.img_url})>"


# ================= 新增：时间轴模型 =================

class AboutStep(Base):
    __tablename__ = "about_step"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 标题 (例如：年份 "2009", "2023")
    title = Column(String(50), nullable=False, comment="步骤标题/年份")

    # 图片地址 (存储相对路径，如 /static/uploads/about/step_xxx.png)
    img_url = Column(String(500), nullable=False, comment="步骤图片URL")

    # 排序权重
    sort_order = Column(Integer, default=0, comment="排序权重")

    # 创建时间
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")

    # 更新时间
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="最后更新时间")

    def __repr__(self):
        return f"<AboutStep(id={self.id}, title={self.title}, sort_order={self.sort_order})>"