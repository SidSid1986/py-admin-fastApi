from fastapi import Response
import base64
import hashlib
import json
import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime
import requests
from Crypto.Cipher import AES
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.chat_model import ChatMessage

chat_router = APIRouter(prefix="/chat", tags=["在线客服"])

# ===================== 微信公众号配置 =====================
WECHAT_APPID = "wx5a4dca819a44304a"
WECHAT_APPSECRET = "8b4d1195870d989aa5d8878453c14696"
WECHAT_TOKEN = "123456"
ADMIN_OPENID = "ovnAZ6VJhWBzj1Gyg4MR8czK1RGI"

# ===================== 企业微信配置 =====================
WECOM_CORP_ID = "ww5dd0722c15118241"
WECOM_AGENT_ID = 1000023
WECOM_APP_SECRET = "U-t68l_cfpqLWDX-gOQMRZZG4I-3w2libwSWWvYoMgA"
ADMIN_WECOM_USERID = "b52369d4a0b2a0d1ee2376d224a6cf74"
WECOM_TOKEN = "wecom123456"
WECOM_AES_KEY = "2dn14NjffkTxxCxpk1J82MAcW6hXlmYjAx1IkcqHdWY"

# 全局缓存：企微用户ID → 对应的网页访客ID
user_visitor_map = {}

# ===================== JSON 请求模型 =====================
class ChatSendRequest(BaseModel):
    visitor_id: str
    sender: str
    content: str
    touser: str = None  # 可选字段

# -------------------------- 微信签名 --------------------------
def check_wechat_signature(signature: str, timestamp: str, nonce: str) -> bool:
    if not all([signature, timestamp, nonce, WECHAT_TOKEN]):
        return False
    tmp_list = sorted([WECHAT_TOKEN, timestamp, nonce], key=str)
    tmp_str = "".join(tmp_list)
    sha1 = hashlib.sha1()
    sha1.update(tmp_str.encode("utf-8"))
    return sha1.hexdigest() == signature

# -------------------------- 公众号 access_token --------------------------
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

# -------------------------- 公众号发送消息 --------------------------
@chat_router.post("/send", summary="客户发送消息 -> 公众号")
def send_chat_message(
    data: ChatSendRequest,
    db: Session = Depends(get_db)
):
    visitor_id = data.visitor_id
    sender = data.sender
    content = data.content

    print("==================== 【公众号】发送接口开始 ====================")
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

        token = get_access_token()
        if not token:
            return {"code": 200, "msg": "发送成功，但微信推送失败"}

        url = f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={token}"
        send_data = {
            "touser": ADMIN_OPENID,
            "msgtype": "text",
            "text": {"content": f"【官网咨询】\n{content}"}
        }

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

# -------------------------- 动态发送到企业微信区分接收者 touser） --------------------------
@chat_router.post("/send_to_wecom", summary="【动态发送】客户发送消息 -> 企业微信指定成员")
async def send_chat_to_wecom(
    data: ChatSendRequest,
    db: Session = Depends(get_db)
):
    visitor_id = data.visitor_id
    sender = data.sender
    content = data.content
    touser = data.touser

    print("==================== 【企业微信】动态发送 ====================")
    print(f"访客ID: {visitor_id}")
    print(f"接收人: {touser}")
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
        user_visitor_map[touser] = visitor_id
        token = get_wecom_access_token()
        if not token:
            return {"code": 200, "msg": "消息已保存，企业微信推送失败"}

        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
        send_data = {
            "touser": touser,
            "msgtype": "text",
            "agentid": WECOM_AGENT_ID,
            "text": {
                "content": f"【网站咨询】\n访客ID：{visitor_id}\n内容：{content}"
                # "content": f"【网站咨询】\n内容：{content}"
        }
        }

        res = requests.post(url, json=send_data, timeout=10)
        result = res.json()
        print(f"【企业微信】返回结果：{result}")

        return {"code": 200, "msg": "发送成功"}

    except Exception as e:
        db.rollback()
        print(f"【企业微信错误】: {e}")
        return {"code": 500, "msg": f"企业微信接口错误：{str(e)}"}

