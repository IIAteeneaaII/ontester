#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enable SSH (best-effort) on an ONT/router using Telnet and/or Serial.
- Verifies first if SSH is already open (TCP/22).
- If closed, attempts to enable via Telnet (telnetlib3) and/or Serial (pyserial)
  by running a sequence of safe, common commands for BusyBox/OpenWrt/systemd SysV.
- Designed to be non-destructive and idempotent.
- Prints a JSON result summary at the end.

Usage examples:
  python enable_ssh_any.py --host 192.168.100.1 -u admin -p admin
  python enable_ssh_any.py --host 192.168.1.1 -u root -p root --try-telnet --skip-serial
  python enable_ssh_any.py --serial-port COM4 --baud 115200 -u root -p root
  python enable_ssh_any.py --host 192.168.1.1 -u telecomadmin -p admintelecom --root-password root

Requirements:
  pip install paramiko telnetlib3 pyserial
"""
from __future__ import annotations
import asyncio, json, os, re, socket, sys, time
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any

# Optional imports (only required if the respective protocol is used)
try:
    import telnetlib3  # asyncio telnet
except Exception:
    telnetlib3 = None

try:
    import serial  # pyserial
except Exception:
    serial = None


# ------------------------- Utilities -------------------------
def check_tcp(host: str, port: int, timeout: float = 2.0) -> bool:
    """Return True if TCP port is open."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

def now_ms() -> int:
    return int(time.time() * 1000)


# ------------------------- Recipes -------------------------
# Each recipe is a list of shell commands (strings). We'll try all recipes in order.
RECIPES: Dict[str, List[str]] = {
    # OpenWrt/BusyBox Dropbear via UCI
    "openwrt_dropbear": [
        "which uci >/dev/null 2>&1 && uci set dropbear.@dropbear[0].Port=22 || true",
        "which uci >/dev/null 2>&1 && uci set dropbear.@dropbear[0].PasswordAuth=on || true",
        "which uci >/dev/null 2>&1 && uci commit dropbear || true",
        "[ -x /etc/init.d/dropbear ] && /etc/init.d/dropbear enable || true",
        "[ -x /etc/init.d/dropbear ] && (/etc/init.d/dropbear restart || /etc/init.d/dropbear start) || true"
    ],
    # BusyBox Dropbear service via init.d only
    "dropbear_initd_only": [
        "[ -x /etc/init.d/dropbear ] && /etc/init.d/dropbear enable || true",
        "[ -x /etc/init.d/dropbear ] && (/etc/init.d/dropbear restart || /etc/init.d/dropbear start) || true"
    ],
    # Start Dropbear directly (non-persistent)
    "start_dropbear_direct": [
        "killall dropbear >/dev/null 2>&1 || true",
        "dropbear -R -p 22 >/dev/null 2>&1 &",
        "sleep 1"
    ],
    # OpenSSH via systemd
    "openssh_systemd": [
        "which systemctl >/dev/null 2>&1 || exit 0",
        "systemctl enable ssh >/dev/null 2>&1 || systemctl enable sshd >/dev/null 2>&1 || true",
        "systemctl restart ssh >/dev/null 2>&1 || systemctl restart sshd >/dev/null 2>&1 || true"
    ],
    # OpenSSH via SysV init
    "openssh_sysv": [
        "[ -x /etc/init.d/ssh ] && (/etc/init.d/ssh restart || /etc/init.d/ssh start) || true",
        "service ssh restart >/dev/null 2>&1 || service ssh start >/dev/null 2>&1 || true"
    ],
}

# Optional privilege escalation steps commonly found on ONTs
# We'll attempt them opportunistically before recipes (no failure if they don't work).
ESCALATION: List[Dict[str, str]] = [
    {"send": "su", "expect": r"Password:|# |\$ ", "after_send_secret": True},   # send root password if prompted
    {"send": "shell", "expect": r"# |\$ "},                                     # enter BusyBox shell
    {"send": "sh", "expect": r"# |\$ "},                                        # fallback shell
]


