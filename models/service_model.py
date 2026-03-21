from sqlalchemy import Column, Integer, Text, DateTime
from sqlalchemy.sql import func
from database import Base  # 确保你的项目中有一个名为 Base 的声明基类


class ServiceContent(Base):
    """
    服务介绍内容模型
    对应数据库表名: service_contents (SQLAlchemy 默认会将类名转为复数小写)
    """
    __tablename__ = "service_contents"

    # 主键 ID，我们业务逻辑中固定使用 ID=1
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 内容字段，使用 Text 类型以支持长富文本 (HTML)
    content = Column(Text, nullable=True, default="暂无服务内容")

    # 更新时间 (可选，方便知道最后什么时候改的)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<ServiceContent(id={self.id}, content='{self.content[:20]}...')>"