# ===================== 拉取消息 =====================
@chat_router.get("/pull", summary="长轮询获取聊天记录")
async def get_chat_messages(
    visitor_id: str,
    last_id: int = 0,
    db: Session = Depends(get_db)
):
    max_wait = 25
    check_interval = 1

    try:
        for _ in range(max_wait):

            db.commit()

            msgs = db.query(ChatMessage)\
                .filter(ChatMessage.visitor_id == visitor_id)\
                .filter(ChatMessage.id > last_id)\
                .order_by(ChatMessage.id.asc()).all()

            if msgs:
                data = [{
                    "id": m.id,
                    "visitor_id": m.visitor_id,
                    "sender": m.sender,
                    "content": m.content,
                    "create_time": m.create_time.isoformat() if m.create_time else None
                } for m in msgs]
                return {"code": 200, "msg": "成功", "data": data}

            await asyncio.sleep(check_interval)

        return {"code": 200, "msg": "暂无新消息", "data": []}

    except Exception as e:
        print(f"长轮询错误: {e}")
        return {"code": 500, "msg": "拉取失败"}

# -------------------------- 公众号回调 --------------------------
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
            print("【公众号回调】用户 OpenID:", user_openid)
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


# ===================== 企业微信部分 =====================

class WeComCrypto:
    def __init__(self, token, encoding_aes_key, corp_id):
        self.token = token
        self.corp_id = corp_id
        self.aes_key = base64.b64decode(encoding_aes_key + "=")
        self.iv = self.aes_key[:16]

    def decode(self, text):
        pad = ord(text[-1:])
        if pad < 1 or pad > 32:
            pad = 0
        return text[:-pad]

    def decrypt(self, encrypted):
        import base64
        from Crypto.Cipher import AES

        cipher = AES.new(self.aes_key, AES.MODE_CBC, self.iv)
        raw = cipher.decrypt(base64.b64decode(encrypted))
        decrypted = self.decode(raw)

        if len(decrypted) < 16:
            return ""
        content = decrypted[16:]
        xml_len = int.from_bytes(content[:4], byteorder='big', signed=False)
        xml_content = content[4:4 + xml_len].decode('utf-8')
        from_corpid = content[4 + xml_len:].decode('utf-8')

        if from_corpid != self.corp_id:
            return ""
        return xml_content


wxcpt = WeComCrypto(
    token=WECOM_TOKEN,
    encoding_aes_key=WECOM_AES_KEY,
    corp_id=WECOM_CORP_ID
)

_wecom_token_cache = None
_wecom_expire_time = 0

def get_wecom_access_token():
    global _wecom_token_cache, _wecom_expire_time
    now = datetime.now().timestamp()

    if _wecom_token_cache and now < _wecom_expire_time:
        return _wecom_token_cache

    url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={WECOM_CORP_ID}&corpsecret={WECOM_APP_SECRET}"
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
        if "access_token" in data:
            _wecom_token_cache = data["access_token"]
            _wecom_expire_time = now + data.get("expires_in", 7200) - 300
            return _wecom_token_cache
    except Exception as e:
        print(f"获取企业微信token失败：{e}")
    return None

# -------------------------- 企业微信回调 --------------------------

@chat_router.api_route("/wecom/callback", methods=["GET", "POST"])
async def wecom_callback(request: Request, db: Session = Depends(get_db)):
    try:
        if request.method == "GET":
            echostr = request.query_params.get("echostr", "")
            msg = wxcpt.decrypt(echostr)
            print("✅ 企业微信验证成功:", msg)
            return Response(content=msg, media_type="text/plain")

        if request.method == "POST":
            body = await request.body()
            root = ET.fromstring(body.decode("utf-8"))
            encrypt = root.find("Encrypt").text
            xml_content = wxcpt.decrypt(encrypt)
            msg_root = ET.fromstring(xml_content)

            from_user = msg_root.find("FromUserName").text
            content = msg_root.find("Content").text
            print(f"收到微信消息 from_user={from_user}, content={content}")

            # ======================
            # 核心修复：取正确ID
            # ======================
            visitor_id = user_visitor_map.get(from_user)
            if not visitor_id:
                print("❌ 找不到对应访客，忽略消息")
                return PlainTextResponse("success")

            # 保存到对应窗口
            new_msg = ChatMessage(
                visitor_id=visitor_id,
                sender="admin",
                content=content,
                create_time=datetime.now()
            )
            db.add(new_msg)
            db.commit()

            return PlainTextResponse("success")

    except Exception as e:
        print("回调错误:", e)
        return PlainTextResponse("success")