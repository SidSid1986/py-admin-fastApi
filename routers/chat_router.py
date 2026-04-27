from fastapi import Response
import base64
import json
import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime
import time
import requests
from Crypto.Cipher import AES
from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from database import get_db
from models.chat_model import ChatMessage

chat_router = APIRouter(prefix="/chat", tags=["在线客服"])

# ===================== 请求体 =====================
class ChatSendRequest(BaseModel):
    visitor_id: str
    sender: str
    content: str
    touser: str = None
    chat_type: str

# ===================== 企微配置 =====================
WECOM_CORP_ID = "ww5dd0722c15118241"
WECOM_AGENT_ID = 1000030
WECOM_APP_SECRET = "fGriAfN2yxfJhYHAoIo0JO-vvSO9ymmVDwY-9pTW4Zs"
WECOM_TOKEN = "wecom123456"
WECOM_AES_KEY = "zOR16suTiC3eDPKJooQSLGMInwNOYKbiiCU7xcASSwS"

PRODUCT_USERID = "LiuCheng"
MAINTAIN_USERID = "XiaoNanGua"

user_visitor_map = {}

visitor_alias_map = {}
visitor_alias_counter = 1000

def get_friendly_visitor_id(visitor_id: str) -> str:
    global visitor_alias_counter
    if visitor_id not in visitor_alias_map:
        visitor_alias_map[visitor_id] = f"{visitor_alias_counter}"
        visitor_alias_counter += 1
    return visitor_alias_map[visitor_id]

_wecom_token_cache = None
_wecom_expire_time = 0

def get_wecom_access_token():
    global _wecom_token_cache, _wecom_expire_time
    now = time.time()
    if _wecom_token_cache and now < _wecom_expire_time:
        return _wecom_token_cache
    url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={WECOM_CORP_ID}&corpsecret={WECOM_APP_SECRET}"
    data = requests.get(url, timeout=10).json()
    if "access_token" in data:
        _wecom_token_cache = data["access_token"]
        _wecom_expire_time = now + data.get("expires_in", 7200) - 300
        return _wecom_token_cache
    return None

class WeComCrypto:
    def __init__(self, token, encoding_aes_key, corp_id):
        self.token = token
        self.corp_id = corp_id
        self.aes_key = base64.b64decode(encoding_aes_key + "=")
        self.iv = self.aes_key[:16]

    def decode(self, text):
        pad = ord(text[-1:])
        return text[:-pad] if 1 <= pad <= 32 else text

    def decrypt(self, encrypted):
        cipher = AES.new(self.aes_key, AES.MODE_CBC, self.iv)
        raw = cipher.decrypt(base64.b64decode(encrypted))
        decrypted = self.decode(raw)
        if len(decrypted) < 16:
            return ""
        content = decrypted[16:]
        xml_len = int.from_bytes(content[:4], byteorder='big')
        xml_content = content[4:4 + xml_len].decode()
        from_corpid = content[4 + xml_len:].decode()
        return xml_content if from_corpid == self.corp_id else ""

wxcpt = WeComCrypto(WECOM_TOKEN, WECOM_AES_KEY, WECOM_CORP_ID)

# ===================== 发送消息（入库+未读+企微卡片） =====================
@chat_router.post("/send_to_wecom_card")
async def send_chat_to_wecom_card(
    data: ChatSendRequest,
    db: Session = Depends(get_db)
):
    visitor_id = data.visitor_id
    sender = data.sender
    content = data.content
    chat_type = data.chat_type

    try:
        is_read = (sender != "visitor")

        msg = ChatMessage(
            visitor_id=visitor_id,
            sender=sender,
            content=content,
            create_time=datetime.now(),
            is_read=is_read
        )
        db.add(msg)
        db.commit()

        if sender != "visitor":
            return {"code": 200, "msg": "客服消息已保存"}

        if chat_type == "product":
            touser = PRODUCT_USERID
            title = "【产品咨询】新消息"
        elif chat_type == "maintain":
            touser = MAINTAIN_USERID
            title = "【维保咨询】新消息"
        else:
            return {"code": 400, "msg": "无效的聊天类型"}

        user_visitor_map[touser] = visitor_id

        token = get_wecom_access_token()
        if not token:
            return {"code": 200, "msg": "消息已保存，企微推送失败"}

        visitor_name = get_friendly_visitor_id(visitor_id)
        now_str = datetime.now().strftime("%m-%d %H:%M")
        jump_url = f"https://www.ytfreeie.com/chat/#/?visitor_id={visitor_id}&chat_type={chat_type}"

        send_data = {
            "touser": touser,
            "msgtype": "textcard",
            "agentid": WECOM_AGENT_ID,
            "textcard": {
                "title": title,
                "description": f"访客ID：{visitor_name}\n时间：{now_str}\n内容：{content}",
                "url": jump_url,
                "btntxt": "进入聊天窗口"
            }
        }

        requests.post(
            f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}",
            json=send_data,
            timeout=10
        )

        return {"code": 200, "msg": "发送成功"}

    except Exception as e:
        db.rollback()
        return {"code": 500, "msg": str(e)}

