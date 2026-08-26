# -*- coding: utf-8 -*-
"""项目授权码：锁项目 + 锁机器（独立于 HRVision 公司认证，公司认证零改动）。

授权码形态（内嵌项目字段 + 高加密等级）：
    签发（厂商）：JSON{project, issued, expire, quota, used, hardware}
        → Ed25519 签名（厂商私钥，防伪造：校验端只有公钥，逆向也造不出码）
        → AES-256-GCM 加密（机密性 + 完整性：篡改即解密失败）
        → base64 授权码字符串

    校验（项目侧）：base64 解码 → AES-256-GCM 解密 → Ed25519 验签
        → 项目名匹配（中文 utf-8）→ 未过期 → 配额未超 → 硬件匹配（锁机器）

用法：
    # 签发（厂商侧，GenProjectLicense.py 封装）
    code = ProjectLicense.generate("视觉检测项目", days=365, quota=100)

    # 校验（项目侧一行；code 缺省读环境变量 HR_PROJECT_LICENSE）
    ok = ProjectLicense.check_project_license("视觉检测项目")

密钥管理：
    签发侧：ed25519 私钥 + AES 密钥（文件 keys/，厂商持有，不外发）
    校验侧：ed25519 公钥 + AES 密钥内嵌本模块（混淆存储）；
            可被环境变量 HR_PROJECT_PUBKEY / HR_PROJECT_AESKEY 覆盖（动态分发场景）
    注意：AES 密钥在校验端可被逆向（机密性有限），防伪由 Ed25519 签名保证
    （私钥仅厂商持有）——如需更强可把校验端 Cython 编译（密钥进编译产物）。

依赖：cryptography（pip install cryptography；HRVisionSuite 已加入依赖）。
"""
import base64
import hashlib
import json
import os
import sys
import time

from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (Ed25519PrivateKey,
                                                               Ed25519PublicKey)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# ------------------------------------------------------------------
# 密钥（校验端内嵌，混淆存储；签发端从 keys/ 目录加载）
# ------------------------------------------------------------------

# 校验端默认密钥（厂商签发工具首次运行生成并回填此处；也可用环境变量覆盖）
_DEFAULT_PUBKEY = "020d6b206e20162a710c333317166e1d0a630c3034301e3663716d332a190e1933380b282908751829146267"
_DEFAULT_AESKEY = "1037110f2a343b220f03383c2e710a13207133711815023b696b08751962682c310a1c3d39302e6b363e2d67"

# 混淆/解混淆（防直接搜索密钥字符串）：hex 编码保证 ASCII 安全，可内嵌源码
_MASK = 0x5A

def _obf(s: str) -> str:
    return bytes(ord(c) ^ _MASK for c in s).hex()

def _unobf(s: str) -> str:
    return "".join(chr(b ^ _MASK) for b in bytes.fromhex(s))


def _get_pubkey() -> bytes:
    """校验端公钥：环境变量优先，其次模块内嵌（混淆）。"""
    v = os.environ.get("HR_PROJECT_PUBKEY", "")
    if v:
        return base64.b64decode(v)
    if _DEFAULT_PUBKEY:
        return base64.b64decode(_unobf(_DEFAULT_PUBKEY))
    raise RuntimeError("项目授权码公钥未配置（HR_PROJECT_PUBKEY 或模块内嵌）")


def _get_aeskey() -> bytes:
    """校验端 AES 密钥：环境变量优先，其次模块内嵌（混淆）。"""
    v = os.environ.get("HR_PROJECT_AESKEY", "")
    if v:
        return base64.b64decode(v)
    if _DEFAULT_AESKEY:
        return base64.b64decode(_unobf(_DEFAULT_AESKEY))
    raise RuntimeError("项目授权码 AES 密钥未配置（HR_PROJECT_AESKEY 或模块内嵌）")


# ------------------------------------------------------------------
# 硬件码（锁机器：与 HRLicensing 采集口径一致 —— CPU ID + 磁盘序列号）
# ------------------------------------------------------------------

