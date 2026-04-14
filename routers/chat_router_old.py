from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from database import get_db
import hashlib
import xml.etree.ElementTree as ET
import requests
from models.chat_model import ChatMessage
from datetime import datetime
from pydantic import BaseModel

chat_router = APIRouter(prefix="/chat", tags=["在线客服"])

# ===================== 微信配置 =====================
WECHAT_APPID = "wx5a4dca819a44304a"
WECHAT_APPSECRET = "8b4d1195870d989aa5d8878453c14696"
WECHAT_TOKEN = "123456"
ADMIN_OPENID = "ovnAZ6VJhWBzj1Gyg4MR8czK1RGI"

# ===================== JSON 请求模型 =====================
class ChatSendRequest(BaseModel):
    visitor_id: str
    sender: str
    content: str

# -------------------------- 微信签名 --------------------------
def check_wechat_signature(signature: str, timestamp: str, nonce: str) -> bool:
    if not all([signature, timestamp, nonce, WECHAT_TOKEN]):
        return False
    tmp_list = sorted([WECHAT_TOKEN, timestamp, nonce], key=str)
    tmp_str = "".join(tmp_list)
    sha1 = hashlib.sha1()
    sha1.update(tmp_str.encode("utf-8"))
    return sha1.hexdigest() == signature

# -------------------------- 获取 access_token --------------------------
_access_token_cache = None
_access_token_expire_time = 0

def get_access_token() -> str | None:
    global _access_token_cache, _access_token_expire_time
    if _access_token_cache and datetime.now().timestamp() < _access_token_expire_time:
        return _access_token_cache
    try:
        url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={WECHAT_APPID}&secret={WECHAT_APPSECRET}"
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        data = res.json()
        if "access_token" in data:
            _access_token_cache = data["access_token"]
            _access_token_expire_time = datetime.now().timestamp() + data.get("expires_in", 7200) - 300
            return _access_token_cache
        return None
    except Exception as e:
        print(f"获取access_token失败: {e}")
        return None

# -------------------------- 发送消息（JSON 接收） --------------------------
@chat_router.post("/send", summary="客户发送消息")
def send_chat_message(
    data: ChatSendRequest,
    db: Session = Depends(get_db)
):
    visitor_id = data.visitor_id
    sender = data.sender
    content = data.content

    print("==================== 发送接口开始 ====================")
    print(f"访客ID: {visitor_id}")
    print(f"内容: {content}")

    try:
        msg = ChatMessage(
            visitor_id=visitor_id,
            sender=sender,
            content=content,
            create_time=datetime.now()
        )
        db.add(msg)
        db.commit()
        print("【数据库】保存成功")

        # ====== 微信推送 ======
        token = get_access_token()
        if not token:
            return {"code": 200, "msg": "发送成功，但微信推送失败"}

        url = f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={token}"
        send_data = {
            "touser": ADMIN_OPENID,
            "msgtype": "text",
            "text": {"content": f"【官网咨询】\n{content}"}
        }

      
        import json
        payload = json.dumps(send_data, ensure_ascii=False)
        res = requests.post(url, data=payload.encode("utf-8"), headers={
            "Content-Type": "application/json; charset=utf-8"
        })
        wx_result = res.json()
        print(f"【微信】返回结果: {wx_result}")

        return {"code": 200, "msg": "发送成功"}

    except Exception as e:
        db.rollback()
        print(f"【错误】: {e}")
        return {"code": 500, "msg": f"服务器错误: {str(e)}"}

# -------------------------- 拉取消息 --------------------------
@chat_router.get("/pull", summary="获取聊天记录")
def get_chat_messages(visitor_id: str, db: Session = Depends(get_db)):
    try:
        msgs = db.query(ChatMessage)\
            .filter(ChatMessage.visitor_id == visitor_id)\
            .order_by(ChatMessage.id.asc()).all()
        return {"code": 200, "msg": "成功", "data": msgs}
    except Exception as e:
        print(f"拉取消息失败: {e}")
        raise HTTPException(status_code=500, detail="拉取失败")

# -------------------------- 微信公众号回调 --------------------------
@chat_router.api_route("/wechat/callback", methods=["GET", "POST"])
async def wechat_callback(request: Request, db: Session = Depends(get_db)):
    if request.method == "GET":
        signature = request.query_params.get("signature", "")
        timestamp = request.query_params.get("timestamp", "")
        nonce = request.query_params.get("nonce", "")
        echostr = request.query_params.get("echostr", "")
        if check_wechat_signature(signature, timestamp, nonce):
            return PlainTextResponse(content=echostr, status_code=200)
        return PlainTextResponse(content="invalid", status_code=200)

    if request.method == "POST":
        try:
            xml_data = await request.body()
            root = ET.fromstring(xml_data)
            user_openid = root.find("FromUserName").text
            content = root.find("Content").text

            print("==================================================")
            print("用户 OpenID:", user_openid)
            print("用户消息:", content)
            print("==================================================")

            last_msg = db.query(ChatMessage).order_by(ChatMessage.id.desc()).first()
            if last_msg:
                reply = ChatMessage(
                    visitor_id=last_msg.visitor_id,
                    sender="admin",
                    content=content,
                    create_time=datetime.now()
                )
                db.add(reply)
                db.commit()
        except Exception as e:
            print(f"解析失败: {e}")
    return PlainTextResponse(content="success", status_code=200)