# ===================== 长轮询拉消息 =====================
# ===================== 长轮询拉消息（终极永不卡顿版） =====================
# ===================== 长轮询拉消息（终极完美版） =====================
@chat_router.get("/pull")
async def get_chat_messages(
    visitor_id: str,
    last_id: int = 0
):
    max_wait = 25
    check_interval = 1

    for _ in range(max_wait):
        # 关键：每次循环都 新建数据库会话
        db: Session = next(get_db())
        try:
            msgs = db.query(ChatMessage) \
                .filter(ChatMessage.visitor_id == visitor_id) \
                .filter(ChatMessage.id > last_id) \
                .order_by(ChatMessage.id.asc()).all()

            if msgs:
                data = [{
                    "id": m.id,
                    "visitor_id": m.visitor_id,
                    "sender": m.sender,
                    "content": m.content,
                    "create_time": m.create_time.isoformat() if m.create_time else None,
                    "is_read": m.is_read
                } for m in msgs]
                return {"code": 200, "msg": "成功", "data": data}
        finally:
            db.close()  # 用完立刻关闭会话

        await asyncio.sleep(check_interval)

    return {"code": 200, "msg": "暂无新消息", "data": []}

# ===================== 访客列表长轮询（终极版） =====================
@chat_router.get("/visitor-poll")
async def poll_visitor_list(chat_type: str = "product"):
    max_wait = 25
    check_interval = 1

    def get_snapshot():
        db = next(get_db())
        try:
            visitors = db.query(
                ChatMessage.visitor_id,
                func.max(ChatMessage.create_time).label("last_time")
            ).group_by(ChatMessage.visitor_id).all()
            return str([(vid, lt) for vid, lt in visitors])
        finally:
            db.close()

    first = get_snapshot()

    for _ in range(max_wait):
        current = get_snapshot()
        if current != first:
            break
        await asyncio.sleep(check_interval)

    # 最终返回
    db = next(get_db())
    try:
        visitors = db.query(
            ChatMessage.visitor_id,
            func.max(ChatMessage.create_time).label("last_time")
        ).group_by(ChatMessage.visitor_id).order_by(desc("last_time")).all()

        result = []
        for vid, last_time in visitors:
            if not vid: continue
            if chat_type == "product" and not vid.startswith("wecom_product_"): continue
            if chat_type == "maintain" and not vid.startswith("wecom_maintain_"): continue

            alias = get_friendly_visitor_id(vid)
            last_msg = db.query(ChatMessage) \
                .filter(ChatMessage.visitor_id == vid) \
                .order_by(desc(ChatMessage.create_time)).first()

            unread = db.query(func.count(ChatMessage.id)) \
                .filter(ChatMessage.visitor_id == vid,
                        ChatMessage.sender == "visitor",
                        ChatMessage.is_read == False).scalar() or 0

            result.append({
                "visitor_id": vid,
                "alias_name": alias,
                "chat_type": "product" if "product" in vid else "maintain",
                "unread": unread,
                "last_msg": last_msg.content if last_msg else "",
                "last_msg_time": last_time.strftime("%Y-%m-%d %H:%M:%S") if last_time else ""
            })
        return {"code": 200, "data": result}
    finally:
        db.close()
# ===================== 企微回调 =====================
@chat_router.api_route("/wecom/callback3", methods=["GET", "POST"])
async def wecom_callback(request: Request, db: Session = Depends(get_db)):
    try:
        if request.method == "GET":
            return Response(wxcpt.decrypt(request.query_params.get("echostr", "")), media_type="text/plain")
        body = await request.body()
        root = ET.fromstring(body.decode())
        xml = wxcpt.decrypt(root.find("Encrypt").text)
        msg = ET.fromstring(xml)
        user = msg.find("FromUserName").text
        content = msg.find("Content").text

        visitor_id = user_visitor_map.get(user)
        if visitor_id:
            db.add(ChatMessage(
                visitor_id=visitor_id,
                sender="admin",
                content=content,
                create_time=datetime.now(),
                is_read=False
            ))
            db.commit()
    except:
        pass
    return PlainTextResponse("success")

