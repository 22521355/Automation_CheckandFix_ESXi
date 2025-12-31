"""
CIS VMware ESXi 8 - Section 3: Management Checks
- 3.3: Disable Managed Object Browser (MOB)
- 3.7: Set DCUI timeout
- 3.8: Set ESXi Shell Interactive Timeout
- 3.9: Set ESXi Shell Timeout
- 3.12: Set Security.AccountLockFailures
- 3.13: Set Security.AccountUnlockTime
"""

from utils import run_ssh_command


# ==================== CIS 3.3 ====================

def parse_vim_cmd_bool(output: str):
    """Parse boolean value from vim-cmd output."""
    enabled = None
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("value"):
            parts = line.split("=", 1)
            if len(parts) == 2:
                raw_val = parts[1].strip().strip(",")
                low = raw_val.lower()
                if low.startswith("true"):
                    enabled = True
                elif low.startswith("false"):
                    enabled = False
            break
    return enabled, output

def check_3_3_for_host(host: str, username: str, password: str, port: int = 22, key_path: str = None) -> dict:
    """
    CIS 3.3: Kiểm tra Managed Object Browser (MOB)
    Yêu cầu: MOB phải bị disable (false)
    """
    print(f"\n=== Kiểm tra CIS 3.3 trên host {host} ===")
    cmd = "vim-cmd hostsvc/advopt/view Config.HostAgent.plugins.solo.enableMob"
    out = run_ssh_command(host, username, password, cmd, port=port, key_path=key_path)
    mob_enabled, raw = parse_vim_cmd_bool(out)

    if mob_enabled is None:
        print(f"[{host}] KHÔNG đọc được giá trị MOB.")
        ok = False
    else:
        print(f"[{host}] Config.HostAgent.plugins.solo.enableMob = {mob_enabled}")
        ok = not mob_enabled
        print(f"[{host}] KẾT LUẬN CIS 3.3: {'ĐẠT' if ok else 'KHÔNG ĐẠT'}")

    return {
        "host": host,
        "cis_3_3_ok": ok,
        "detail": {"mob_enabled": mob_enabled}
    }


def fix_3_3_for_host(host, username, password, port=22, key_path=None):
    """Sửa lỗi CIS 3.3: Disable MOB."""
    print(f"[{host}] Đang sửa lỗi CIS 3.3 (Disable MOB)...")
    cmd = "vim-cmd hostsvc/advopt/update Config.HostAgent.plugins.solo.enableMob bool false"
    run_ssh_command(host, username, password, cmd, port=port, key_path=key_path)
    return True


# ==================== CIS 3.7 ====================

def parse_int_value(output: str):
    """Parse Int Value từ output của esxcli system settings advanced list."""
    value = None
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("Int Value"):
            parts = line.split(":", 1)
            if len(parts) == 2:
                try:
                    value = int(parts[1].strip())
                except ValueError:
                    value = None
            break
    return value, output

DCUI_TIMEOUT_MAX_SECONDS = 600

def check_3_7_for_host(host: str, username: str, password: str, port: int = 22, key_path: str = None) -> dict:
    """
    CIS 3.7: Kiểm tra DCUI timeout
    Yêu cầu: 0 < timeout <= 600 giây
    """
    print(f"\n=== Kiểm tra CIS 3.7 trên host {host} ===")
    cmd = "esxcli system settings advanced list -o /UserVars/DcuiTimeOut"
    out = run_ssh_command(host, username, password, cmd, port=port, key_path=key_path)
    val, raw = parse_int_value(out)

    ok = False
    if val is not None:
        print(f"[{host}] UserVars.DcuiTimeOut: {val}")
        if 0 < val <= DCUI_TIMEOUT_MAX_SECONDS:
            ok = True
    else:
        print(f"[{host}] Không đọc được giá trị DCUI timeout.")
    
    print(f"[{host}] KẾT LUẬN CIS 3.7: {'ĐẠT' if ok else 'KHÔNG ĐẠT'}")
    return {"host": host, "cis_3_7_ok": ok, "detail": {"dcui_timeout": val}}


