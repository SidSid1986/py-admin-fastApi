from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
from database import get_db
from datetime import datetime
from pydantic import BaseModel
import requests
import xml.etree.ElementTree as ET

# 只导入 ORM，不导入任何 BaseModel！！
from models.chat_model import ChatMessage

chat_router = APIRouter(prefix="/api/chat", tags=["在线客服"])

# ================= 微信配置 =================
WECHAT_APPID = ""
WECHAT_APPSECRET = ""
ADMIN_OPENID = ""
# ============================================

# --------------------------
# 所有 BaseModel 都在这里！
# --------------------------

# 前端发送消息用
class ChatMessageCreate(BaseModel):
    visitor_id: str
    sender: str
    content: str

# 单条消息返回
class ChatMessageBack(BaseModel):
    id: int
    visitor_id: str
    sender: str
    content: str
    create_time: datetime

    class Config:
        from_attributes = True

# 列表响应
class ChatListResponse(BaseModel):
    code: int
    msg: str
    data: List[ChatMessageBack]

# 通用响应
class CommonResponse(BaseModel):
    code: int
    msg: str


# ---------------- 工具函数 ----------------
def get_access_token():
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={WECHAT_APPID}&secret={WECHAT_APPSECRET}"
    try:
        res = requests.get(url, timeout=5)
        return res.json().get("access_token")
    except:
        return None

def send_to_admin(content: str):
    at = get_access_token()
    if not at:
        return
    url = f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={at}"
    data = {
        "touser": ADMIN_OPENID,
        "msgtype": "text",
        "text": {"content": content}
    }
    requests.post(url, json=data)


# ---------------- 1. 发送消息 ----------------
@chat_router.post("/send", summary="发送聊天消息", response_model=CommonResponse)
def send_chat(
    data: ChatMessageCreate,
    db: Session = Depends(get_db)
):
    try:
        msg = ChatMessage(
            visitor_id=data.visitor_id,
            sender=data.sender,
            content=data.content,
            create_time=datetime.now()
        )
        db.add(msg)
        db.commit()

        send_to_admin(f"网页访客 {data.visitor_id}：{data.content}")
        return {"code": 200, "msg": "发送成功"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"发送失败：{str(e)}")


# ---------------- 2. 获取聊天记录 ----------------
@chat_router.get("/pull", summary="获取聊天记录", response_model=ChatListResponse)
def get_chat_records(
    visitor_id: str = Query(...),
    db: Session = Depends(get_db)
):
    try:
        messages = db.query(ChatMessage)\
            .filter(ChatMessage.visitor_id == visitor_id)\
            .order_by(ChatMessage.id.asc())\
            .all()

        return {
            "code": 200,
            "msg": "获取成功",
            "data": messages
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取失败：{str(e)}")


# ---------------- 3. 微信公众号回调 ----------------
@chat_router.post("/wechat/callback", summary="微信消息回调")
async def wechat_callback(
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        body = await request.body()
        root = ET.fromstring(body)
        from_user = root.find("FromUserName").text
        msg_type = root.find("MsgType").text
        content = root.find("Content").text if msg_type == "text" else ""

        if from_user != ADMIN_OPENID:
            return "success"

        last = db.query(ChatMessage).order_by(desc(ChatMessage.id)).first()
        if last:
            reply = ChatMessage(
                visitor_id=last.visitor_id,
                sender="admin",
                content=content,
                create_time=datetime.now()
            )
            db.add(reply)
            db.commit()

        return "success"
    except:
        return "success"