"""Bounded, read-only Windows telemetry primitives for the SYSWATCH console.

This module intentionally uses only the Python standard library and Windows
commands that are present on supported Windows installations. It never
executes host-mutating actions.
"""

from __future__ import annotations

import ctypes
import json
import os
import platform
import re
import socket
import subprocess
import time
from pathlib import Path


def _run(args: list[str], timeout: float = 2.0) -> str:
    try:
        return subprocess.check_output(
            args, text=True, stderr=subprocess.DEVNULL, timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def cpu_percent() -> float:
    class FILETIME(ctypes.Structure):
        _fields_ = [("dwLowDateTime", ctypes.c_ulong), ("dwHighDateTime", ctypes.c_ulong)]

    idle1, kernel1, user1 = FILETIME(), FILETIME(), FILETIME()
    idle2, kernel2, user2 = FILETIME(), FILETIME(), FILETIME()
    get_times = ctypes.windll.kernel32.GetSystemTimes
    if not get_times(ctypes.byref(idle1), ctypes.byref(kernel1), ctypes.byref(user1)):
        return 0.0
    time.sleep(0.08)
    if not get_times(ctypes.byref(idle2), ctypes.byref(kernel2), ctypes.byref(user2)):
        return 0.0

    def value(ft: FILETIME) -> int:
        return (ft.dwHighDateTime << 32) | ft.dwLowDateTime

    idle = value(idle2) - value(idle1)
    kernel = value(kernel2) - value(kernel1)
    user = value(user2) - value(user1)
    total = kernel + user
    return round(max(0.0, min(100.0, (1.0 - idle / total) * 100.0)), 1) if total else 0.0


def memory_percent() -> float:
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
            ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]
    status = MEMORYSTATUSEX()
    status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return float(status.dwMemoryLoad)
    return 0.0


def network_interfaces() -> list[dict]:
    result = []
    output = _run(["ipconfig", "/all"], timeout=3)
    current = None
    for raw in output.splitlines():
        line = raw.rstrip()
        if line and not line.startswith(" ") and line.endswith(":"):
            name = line[:-1]
            current = {"name": name, "state": "unknown", "mac": "", "rx_bytes": 0, "tx_bytes": 0, "wireless": False}
            result.append(current)
        elif current:
            lower = line.strip().lower()
            if "physical address" in lower and ":" in line:
                current["mac"] = line.split(":", 1)[1].strip()
            if "media disconnected" in lower:
                current["state"] = "down"
            elif "ipv4 address" in lower:
                current["state"] = "up"
            if any(token in current["name"].lower() for token in ("wi-fi", "wifi", "wireless", "wlan")):
                current["wireless"] = True
    return result[:64]


def ports() -> list[str]:
    return _run(["netstat", "-ano"], timeout=3).splitlines()[:100]


def wifi_security() -> dict:
    output = _run(["netsh", "wlan", "show", "interfaces"], timeout=3)
    if not output:
        return {"available": False, "status": "NOT_PRESENT"}
    values = {}
    for raw in output.splitlines():
        if ":" in raw:
            key, value = raw.split(":", 1)
            values[key.strip().lower()] = value.strip()
    auth = values.get("authentication", "UNKNOWN")
    status = "GOOD" if auth and auth.upper() not in ("OPEN", "UNKNOWN") else ("OPEN" if auth.upper() == "OPEN" else "UNKNOWN")
    return {
        "available": True,
        "interface": values.get("name", "unknown"),
        "ssid": values.get("ssid", "unknown"),
        "signal": values.get("signal", ""),
        "security": auth,
        "status": status,
    }


def firewall_health() -> dict:
    output = _run(["netsh", "advfirewall", "show", "allprofiles", "state"], timeout=3)
    if not output:
        return {"backend": "windows-defender-firewall", "status": "UNKNOWN", "detail": "Firewall status unavailable"}
    enabled = len(re.findall(r"State\s+ON", output, re.I))
    disabled = len(re.findall(r"State\s+OFF", output, re.I))
    if enabled and not disabled:
        status = "ACTIVE"
    elif disabled:
        status = "REVIEW"
    else:
        status = "UNKNOWN"
    return {"backend": "windows-defender-firewall", "status": status, "detail": f"profiles_on={enabled}; profiles_off={disabled}"}