def fix_3_7_for_host(host, username, password, port=22, key_path=None):
    """Sửa lỗi CIS 3.7: Set DcuiTimeOut."""
    print(f"[{host}] Đang sửa lỗi CIS 3.7 (Set DcuiTimeOut = {DCUI_TIMEOUT_MAX_SECONDS})...")
    cmd = f"esxcli system settings advanced set -o /UserVars/DcuiTimeOut -i {DCUI_TIMEOUT_MAX_SECONDS}"
    run_ssh_command(host, username, password, cmd, port=port, key_path=key_path)
    return True


# ==================== CIS 3.8 ====================

SHELL_IDLE_TIMEOUT_MAX_SECONDS = 300

def check_3_8_for_host(host: str, username: str, password: str, port: int = 22, key_path: str = None) -> dict:
    """
    CIS 3.8: Kiểm tra ESXi Shell Interactive Timeout
    Yêu cầu: 0 < timeout <= 300 giây
    """
    print(f"\n=== Kiểm tra CIS 3.8 trên host {host} ===")
    cmd = "esxcli system settings advanced list -o /UserVars/ESXiShellInteractiveTimeOut"
    out = run_ssh_command(host, username, password, cmd, port=port, key_path=key_path)
    val, raw = parse_int_value(out)

    ok = False
    if val is not None:
        print(f"[{host}] UserVars.ESXiShellInteractiveTimeOut: {val}")
        if 0 < val <= SHELL_IDLE_TIMEOUT_MAX_SECONDS:
            ok = True
    else:
        print(f"[{host}] Không đọc được giá trị Shell Interactive Timeout.")

    print(f"[{host}] KẾT LUẬN CIS 3.8: {'ĐẠT' if ok else 'KHÔNG ĐẠT'}")
    return {"host": host, "cis_3_8_ok": ok, "detail": {"shell_interactive_timeout": val}}


def fix_3_8_for_host(host, username, password, port=22, key_path=None):
    """Sửa lỗi CIS 3.8: Set ESXiShellInteractiveTimeOut."""
    print(f"[{host}] Đang sửa lỗi CIS 3.8 (Set ESXiShellInteractiveTimeOut = {SHELL_IDLE_TIMEOUT_MAX_SECONDS})...")
    cmd = f"esxcli system settings advanced set -o /UserVars/ESXiShellInteractiveTimeOut -i {SHELL_IDLE_TIMEOUT_MAX_SECONDS}"
    run_ssh_command(host, username, password, cmd, port=port, key_path=key_path)
    return True


# ==================== CIS 3.9 ====================

SHELL_TIMEOUT_MAX_SECONDS = 3600

def check_3_9_for_host(host: str, username: str, password: str, port: int = 22, key_path: str = None) -> dict:
    """
    CIS 3.9: Kiểm tra ESXi Shell Timeout
    Yêu cầu: 0 < timeout <= 3600 giây
    """
    print(f"\n=== Kiểm tra CIS 3.9 trên host {host} ===")
    cmd = "esxcli system settings advanced list -o /UserVars/ESXiShellTimeOut"
    out = run_ssh_command(host, username, password, cmd, port=port, key_path=key_path)
    val, raw = parse_int_value(out)

    ok = False
    if val is not None:
        print(f"[{host}] UserVars.ESXiShellTimeOut: {val}")
        if 0 < val <= SHELL_TIMEOUT_MAX_SECONDS:
            ok = True
    else:
        print(f"[{host}] Không đọc được giá trị Shell Timeout.")
    
    print(f"[{host}] KẾT LUẬN CIS 3.9: {'ĐẠT' if ok else 'KHÔNG ĐẠT'}")
    return {"host": host, "cis_3_9_ok": ok, "detail": {"shell_timeout": val}}


def fix_3_9_for_host(host, username, password, port=22, key_path=None):
    """Sửa lỗi CIS 3.9: Set ESXiShellTimeOut."""
    print(f"[{host}] Đang sửa lỗi CIS 3.9 (Set ESXiShellTimeOut = {SHELL_TIMEOUT_MAX_SECONDS})...")
    cmd = f"esxcli system settings advanced set -o /UserVars/ESXiShellTimeOut -i {SHELL_TIMEOUT_MAX_SECONDS}"
    run_ssh_command(host, username, password, cmd, port=port, key_path=key_path)
    return True


