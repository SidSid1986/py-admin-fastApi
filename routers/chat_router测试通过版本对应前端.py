from fastapi import Response
import base64
import hashlib
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
import threading

from database import get_db
from models.chat_model import ChatMessage

chat_router = APIRouter(prefix="/chat", tags=["在线客服"])


# ===================== 请求体模型 =====================
class ChatSendRequest(BaseModel):
    visitor_id: str
    sender: str
    content: str
    touser: str = None
    chat_type: str  # product / maintain


# ===================== 微信公众号配置 =====================
WECHAT_APPID = "wx5a4dca819a44304a"
WECHAT_APPSECRET = "8b4d1195870d989aa5d8878453c14696"
WECHAT_TOKEN = "123456"
ADMIN_OPENID = "ovnAZ6VJhWBzj1Gyg4MR8czK1RGI"

# ===================== 企业微信应用1 = 座席1 =====================
WECOM_CORP_ID = "ww5dd0722c15118241"
WECOM_AGENT_ID = 1000023
WECOM_APP_SECRET = "U-t68l_cfpqLWDX-gOQMRZZG4I-3w2libwSWWvYoMgA"
WECOM_TOKEN = "wecom123456"
WECOM_AES_KEY = "2dn14NjffkTxxCxpk1J82MAcW6hXlmYjAx1IkcqHdWY"

# ===================== 企业微信应用2 = 座席2 =====================
WECOM_AGENT_ID2 = 1000029
WECOM_APP_SECRET2 = "SmtH2at28ZsbbdVEWEawnEGfhOYUQpWWHwxFV1oYMRc"
WECOM_TOKEN2 = "wecom123456"
WECOM_AES_KEY2 = "2dn14NjffkTxxCxpk1J82MAcW6hXlmYjAx1IkcqHdWY"

# ===================== 4 套独立映射 =====================
user_visitor_p1 = {}
user_visitor_m1 = {}
user_visitor_p2 = {}
user_visitor_m2 = {}


# ===================== 【核心】座席管理器类 =====================
class SeatManager:
    def __init__(self, total_seats=2):
        self.total_seats = total_seats
        self.seats = {}  # {seat_id: {"busy": bool, "visitor_id": str, "heartbeat": float}}
        self.lock = threading.Lock()
        self.last_allocated_seat = 0  # 上次分配的座席ID
        self.HEARTBEAT_TIMEOUT = 30  # 延长超时时间到30秒，避免频繁超时
        # 初始化座席
        for i in range(1, total_seats + 1):
            self.seats[i] = {"busy": False, "visitor_id": None, "heartbeat": 0}

    def get_active_count(self):
        """获取真正活跃的座席数量（未超时的）"""
        now = time.time()
        active_count = 0
        for info in self.seats.values():
            if info["busy"] and (now - info["heartbeat"]) <= self.HEARTBEAT_TIMEOUT:
                active_count += 1
        return active_count

    def clean_expired(self):
        """清理过期的座席"""
        now = time.time()
        expired_count = 0
        for seat_id, info in self.seats.items():
            if info["busy"] and now - info["heartbeat"] > self.HEARTBEAT_TIMEOUT:
                print(f"[DEBUG] 清理过期座席 {seat_id}，访客ID: {info['visitor_id']}")
                self.seats[seat_id] = {"busy": False, "visitor_id": None, "heartbeat": 0}
                expired_count += 1
        if expired_count > 0:
            print(f"[DEBUG] 共清理了 {expired_count} 个过期座席")

    def get_available_seats(self):
        """获取可用座席列表（排除超时座席）"""
        now = time.time()
        available = []
        for seat_id, info in self.seats.items():
            # 座席空闲 或者 座席忙碌但已超时
            if not info["busy"] or (info["busy"] and now - info["heartbeat"] > self.HEARTBEAT_TIMEOUT):
                available.append(seat_id)
        print(f"[DEBUG] 可用座席: {available}")
        return available

    def allocate_seat(self, visitor_id):
        """分配座席给访客"""
        with self.lock:
            print(f"[DEBUG] 尝试为访客 {visitor_id} 分配座席")

            # 检查该访客是否正在使用座席（用于心跳续期）
            for seat_id, info in self.seats.items():
                if info["visitor_id"] == visitor_id and info["busy"]:
                    print(f"[DEBUG] 访客 {visitor_id} 已在使用座席 {seat_id}，更新心跳")
                    self.seats[seat_id]["heartbeat"] = time.time()
                    self.last_allocated_seat = seat_id
                    return {"code": 200, "agent": seat_id}

            # 获取当前活跃数量
            active_count = self.get_active_count()
            print(f"[DEBUG] 当前活跃座席数: {active_count}, 最大限制: {self.total_seats}")

            # 检查是否已达到最大活跃数量
            if active_count >= self.total_seats:
                print(f"[DEBUG] 活跃座席已达上限 ({active_count}/{self.total_seats})，返回繁忙")
                return {"code": 503, "msg": "客服繁忙，请稍后"}

            # 获取可用座席（包括清理超时座席后的可用座席）
            self.clean_expired()  # 清理过期座席

            # 再次检查活跃数量，因为清理后可能有变化
            active_count_after_clean = self.get_active_count()
            if active_count_after_clean >= self.total_seats:
                print(f"[DEBUG] 清理后活跃座席仍达上限 ({active_count_after_clean}/{self.total_seats})，返回繁忙")
                return {"code": 503, "msg": "客服繁忙，请稍后"}

            # 查找空闲座席
            for seat_id, info in self.seats.items():
                if not info["busy"]:  # 只分配完全空闲的座席
                    print(f"[DEBUG] 分配座席 {seat_id} 给访客 {visitor_id}")
                    self.seats[seat_id]["busy"] = True
                    self.seats[seat_id]["visitor_id"] = visitor_id
                    self.seats[seat_id]["heartbeat"] = time.time()
                    self.last_allocated_seat = seat_id
                    print(f"[DEBUG] 座席分配完成，当前状态: {[f'{sid}:{info}' for sid, info in self.seats.items()]}")
                    return {"code": 200, "agent": seat_id}

            print(f"[DEBUG] 无法找到空闲座席，返回繁忙")
            return {"code": 503, "msg": "客服繁忙，请稍后"}

    def release_seat(self, seat_id):
        """释放座席"""
        with self.lock:
            if seat_id in self.seats:
                old_visitor = self.seats[seat_id]["visitor_id"]
                self.seats[seat_id] = {"busy": False, "visitor_id": None, "heartbeat": 0}
                print(f"[DEBUG] 座席 {seat_id} 已释放，原访客: {old_visitor}")
                print(f"[DEBUG] 释放后状态: {[f'{sid}:{info}' for sid, info in self.seats.items()]}")

    def update_heartbeat(self, visitor_id):
        """更新访客心跳"""
        with self.lock:
            for seat_id, info in self.seats.items():
                if info["visitor_id"] == visitor_id and info["busy"]:
                    self.seats[seat_id]["heartbeat"] = time.time()
                    print(f"[DEBUG] 更新访客 {visitor_id} 在座席 {seat_id} 的心跳")