# ------------------------- Telnet path -------------------------
async def telnet_run_commands(host: str, port: int, username: str, password: str,
                              root_password: Optional[str], cmds: List[str],
                              login_timeout: float = 7.0, step_timeout: float = 6.0) -> Dict[str, Any]:
    """Login via telnetlib3 and run a list of commands, returning a transcript."""
    if telnetlib3 is None:
        raise RuntimeError("telnetlib3 is not installed")
    reader, writer = await telnetlib3.open_connection(host, port)
    transcript = ""
    prompt_re = re.compile(r"(?:ATP> |# |\$ )", re.MULTILINE)

    async def read_until(pattern: re.Pattern, timeout: float) -> str:
        nonlocal transcript
        buf = ""
        start = time.time()
        while True:
            try:
                chunk = await asyncio.wait_for(reader.read(1024), timeout=0.4)
            except asyncio.TimeoutError:
                chunk = ""
            if chunk:
                transcript += chunk
                buf += chunk
                if pattern.search(buf):
                    return buf
            if time.time() - start > timeout:
                raise TimeoutError(f"Timeout waiting for pattern {pattern.pattern}")

    # Basic login dialog (best-effort)
    await writer.drain()
    await writer.write("\n")
    try:
        buf = await read_until(re.compile(r"(?:login:|Username:)", re.MULTILINE), login_timeout)
        await writer.write(username + "\n")
    except Exception:
        # Some devices directly show Password or a prompt
        pass
    try:
        buf = await read_until(re.compile(r"Password:", re.MULTILINE), login_timeout)
        await writer.write(password + "\n")
    except Exception:
        pass

    # prompt sync
    await writer.write("\n")
    try:
        await read_until(prompt_re, 3.0)
    except Exception:
        pass

    # Privilege escalation attempts
    for step in ESCALATION:
        try:
            await writer.write(step["send"] + "\n")
            buf = await read_until(re.compile(step["expect"], re.MULTILINE), 4.0)
            if step.get("after_send_secret") and root_password:
                await writer.write(root_password + "\n")
                try:
                    await read_until(prompt_re, 3.0)
                except Exception:
                    pass
        except Exception:
            continue  # ignore failed escalation

    # Run recipes
    for cmd in cmds:
        await writer.write(cmd + "\n")
        try:
            await read_until(prompt_re, step_timeout)
        except Exception:
            # continue even if a single step times out (non-fatal)
            pass

    writer.close()
    try:
        await writer.wait_closed()
    except Exception:
        pass

    return {"transcript": transcript}


# ------------------------- Serial path -------------------------
def serial_run_commands(port: str, baud: int, username: str, password: str,
                        root_password: Optional[str], cmds: List[str],
                        login_timeout: float = 7.0, step_timeout: float = 6.0) -> Dict[str, Any]:
    """Login via pyserial and run a list of commands."""
    if serial is None:
        raise RuntimeError("pyserial is not installed")
    ser = serial.Serial(port, baudrate=baud, timeout=0.4)
    transcript = ""

    def write_line(s: str):
        nonlocal transcript
        if not s.endswith("\n"):
            s += "\n"
        ser.write(s.encode("utf-8", errors="ignore"))
        ser.flush()
        transcript += f"$ {s}"

    def read_until(pattern: re.Pattern, timeout: float) -> str:
        nonlocal transcript
        buf = ""
        start = time.time()
        while True:
            data = ser.read(1024)
            if data:
                chunk = data.decode("utf-8", errors="ignore")
                transcript += chunk
                buf += chunk
                if pattern.search(buf):
                    return buf
            if time.time() - start > timeout:
                raise TimeoutError(f"Timeout waiting for pattern {pattern.pattern}")

    prompt_re = re.compile(r"(?:ATP> |# |\$ )", re.MULTILINE)
    write_line("")  # wake
    try:
        read_until(re.compile(r"(?:login:|Username:)", re.MULTILINE), login_timeout)
        write_line(username)
    except Exception:
        pass
    try:
        read_until(re.compile(r"Password:", re.MULTILINE), login_timeout)
        write_line(password)
    except Exception:
        pass
    write_line("")
    try:
        read_until(prompt_re, 3.0)
    except Exception:
        pass

    # escalation
    for step in ESCALATION:
        try:
            write_line(step["send"])
            read_until(re.compile(step["expect"], re.MULTILINE), 4.0)
            if step.get("after_send_secret") and root_password:
                write_line(root_password)
                try:
                    read_until(prompt_re, 3.0)
                except Exception:
                    pass
        except Exception:
            continue

    # recipes
    for cmd in cmds:
        write_line(cmd)
        try:
            read_until(prompt_re, step_timeout)
        except Exception:
            pass

    ser.close()
    return {"transcript": transcript}