def ssh_health() -> dict:
    # Windows OpenSSH, when installed, exposes configuration under ProgramData.
    path = Path(os.environ.get("ProgramData", r"C:\ProgramData")) / "ssh" / "sshd_config"
    if not path.exists():
        return {"available": False, "status": "NOT_PRESENT"}
    values = {}
    try:
        for raw in path.read_text(errors="ignore").splitlines():
            line = raw.strip()
            if line and not line.startswith("#") and " " in line:
                key, value = line.split(None, 1)
                values[key.lower()] = value.strip()
    except OSError:
        return {"available": True, "status": "UNKNOWN"}
    root = values.get("permitrootlogin", "default")
    password = values.get("passwordauthentication", "default")
    risk = password.lower() == "yes" and root.lower() in ("yes", "without-password", "prohibit-password")
    return {"available": True, "status": "REVIEW" if risk else "OK", "permit_root_login": root, "password_authentication": password}


def load_metrics() -> dict:
    return {"1m": 0, "5m": 0, "15m": 0}


def process_lineage(limit: int = 250) -> list[dict]:
    """Return bounded native Windows process metadata without command lines.

    Win32_Process is used instead of Get-Process CSV output because its
    structured JSON representation avoids locale-dependent CSV parsing and
    exposes the parent PID directly. Access failures are isolated per record
    by selecting only metadata fields that do not require elevated inspection.
    """
    bounded = max(1, min(int(limit), 250))
    ps = (
        "$ErrorActionPreference='SilentlyContinue'; "
        "$p=Get-CimInstance Win32_Process | "
        "Select-Object -First %d ProcessId,ParentProcessId,Name,ExecutablePath,CreationDate; "
        "@($p) | ConvertTo-Json -Compress -Depth 3"
    ) % bounded
    output = _run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps],
        timeout=5,
    )
    if not output:
        return []
    try:
        payload = json.loads(output)
    except (json.JSONDecodeError, TypeError):
        return []
    rows = payload if isinstance(payload, list) else [payload]
    result = []
    for item in rows[:bounded]:
        if not isinstance(item, dict):
            continue
        try:
            pid = int(item.get("ProcessId"))
            ppid = int(item.get("ParentProcessId") or 0)
        except (TypeError, ValueError):
            continue
        name = str(item.get("Name") or "unknown")
        result.append({
            "pid": pid,
            "ppid": ppid,
            "state": "running",
            "name": name,
            "exe": str(item.get("ExecutablePath") or name),
            "user": "unresolved",
            "start_time": str(item.get("CreationDate") or ""),
        })
    return result


def filesystem_roots() -> tuple[str, ...]:
    return (os.environ.get("SystemRoot", r"C:\Windows"), os.environ.get("TEMP", r"C:\Windows\Temp"))


def metrics() -> dict:
    root = Path(os.environ.get("SystemDrive", "C:")) / "\\"
    try:
        usage = __import__("shutil").disk_usage(root)
        disk = round(usage.used / usage.total * 100, 1) if usage.total else 0.0
        free = round(usage.free / 1024**3, 2)
    except OSError:
        disk, free = 0.0, 0.0
    return {
        "cpu": cpu_percent(), "memory": memory_percent(), "disk": disk, "disk_free_gb": free,
        "processes": len(process_lineage(250)), "ports": ports(), "hostname": socket.gethostname(),
        "platform": platform.platform(), "kernel": platform.version(), "uptime_seconds": 0,
        "load": load_metrics(), "interfaces": network_interfaces(), "wifi": wifi_security(),
        "firewall": firewall_health(), "ssh": ssh_health(), "timestamp": int(time.time()),
    }