# ===================== 访客列表 =====================
@chat_router.get("/visitor-list")
async def get_visitor_list(
    chat_type: str = "product",
    db: Session = Depends(get_db)
):
    try:
        visitors = db.query(
            ChatMessage.visitor_id,
            func.max(ChatMessage.create_time).label("last_time")
        ).group_by(ChatMessage.visitor_id)\
         .order_by(desc("last_time")).all()

        result = []

        for vid, last_time in visitors:
            if not vid:
                continue

            if chat_type == "product":
                if not vid.startswith("wecom_product_"):
                    continue
            if chat_type == "maintain":
                if not vid.startswith("wecom_maintain_"):
                    continue

            if vid.startswith("wecom_product_"):
                ctype = "product"
            elif vid.startswith("wecom_maintain_"):
                ctype = "maintain"
            else:
                continue

            alias = get_friendly_visitor_id(vid)

            last_msg = db.query(ChatMessage)\
                .filter(ChatMessage.visitor_id == vid)\
                .order_by(desc(ChatMessage.create_time))\
                .first()

            try:
                unread = db.query(func.count(ChatMessage.id))\
                    .filter(ChatMessage.visitor_id == vid)\
                    .filter(ChatMessage.sender == "visitor")\
                    .filter(ChatMessage.is_read == False)\
                    .scalar() or 0
            except:
                unread = 0

            last_content = last_msg.content if last_msg else ""
            last_time_str = last_time.strftime("%Y-%m-%d %H:%M:%S") if last_time else ""

            result.append({
                "visitor_id": vid,
                "alias_name": alias,
                "chat_type": ctype,
                "unread": unread,
                "last_msg": last_content,
                "last_msg_time": last_time_str
            })

        return {"code": 200, "data": result}
    except Exception as e:
        print("visitor-list error:", e)
        return {"code": 200, "data": []}

@chat_router.delete("/clear-by-visitor")
async def clear_chat_by_visitor(
    visitor_id: str,
    db: Session = Depends(get_db)
):
    try:
        db.query(ChatMessage)\
          .filter(ChatMessage.visitor_id == visitor_id)\
          .delete()
        db.commit()
        return {"code": 200, "msg": "聊天记录已清空"}
    except Exception as e:
        db.rollback()
        return {"code": 500, "msg": str(e)}

# ===================== 进入聊天 → 全部标为已读 =====================
@chat_router.post("/mark-read")
async def mark_read(visitor_id: str, db: Session = Depends(get_db)):
    try:
        db.query(ChatMessage)\
            .filter(ChatMessage.visitor_id == visitor_id)\
            .filter(ChatMessage.sender == "visitor")\
            .filter(ChatMessage.is_read == False)\
            .update({"is_read": True})
        db.commit()
    except:
        pass
    return {"code": 200, "msg": "已标为已读"}

# ===================== 获取历史消息 =====================
@chat_router.get("/messages")
async def get_messages(visitor_id: str, db: Session = Depends(get_db)):
    msgs = db.query(ChatMessage)\
        .filter(ChatMessage.visitor_id == visitor_id)\
        .order_by(ChatMessage.id.asc())\
        .all()

    data = [{
        "id": m.id,
        "visitor_id": m.visitor_id,
        "sender": m.sender,
        "content": m.content,
        "create_time": m.create_time.isoformat() if m.create_time else None,
        "is_read": m.is_read
    } for m in msgs]

    return {"code": 200, "data": data}

# ===================== 兼容旧接口 =====================
@chat_router.get("/assign-product-agent")
async def assign_product_agent(visitor_id: str = ""):
    return {"code": 200}

@chat_router.post("/release-product-agent")
async def release_product_agent(data: ChatSendRequest):
    return {"code": 200}

@chat_router.get("/assign-maintain-agent")
async def assign_maintain_agent(visitor_id: str = ""):
    return {"code": 200}

@chat_router.post("/release-maintain-agent")
async def release_maintain_agent(data: ChatSendRequest):
    return {"code": 200}

@chat_router.get("/poll-heartbeat")
async def poll_heartbeat(visitor_id: str, chat_type: str):
    return {"code": 200}