# ------------------------- Orchestrator -------------------------
@dataclass
class Result:
    host: Optional[str]
    serial_port: Optional[str]
    protocol_used: Optional[str]
    ssh_open_before: bool
    ssh_open_after: bool
    success: bool
    details: Dict[str, Any]


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Attempt to enable SSH on a router via Telnet and/or Serial.")
    ap.add_argument("--host", help="Router IP/hostname (for Telnet and SSH check).")
    ap.add_argument("--telnet-port", type=int, default=23)
    ap.add_argument("--serial-port", help="Serial port, e.g., COM4 or /dev/ttyUSB0")
    ap.add_argument("--baud", type=int, default=115200)

    ap.add_argument("-u", "--username", default="root")
    ap.add_argument("-p", "--password", default="root")
    ap.add_argument("--root-password", default=None, help="Optional root password for 'su'")

    ap.add_argument("--try-telnet", action="store_true", help="Force try Telnet (default: auto if host is provided)")
    ap.add_argument("--try-serial", action="store_true", help="Force try Serial (default: auto if serial-port is provided)")
    ap.add_argument("--skip-telnet", action="store_true")
    ap.add_argument("--skip-serial", action="store_true")

    ap.add_argument("--sleep-after", type=float, default=2.0, help="Seconds to wait after commands before re-checking SSH")
    args = ap.parse_args()

    # decide modes
    do_telnet = (args.try_telnet or (args.host and not args.skip_telnet))
    do_serial = (args.try_serial or (args.serial_port and not args.skip_serial))

    ssh_before = False
    if args.host:
        ssh_before = check_tcp(args.host, 22, timeout=1.5)

    # If already open, exit early
    if ssh_before:
        res = Result(
            host=args.host, serial_port=args.serial_port, protocol_used=None,
            ssh_open_before=True, ssh_open_after=True, success=True,
            details={"note": "SSH already open before any changes."}
        )
        print(json.dumps(asdict(res), indent=2))
        return 0

    # Build the unified list of commands (all recipes in order)
    recipe_order = ["openwrt_dropbear", "dropbear_initd_only", "start_dropbear_direct", "openssh_systemd", "openssh_sysv"]
    cmds: List[str] = []
    for r in recipe_order:
        cmds.extend(RECIPES[r])

    detail: Dict[str, Any] = {"attempts": []}

    # Try Telnet first (if applicable)
    if do_telnet and args.host:
        try:
            transcript = asyncio.run(telnet_run_commands(
                host=args.host, port=args.telnet_port,
                username=args.username, password=args.password,
                root_password=args.root_password, cmds=cmds
            ))
            detail["attempts"].append({"protocol": "telnet", "ok": True})
            time.sleep(args.sleep_after)
            ssh_after = check_tcp(args.host, 22, timeout=1.5)
            if ssh_after:
                res = Result(
                    host=args.host, serial_port=args.serial_port, protocol_used="telnet",
                    ssh_open_before=False, ssh_open_after=True, success=True,
                    details={"transcript_tail": transcript["transcript"][-4000:]}
                )
                print(json.dumps(asdict(res), indent=2))
                return 0
        except Exception as e:
            detail["attempts"].append({"protocol": "telnet", "ok": False, "error": str(e)})

    # Try Serial (if applicable)
    if do_serial and args.serial_port:
        try:
            transcript = serial_run_commands(
                port=args.serial_port, baud=args.baud,
                username=args.username, password=args.password,
                root_password=args.root_password, cmds=cmds
            )
            detail["attempts"].append({"protocol": "serial", "ok": True})
            # For serial-only cases without host, we cannot TCP-check. Assume best-effort: we end here.
            if args.host:
                time.sleep(args.sleep_after)
                ssh_after = check_tcp(args.host, 22, timeout=1.5)
            else:
                ssh_after = False  # unknown
            res = Result(
                host=args.host, serial_port=args.serial_port, protocol_used="serial",
                ssh_open_before=False, ssh_open_after=bool(ssh_after), success=bool(ssh_after),
                details={"transcript_tail": transcript["transcript"][-4000:], "note": "SSH state unknown if no host provided" if not args.host else None}
            )
            print(json.dumps(asdict(res), indent=2))
            return 0 if ssh_after else 2
        except Exception as e:
            detail["attempts"].append({"protocol": "serial", "ok": False, "error": str(e)})

    # Final check (if host provided)
    ssh_after_final = check_tcp(args.host, 22, timeout=1.5) if args.host else False
    res = Result(
        host=args.host, serial_port=args.serial_port, protocol_used=None,
        ssh_open_before=False, ssh_open_after=ssh_after_final, success=ssh_after_final,
        details=detail
    )
    print(json.dumps(asdict(res), indent=2))
    return 0 if ssh_after_final else 2


if __name__ == "__main__":
    sys.exit(main())