# ==================== CIS 3.12 ====================

def parse_vim_cmd_int(output: str):
    """Parse integer value from vim-cmd output (value = <int>)."""
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("value ="):
            parts = line.split("=", 1)
            if len(parts) == 2:
                val_str = parts[1].strip().rstrip(",")
                try:
                    return int(val_str)
                except ValueError:
                    pass
    return None

ACCOUNT_LOCK_FAILURES = 5

def check_3_12_for_host(host: str, username: str, password: str, port: int = 22, key_path: str = None) -> dict:
    """
    CIS 3.12: Kiểm tra Security.AccountLockFailures
    Yêu cầu: giá trị phải bằng 5
    """
    print(f"\n=== Kiểm tra CIS 3.12 trên host {host} ===")
    cmd = "vim-cmd hostsvc/advopt/view Security.AccountLockFailures"
    out = run_ssh_command(host, username, password, cmd, port=port, key_path=key_path)
    val = parse_vim_cmd_int(out)

    ok = False
    if val is not None:
        print(f"[{host}] Security.AccountLockFailures: {val}")
        if val == ACCOUNT_LOCK_FAILURES:
            ok = True
    else:
        print(f"[{host}] Không đọc được giá trị Security.AccountLockFailures.")
    
    print(f"[{host}] KẾT LUẬN CIS 3.12: {'ĐẠT' if ok else 'KHÔNG ĐẠT'}")
    return {"host": host, "cis_3_12_ok": ok, "detail": {"account_lock_failures": val}}


def fix_3_12_for_host(host, username, password, port=22, key_path=None):
    """Sửa lỗi CIS 3.12: Set AccountLockFailures."""
    print(f"[{host}] Đang sửa lỗi CIS 3.12 (Set AccountLockFailures = {ACCOUNT_LOCK_FAILURES})...")
    cmd = f"vim-cmd hostsvc/advopt/update Security.AccountLockFailures int {ACCOUNT_LOCK_FAILURES}"
    run_ssh_command(host, username, password, cmd, port=port, key_path=key_path)
    return True


# ==================== CIS 3.13 ====================

ACCOUNT_UNLOCK_TIME = 900

def check_3_13_for_host(host: str, username: str, password: str, port: int = 22, key_path: str = None) -> dict:
    """
    CIS 3.13: Kiểm tra Security.AccountUnlockTime
    Yêu cầu: giá trị phải bằng 900
    """
    print(f"\n=== Kiểm tra CIS 3.13 trên host {host} ===")
    cmd = "vim-cmd hostsvc/advopt/view Security.AccountUnlockTime"
    out = run_ssh_command(host, username, password, cmd, port=port, key_path=key_path)
    val = parse_vim_cmd_int(out)

    ok = False
    if val is not None:
        print(f"[{host}] Security.AccountUnlockTime: {val}")
        if val == ACCOUNT_UNLOCK_TIME:
            ok = True
    else:
        print(f"[{host}] Không đọc được giá trị Security.AccountUnlockTime.")

    print(f"[{host}] KẾT LUẬN CIS 3.13: {'ĐẠT' if ok else 'KHÔNG ĐẠT'}")
    return {"host": host, "cis_3_13_ok": ok, "detail": {"account_unlock_time": val}}


def fix_3_13_for_host(host, username, password, port=22, key_path=None):
    """Sửa lỗi CIS 3.13: Set AccountUnlockTime."""
    print(f"[{host}] Đang sửa lỗi CIS 3.13 (Set AccountUnlockTime = {ACCOUNT_UNLOCK_TIME})...")
    cmd = f"vim-cmd hostsvc/advopt/update Security.AccountUnlockTime int {ACCOUNT_UNLOCK_TIME}"
    run_ssh_command(host, username, password, cmd, port=port, key_path=key_path)
    return True