# 创建座席管理器实例
product_seat_manager = SeatManager(total_seats=2)
maintain_seat_manager = SeatManager(total_seats=2)


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

    try:
        msg = ChatMessage(
            visitor_id=visitor_id,
            sender=sender,
            content=content,
            create_time=datetime.now()
        )
        db.add(msg)
        db.commit()

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
        requests.post(url, data=payload.encode("utf-8"), headers={"Content-Type": "application/json; charset=utf-8"})
        return {"code": 200, "msg": "发送成功"}

    except Exception as e:
        db.rollback()
        print(f"【错误】: {e}")
        return {"code": 500, "msg": f"服务器错误: {str(e)}"}


# -------------------------- 统一发送到企微 --------------------------
@chat_router.post("/send_to_wecom", summary="统一发送：产品/维保 + 座席1/座席2")
async def send_chat_to_wecom(
        data: ChatSendRequest,
        db: Session = Depends(get_db)
):
    visitor_id = data.visitor_id
    sender = data.sender
    content = data.content
    touser = data.touser
    chat_type = data.chat_type

    try:
        msg = ChatMessage(
            visitor_id=visitor_id,
            sender=sender,
            content=content,
            touser=touser,
            create_time=datetime.now()
        )
        db.add(msg)
        db.commit()

        if chat_type == "product":
            if "agent1" in visitor_id:
                user_visitor_p1[touser] = visitor_id
            else:
                user_visitor_p2[touser] = visitor_id
        elif chat_type == "maintain":
            if "agent1" in visitor_id:
                user_visitor_m1[touser] = visitor_id
            else:
                user_visitor_m2[touser] = visitor_id

        agentid = WECOM_AGENT_ID if "agent1" in visitor_id else WECOM_AGENT_ID2
        token = get_wecom_access_token() if "agent1" in visitor_id else get_wecom_access_token2()

        if not token:
            return {"code": 200, "msg": "消息已保存，企微推送失败"}

        title = "【产品咨询】" if chat_type == "product" else "【维保咨询】"
        send_data = {
            "touser": touser,
            "msgtype": "text",
            "agentid": agentid,
            "text": {"content": f"{title}\n访客ID：{visitor_id}\n内容：{content}"}
        }
        requests.post(f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}", json=send_data,
                      timeout=10)
        return {"code": 200, "msg": "发送成功"}

    except Exception as e:
        db.rollback()
        return {"code": 500, "msg": str(e)}


