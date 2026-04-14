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

# ===================== 拉取消息 =====================


@chat_router.get("/pull", summary="长轮询获取聊天记录")
async def get_chat_messages(
    visitor_id: str,
    last_id: int = 0,  # 前端传最后一条消息ID
    db: Session = Depends(get_db)
):
    try:
        # 最多等待30秒
        for _ in range(30):
            # 只查比 last_id 大的新消息
            msgs = db.query(ChatMessage)\
                .filter(ChatMessage.visitor_id == visitor_id)\
                .filter(ChatMessage.id > last_id)\
                .order_by(ChatMessage.id.asc()).all()

            if msgs:
                # 有新消息  立刻返回
                return {"code": 200, "msg": "成功", "data": msgs}

            # 没消息  等1秒再查
            await asyncio.sleep(1)

        # 30秒没消息  返回空
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

# -------------------------- 企业微信工具：AES解密（必须） --------------------------
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
        # ----------------------
        # AES-256-CBC
        # OPENSSL_ZERO_PADDING
        # ----------------------
        import base64
        from Crypto.Cipher import AES

        cipher = AES.new(self.aes_key, AES.MODE_CBC, self.iv)
        raw = cipher.decrypt(base64.b64decode(encrypted))
        decrypted = self.decode(raw)

        # 取内容
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


# -------------------------- 企业微信 access_token 缓存 --------------------------
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

# -------------------------- 企业微信发送接口 --------------------------
@chat_router.post("/send_to_wecom", summary="【独立】客户发送消息 -> 企业微信")
async def send_chat_to_wecom(
    data: ChatSendRequest,
    db: Session = Depends(get_db)
):
    visitor_id = data.visitor_id
    sender = data.sender
    content = data.content

    print("==================== 【企业微信】发送接口开始 ====================")
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
        print("【企业微信】数据库保存成功")

        token = get_wecom_access_token()
        if not token:
            return {"code": 200, "msg": "消息已保存，企业微信推送失败"}

        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
        send_data = {
            "touser": ADMIN_WECOM_USERID,
            "msgtype": "text",
            "agentid": WECOM_AGENT_ID,
            "text": {
                "content": f"【网站咨询】\n访客ID：{visitor_id}\n内容：{content}"
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


# -------------------------- 最终必过版：强制返回 TEXT 纯文本 --------------------------

# @chat_router.api_route("/wecom/callback", methods=["GET", "POST"])
# async def wecom_callback(request: Request, db: Session = Depends(get_db)):
#     if request.method == "GET":
#         try:
#             echostr = request.query_params.get("echostr")
#             # --------------------------
#             # 官方标准解密
#             # --------------------------
#             msg = wxcpt.decrypt(echostr)
#             print("最终解密明文:", msg)
#
#             # --------------------------
#             # 必须纯文本返回！
#             # --------------------------
#             return Response(
#                 content=msg,
#                 media_type="text/plain"
#             )
#         except Exception as e:
#             print("解密错误:", e)
#             return Response("", media_type="text/plain")
#
#     return Response("", media_type="text/plain")

# -------------------------- 企业微信回调：验证 + 接收消息 --------------------------
@chat_router.api_route("/wecom/callback", methods=["GET", "POST"])
async def wecom_callback(request: Request, db: Session = Depends(get_db)):
    try:
        # ==================== GET：企业微信后台验证 ====================
        if request.method == "GET":
            echostr = request.query_params.get("echostr", "")
            msg = wxcpt.decrypt(echostr)
            print("✅ 企业微信验证成功:", msg)
            return Response(content=msg, media_type="text/plain")

        # ==================== POST：接收手机用户发送的消息 ====================
        if request.method == "POST":
            # 1. 获取加密内容
            body = await request.body()
            root = ET.fromstring(body.decode("utf-8"))
            encrypt = root.find("Encrypt").text

            # 2. 解密
            xml_content = wxcpt.decrypt(encrypt)
            msg_root = ET.fromstring(xml_content)

            # 3. 解析消息
            from_user = msg_root.find("FromUserName").text
            content = msg_root.find("Content").text
            print(f"收到手机消息：{content}")

            # 4. 保存到数据库 → 网页就能看到！
            last_msg = db.query(ChatMessage).order_by(ChatMessage.id.desc()).first()
            if last_msg:
                new_msg = ChatMessage(
                    visitor_id=last_msg.visitor_id,
                    sender="admin",
                    content=content,
                    create_time=datetime.now()
                )
                db.add(new_msg)
                db.commit()

            return PlainTextResponse("success", media_type="text/plain")

    except Exception as e:
        print("❌ 回调错误:", e)
        return PlainTextResponse("success", media_type="text/plain")