import os
import uuid
import shutil
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from database import get_db
from models.news_model import News  # 确保这里导入的是包含 summary 字段的模型
from datetime import datetime, date
from pydantic import BaseModel, Field

news_router = APIRouter(prefix="/news", tags=["新闻资讯管理"])

# 配置上传目录
NEWS_UPLOAD_DIR = "static/uploads/news"
os.makedirs(NEWS_UPLOAD_DIR, exist_ok=True)


# --- 1. 统一定义接收数据的模型 ---
class NewsSaveRequest(BaseModel):
    id: Optional[int] = Field(None, description="新闻ID (有则更新，无则新增)")
    title: Optional[str] = Field(None, description="新闻标题")
    summary: Optional[str] = Field(None, description="新闻简介/副标题")  # 【新增】
    content: Optional[str] = Field(None, description="富文本HTML内容")
    cover_image: Optional[str] = Field(None, description="封面图片URL")
    publish_date: Optional[str] = Field(None, description="发布日期 (YYYY-MM-DD)")
    is_top: Optional[bool] = Field(None, description="是否置顶")


# --- 统一保存接口 (新增/更新 二合一) ---
@news_router.post("/save", summary="保存新闻 (新增或更新)")
def save_news(request: NewsSaveRequest, db: Session = Depends(get_db)):
    """
    智能保存 + 唯一置顶逻辑
    """

    # --- 步骤 0: 处理“唯一置顶”逻辑 ---
    if request.is_top is True:
        if request.id:
            # 更新场景：把所有 id != 当前id 的置为 False
            db.query(News).filter(News.id != request.id).update({"is_top": False})
        else:
            # 新增场景：把所有现有的都置为 False
            db.query(News).update({"is_top": False})

    # --- 步骤 1: 判断是新增还是更新 ---
    news_record = None  # 用于最后返回 ID

    if request.id is None:
        # === 执行新增逻辑 ===
        if not request.title or not request.content or not request.publish_date:
            raise HTTPException(status_code=400, detail="新增新闻时，标题、内容和发布日期不能为空")

        try:
            pub_date = datetime.strptime(request.publish_date, "%Y-%m-%d").date()

            new_news = News(
                title=request.title,
                summary=request.summary,  # 【新增】直接赋值，允许为 None
                content=request.content,
                cover_image=request.cover_image or "",
                publish_date=pub_date,
                is_top=request.is_top if request.is_top is not None else False,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            db.add(new_news)
            news_record = new_news  # 记录引用以便后续刷新

        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"日期格式错误: {str(e)}")
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")

    else:
        # === 执行更新逻辑 ===
        record = db.query(News).filter(News.id == request.id).first()
        if not record:
            raise HTTPException(status_code=404, detail="新闻不存在，无法更新")

        # 动态更新提供的字段
        if request.title is not None:
            record.title = request.title
        if request.summary is not None:  # 【新增】如果传了 summary 就更新，没传保持原样
            record.summary = request.summary
        if request.content is not None:
            record.content = request.content
        if request.cover_image is not None:
            record.cover_image = request.cover_image
        if request.publish_date is not None:
            try:
                record.publish_date = datetime.strptime(request.publish_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="日期格式错误")

        if request.is_top is not None:
            record.is_top = request.is_top

        record.updated_at = datetime.now()
        news_record = record

    # --- 步骤 2: 统一提交事务 ---
    try:
        db.commit()
        db.refresh(news_record)  # 刷新获取最新状态

        return {
            "code": 200,
            "msg": "保存成功",
            "data": {"id": news_record.id}
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"数据库提交失败: {str(e)}")


# --- 获取新闻列表 ---
@news_router.get("/list", summary="获取新闻列表")
def get_news_list(
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(10, ge=1, le=100, description="每页数量"),
        keyword: Optional[str] = Query(None, description="搜索标题关键字"),
        db: Session = Depends(get_db)
):
    # 1. 构建基础查询 (处理搜索)
    base_query = db.query(News)
    if keyword:
        base_query = base_query.filter(
            (News.title.contains(keyword)) |
            (News.summary.contains(keyword))
        )

    # ==========================================
    # 核心修改：分离查询策略
    # ==========================================

    # --- 第一步：单独查出所有“置顶”数据 ---
    # 这部分数据不参与分页计算，永远作为“赠品”返回
    top_query = base_query.filter(News.is_top == True)
    top_items = top_query.order_by(desc(News.publish_date)).all()

    # --- 第二步：针对“非置顶”数据进行严格分页 ---
    normal_query = base_query.filter(News.is_top == False)

    # 计算普通数据的总数（用于前端计算总页数，注意这里只算普通的）
    total_normal_count = normal_query.count()

    # 计算偏移量：只根据普通数据的数量来算
    # 例如 page=1, page_size=8 -> offset=0
    # 例如 page=2, page_size=8 -> offset=8
    offset = (page - 1) * page_size

    # 获取当前页的普通数据（严格限制数量）
    normal_items = normal_query.order_by(desc(News.publish_date)).offset(offset).limit(page_size).all()

    # --- 第三步：合并数据 ---
    # 最终列表 = 置顶列表 + 当前页的普通列表
    # 结果长度 = 置顶数量 + page_size
    items = top_items + normal_items

    # 关于 total 的返回：
    # 建议返回 total_normal_count，这样前端分页组件计算的页数是准确的（基于普通数据量）。
    # 如果返回 total_all (包含置顶)，前端页码可能会多算一页（因为置顶占了位置但没占页码）。

    # 数据格式化
    data_list = []
    for item in items:
        current_summary = item.summary if item.summary else ""
        data_list.append({
            "id": item.id,
            "title": item.title,
            "summary": current_summary,
            "pic": item.cover_image or "",
            "date": item.publish_date.strftime("%Y-%m-%d") if item.publish_date else "",
            "isTop": item.is_top
        })

    return {
        "code": 200,
        "msg": "获取成功",
        "total": total_normal_count,  # 【关键点】这里返回普通数据的总数，方便前端计算纯数字页码
        "data": data_list  # 但 data 数组里包含了 置顶 + 普通
    }

# --- 删除新闻 ---
@news_router.delete("/delete/{news_id}", summary="删除新闻")
def delete_news(news_id: int, db: Session = Depends(get_db)):
    record = db.query(News).filter(News.id == news_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="新闻不存在")

    db.delete(record)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

    return {"code": 200, "msg": "删除成功"}


# --- 获取新闻详情 ---
@news_router.get("/{news_id}", summary="获取新闻详情")
def get_news_detail(news_id: int, db: Session = Depends(get_db)):
    record = db.query(News).filter(News.id == news_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="新闻不存在")

    return {
        "code": 200,
        "msg": "获取成功",
        "data": {
            "id": record.id,
            "title": record.title,
            "summary": record.summary or "",
            "content": record.content,
            "cover_image": record.cover_image or "",
            "publish_date": record.publish_date.strftime("%Y-%m-%d") if record.publish_date else "",
            "isTop": record.is_top
        }
    }