from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base  # 假设你的 Base 在 database.py 中定义
from models.industry_model import Industry  # 导入 Industry 模型以建立关系


class Solution(Base):
    __tablename__ = "solutions"

    # --- 主键 ---
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # --- 外键 (隶属于 Industry) ---
    # ondelete="CASCADE" 表示如果行业被删除，该行业下的解决方案也会自动删除
    # 如果希望行业删除后解决方案保留但 industry_id 为空，则去掉 ondelete 或设为 SET NULL (需允许 nullable=True)
    fid = Column(Integer, ForeignKey("industries.id", ondelete="CASCADE"), nullable=False, index=True,
                 comment="所属行业ID")

    # --- 基础信息 ---
    title = Column(String(200), nullable=False, comment="方案标题")

    # --- 图片资源 ---
    cover1 = Column(String(500), nullable=True, comment="封面图1 (主图)")
    cover2 = Column(String(500), nullable=True, comment="封面图2 (副图/悬停图)")

    # --- 富文本内容 ---
    # Text 类型适合存储较长的 HTML 内容
    content = Column(Text, nullable=False, comment="方案详情富文本内容")

    # --- 状态与控制 ---
    is_active = Column(Boolean, default=True, comment="是否启用")
    sort = Column(Integer, default=0, comment="排序权重")

    # --- 时间戳 ---
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    # --- 关系定义 (反向关联) ---
    # 通过 industry.solutions 可以访问该行业下的所有解决方案列表
    industry = relationship("Industry", back_populates="solutions")

    def __repr__(self):
        return f"<Solution(id={self.id}, title='{self.title}', fid={self.fid})>"