# -------------------------- 长轮询拉取消息 --------------------------
@chat_router.get("/pull", summary="长轮询获取聊天记录")
async def get_chat_messages(
        visitor_id: str,
        last_id: int = 0,
        db: Session = Depends(get_db)
):
    max_wait = 25
    check_interval = 1
    for _ in range(max_wait):
        db.commit()
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
                "create_time": m.create_time.isoformat() if m.create_time else None
            } for m in msgs]
            return {"code": 200, "msg": "成功", "data": data}
        await asyncio.sleep(check_interval)
    return {"code": 200, "msg": "暂无新消息", "data": []}


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
            last_msg = db.query(ChatMessage).order_by(ChatMessage.id.desc()).first()
            if last_msg:
                reply = ChatMessage(visitor_id=last_msg.visitor_id, sender="admin", content=content,
                                    create_time=datetime.now())
                db.add(reply)
                db.commit()
        except:
            pass
    return PlainTextResponse("success")


# -------------------------- 加解密工具 --------------------------
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
wxcpt2 = WeComCrypto(WECOM_TOKEN2, WECOM_AES_KEY2, WECOM_CORP_ID)

# -------------------------- 应用token --------------------------
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


_wecom_token_cache2 = None
_wecom_expire_time2 = 0


def get_wecom_access_token2():
    global _wecom_token_cache2, _wecom_expire_time2
    now = time.time()
    if _wecom_token_cache2 and now < _wecom_expire_time2:
        return _wecom_token_cache2
    url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={WECOM_CORP_ID}&corpsecret={WECOM_APP_SECRET2}"
    data = requests.get(url, timeout=10).json()
    if "access_token" in data:
        _wecom_token_cache2 = data["access_token"]
        _wecom_expire_time2 = now + data.get("expires_in", 7200) - 300
        return _wecom_token_cache2
    return None


# -------------------------- 应用1 回调 --------------------------
@chat_router.api_route("/wecom/callback", methods=["GET", "POST"])
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

        vid = user_visitor_p1.get(user) or user_visitor_m1.get(user)
        if vid:
            db.add(ChatMessage(visitor_id=vid, sender="admin", content=content, create_time=datetime.now()))
            db.commit()
    except:
        pass
    return PlainTextResponse("success")


# -------------------------- 应用2 回调 --------------------------
@chat_router.api_route("/wecom/callback2", methods=["GET", "POST"])
async def wecom_callback2(request: Request, db: Session = Depends(get_db)):
    try:
        if request.method == "GET":
            return Response(wxcpt2.decrypt(request.query_params.get("echostr", "")), media_type="text/plain")
        body = await request.body()
        root = ET.fromstring(body.decode())
        xml = wxcpt2.decrypt(root.find("Encrypt").text)
        msg = ET.fromstring(xml)
        user = msg.find("FromUserName").text
        content = msg.find("Content").text

        vid = user_visitor_p2.get(user) or user_visitor_m2.get(user)
        if vid:
            db.add(ChatMessage(visitor_id=vid, sender="admin", content=content, create_time=datetime.now()))
            db.commit()
    except:
        pass
    return PlainTextResponse("success")


# ======================== 座席分配接口 ========================
@chat_router.get("/assign-product-agent")
async def assign_product_agent(visitor_id: str = ""):
    result = product_seat_manager.allocate_seat(visitor_id)
    print(f"[DEBUG] 产品座席分配结果: {result}")
    return result


@chat_router.post("/release-product-agent")
async def release_product_agent(agent: int):
    product_seat_manager.release_seat(agent)
    return {"code": 200}


@chat_router.get("/assign-maintain-agent")
async def assign_maintain_agent(visitor_id: str = ""):
    result = maintain_seat_manager.allocate_seat(visitor_id)
    print(f"[DEBUG] 维保座席分配结果: {result}")
    return result


@chat_router.post("/release-maintain-agent")
async def release_maintain_agent(agent: int):
    maintain_seat_manager.release_seat(agent)
    return {"code": 200}


@chat_router.get("/poll-heartbeat")
async def poll_heartbeat(visitor_id: str, chat_type: str):
    if chat_type == "product":
        product_seat_manager.update_heartbeat(visitor_id)
    elif chat_type == "maintain":
        maintain_seat_manager.update_heartbeat(visitor_id)
    return {"code": 200}