def get_hardware_code() -> str:
    """采集本机硬件码（CPU ID + 磁盘序列号）。

    与 HRLicenseCheck 校验端同口径：Windows 取 **C 盘对应的物理盘**序列号
    （第一块盘可能是虚拟盘，会导致签发/校验不一致）；Linux 用 cpuinfo + 根设备。
    """
    if sys.platform == "win32":
        import wmi
        c = wmi.WMI()
        cpu_id = c.Win32_Processor()[0].ProcessorId.strip()
        disk = ""
        # C 盘 → 物理盘（WMI 关联查询）
        try:
            for ld in c.Win32_LogicalDisk():
                if ld.DeviceID == "C:":
                    for pd in c.Win32_DiskDrive():
                        for part in pd.associators("Win32_DiskDriveToDiskPartition"):
                            for logic in part.associators("Win32_LogicalDiskToPartition"):
                                if logic.DeviceID == "C:":
                                    disk = pd.SerialNumber.strip()
                                    break
                        if disk:
                            break
                    break
        except Exception:
            pass
        return "CpuID:%s|Disk:%s" % (cpu_id, disk)
    # Linux：cpuinfo 家族/型号/步进 + 根设备序列号（尽力而为）
    cpu_id = ""
    family = model = stepping = None
    try:
        for line in open("/proc/cpuinfo", encoding="utf-8", errors="replace"):
            if ":" not in line:
                continue
            k, _, v = line.partition(":")
            k, v = k.strip().lower(), v.strip()
            if k == "cpu family":
                family = v
            elif k == "model":
                model = v
            elif k == "stepping":
                stepping = v
            if family is not None and model is not None and stepping is not None:
                break
        if family is not None and model is not None and stepping is not None:
            cpu_id = "%02X%02X%02X" % (int(family), int(model), int(stepping))
    except Exception:
        pass
    disk = ""
    try:
        import subprocess
        disk = subprocess.run(["lsblk", "-d", "-o", "SERIAL", "-n"],
                              capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        pass
    return "CpuID:%s|Disk:%s" % (cpu_id, disk)


# ------------------------------------------------------------------
# 签发（厂商侧）
# ------------------------------------------------------------------

def _load_or_create_keys(key_dir: str = "keys"):
    """签发密钥：keys/ed25519_private.pem + keys/aes.key；不存在则生成。"""
    os.makedirs(key_dir, exist_ok=True)
    priv_path = os.path.join(key_dir, "ed25519_private.pem")
    aes_path = os.path.join(key_dir, "aes.key")
    if not os.path.isfile(priv_path):
        priv = Ed25519PrivateKey.generate()
        with open(priv_path, "wb") as f:
            f.write(priv.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption()))
        print("[ProjectLicense] 已生成签发私钥: %s（请妥善保管，不外发）" % priv_path)
    if not os.path.isfile(aes_path):
        with open(aes_path, "wb") as f:
            f.write(os.urandom(32))
        print("[ProjectLicense] 已生成 AES 密钥: %s" % aes_path)
    with open(priv_path, "rb") as f:
        priv = serialization.load_pem_private_key(f.read(), password=None)
    with open(aes_path, "rb") as f:
        aes_key = f.read()
    return priv, aes_key


def generate(project: str, days: int = 365, quota: int = 100,
             hardware: "str | None" = None, key_dir: str = "keys") -> str:
    """签发项目授权码（锁项目 + 锁机器）。

    Args:
        project: 项目名（支持中文）
        days: 有效期天数
        quota: 可签发部署授权总数（本项目语义：可激活的项目实例数）
        hardware: 目标机器硬件码（None = 签发机自身；锁机器用）
        key_dir: 签发密钥目录（厂商持有）

    Returns:
        授权码字符串（base64：AES-GCM 密文 || Ed25519 签名）
    """
    priv, aes_key = _load_or_create_keys(key_dir)
    hardware = hardware or get_hardware_code()
    payload = {
        "project": project,
        "issued": int(time.time()),
        "expire": int(time.time()) + days * 86400,
        "quota": quota,
        "used": 0,
        "hardware": hardware,
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    sig = priv.sign(body)                       # Ed25519 签名（防伪造）
    nonce = os.urandom(12)
    ct = AESGCM(aes_key).encrypt(nonce, body, None)   # AES-256-GCM（机密+完整）
    return base64.b64encode(nonce + ct + sig).decode("ascii")


# ------------------------------------------------------------------
# 校验（项目侧）
# ------------------------------------------------------------------

def _decode(code: str):
    """解码授权码 → (载荷 dict)；格式/解密/验签失败抛异常。"""
    raw = base64.b64decode(code)
    nonce, ct, sig = raw[:12], raw[12:-64], raw[-64:]
    body = AESGCM(_get_aeskey()).decrypt(nonce, ct, None)   # 篡改 → InvalidTag
    pub = Ed25519PublicKey.from_public_bytes(_get_pubkey())
    pub.verify(sig, body)                                   # 伪造 → InvalidSignature
    return json.loads(body.decode("utf-8"))


def check_project_license(project: str, code: "str | None" = None,
                          hardware: "str | None" = None) -> bool:
    """校验项目授权码：项目名（中文）+ 有效期 + 配额 + 机器（锁项目锁机器）。

    Args:
        project: 期望项目名
        code: 授权码；None 读环境变量 HR_PROJECT_LICENSE（或项目配置注入）
        hardware: 期望机器硬件码；None = 当前机器（锁机器）

    Returns:
        True 通过；False/异常 失败
    """
    code = code or os.environ.get("HR_PROJECT_LICENSE", "")
    if not code:
        raise RuntimeError("项目授权码缺失（HR_PROJECT_LICENSE 未设置）")
    data = _decode(code)
    if data.get("project") != project:
        raise RuntimeError("项目不匹配：授权码属于「%s」，当前项目「%s」"
                           % (data.get("project"), project))
    now = int(time.time())
    if now < data.get("issued", 0) or now > data.get("expire", 0):
        raise RuntimeError("项目授权码已过期")
    if data.get("used", 0) >= data.get("quota", 0):
        raise RuntimeError("项目授权码配额已用完")
    cur = hardware or get_hardware_code()
    if data.get("hardware") != cur:
        raise RuntimeError("机器不匹配：授权码绑定其他机器")
    return True
