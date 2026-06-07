"""
企业微信消息处理模块

处理企业微信回调消息的解析、签名校验、加解密、回复构建。
支持加密模式（AES-256-CBC），需要 pycryptodome。

协议参考: https://developer.work.weixin.qq.com/document/path/90930
"""

import base64
import hashlib
import os
import struct
import time
from xml.etree import ElementTree as ET

from Crypto.Cipher import AES


# ────────────────────────────────────────────
# 签名校验
# ────────────────────────────────────────────

def calc_signature(token: str, timestamp: str, nonce: str, enc_msg: str = "") -> str:
    """
    计算企业微信回调签名

    将 token, timestamp, nonce, enc_msg 按字典序排序后拼接，SHA1 哈希。
    """
    parts = sorted([token, timestamp, nonce, enc_msg])
    raw = "".join(parts)
    return hashlib.sha1(raw.encode()).hexdigest()


# ────────────────────────────────────────────
# AES 加解密（加密模式）
# ────────────────────────────────────────────

def _aes_key(encoding_aes_key: str) -> bytes:
    """EncodingAESKey (43 字符 Base64) → 32 字节 AES 密钥"""
    return base64.b64decode(encoding_aes_key + "=")


def decrypt(encrypted: str, encoding_aes_key: str) -> str:
    """
    AES-256-CBC 解密

    输入: Base64 编码的密文字符串
    输出: 解密后的明文字符串

    明文格式: random(16 bytes) + msg_len(4 bytes, 大端) + msg + corp_id

    抛出 ValueError 如果解密失败或 corp_id 不匹配。
    """
    key = _aes_key(encoding_aes_key)
    cipher = AES.new(key, AES.MODE_CBC, iv=key[:16])
    plaintext = cipher.decrypt(base64.b64decode(encrypted))

    # 去除 PKCS#7 填充
    pad = plaintext[-1]
    plaintext = plaintext[:-pad]

    # 解析: random(16) + msg_len(4) + msg + corp_id
    content = plaintext[16:]          # 跳过 16 字节随机串
    msg_len = struct.unpack(">I", content[:4])[0]  # 大端 4 字节长度
    msg = content[4:4 + msg_len].decode("utf-8")
    # content[4+msg_len:] 是 corp_id，解密时不校验

    return msg


def encrypt(msg: str, encoding_aes_key: str, corp_id: str) -> str:
    """
    AES-256-CBC 加密

    输入: 明文消息、EncodingAESKey、企业 CorpID
    输出: Base64 编码的密文字符串
    """
    key = _aes_key(encoding_aes_key)

    # 构造明文: random(16) + msg_len(4) + msg + corp_id
    random_bytes = os.urandom(16)
    msg_bytes = msg.encode("utf-8")
    msg_len = struct.pack(">I", len(msg_bytes))  # 大端 4 字节
    plaintext = random_bytes + msg_len + msg_bytes + corp_id.encode("utf-8")

    # PKCS#7 填充到 32 字节倍数
    block_size = 32
    pad = block_size - len(plaintext) % block_size
    plaintext += bytes([pad] * pad)

    cipher = AES.new(key, AES.MODE_CBC, iv=key[:16])
    return base64.b64encode(cipher.encrypt(plaintext)).decode()


# ────────────────────────────────────────────
# XML 消息解析与构建
# ────────────────────────────────────────────

def parse_message(xml_body: str) -> dict:
    """
    解析明文 XML 消息体

    输入:
        <xml>
          <ToUserName><![CDATA[corp_id]]></ToUserName>
          <FromUserName><![CDATA[user_id]]></FromUserName>
          <CreateTime>1234567890</CreateTime>
          <MsgType><![CDATA[text]]></MsgType>
          <Content><![CDATA[报销流程]]></Content>
          <MsgId>123456</MsgId>
        </xml>

    返回消息字段 dict，解析失败返回空 dict。
    """
    try:
        root = ET.fromstring(xml_body)
        return {child.tag: child.text or "" for child in root}
    except ET.ParseError:
        return {}


def parse_encrypted_message(xml_body: str, encoding_aes_key: str) -> dict:
    """
    解析加密 XML 消息体

    输入:
        <xml>
          <ToUserName><![CDATA[...]]></ToUserName>
          <Encrypt><![CDATA[base64_ciphertext]]></Encrypt>
        </xml>

    解密后返回内部的明文消息 dict。
    """
    root = ET.fromstring(xml_body)
    enc = root.find("Encrypt")
    if enc is None or not enc.text:
        return {}
    plain_xml = decrypt(enc.text, encoding_aes_key)
    return parse_message(plain_xml)


def build_text_reply(to_user: str, from_user: str, content: str) -> str:
    """
    构建明文文本回复 XML
    """
    return (
        "<xml>"
        f"<ToUserName><![CDATA[{to_user}]]></ToUserName>"
        f"<FromUserName><![CDATA[{from_user}]]></FromUserName>"
        f"<CreateTime>{int(time.time())}</CreateTime>"
        "<MsgType><![CDATA[text]]></MsgType>"
        f"<Content><![CDATA[{content}]]></Content>"
        "</xml>"
    )


def build_encrypted_reply(
    to_user: str,
    from_user: str,
    content: str,
    encoding_aes_key: str,
    corp_id: str,
    token: str,
) -> str:
    """
    构建加密文本回复 XML

    返回完整的加密回复 XML，包含 Encrypt 和 MsgSignature。
    """
    # 1. 先构建明文回复
    plain_xml = build_text_reply(to_user, from_user, content)

    # 2. 加密
    encrypted = encrypt(plain_xml, encoding_aes_key, corp_id)

    # 3. 计算签名
    timestamp = str(int(time.time()))
    nonce = hashlib.md5(os.urandom(16)).hexdigest()[:16]
    signature = calc_signature(token, timestamp, nonce, encrypted)

    # 4. 构建加密回复 XML
    return (
        "<xml>"
        f"<Encrypt><![CDATA[{encrypted}]]></Encrypt>"
        f"<MsgSignature><![CDATA[{signature}]]></MsgSignature>"
        f"<TimeStamp>{timestamp}</TimeStamp>"
        f"<Nonce><![CDATA[{nonce}]]></Nonce>"
        "</xml>"
    )


# ────────────────────────────────────────────
# 搜索结果格式化
# ────────────────────────────────────────────

def format_search_reply(query: str, results: list[dict], web_url: str = "") -> str:
    """
    将搜索结果格式化为适合企业微信聊天窗口的文本
    """
    if not results:
        base = f"未找到与「{query}」相关的文档。"
        if web_url:
            base += f"\n\n试试换个关键词，或访问 Web 页面搜索：{web_url}"
        return base

    lines = [f"找到 {len(results)} 条相关文档:"]
    lines.append("")

    for i, r in enumerate(results[:3], 1):
        snippet = r["snippet"].replace("\n", " ")[:100]
        lines.append(f"{i}. 【{r['title']}】")
        lines.append(f"   {snippet}...")
        lines.append("")

    if web_url:
        lines.append(f"查看更多: {web_url}")

    return "\n".join(lines)
