"""
CIS VMware ESXi 8 - Section 4: Logging Checks
- 4.2: Configure remote syslog
"""

from utils import run_ssh_command


def parse_syslog_config(output: str):
    """Parse 'esxcli system syslog config get' output."""
    config = {}
    for line in output.splitlines():
        line = line.strip()
        if ":" in line:
            key, val = line.split(":", 1)
            config[key.strip()] = val.strip()
    return config


def check_4_2_for_host(host: str, username: str, password: str, port: int = 22, key_path: str = None) -> dict:
    """
    CIS 4.2: Kiểm tra Remote Syslog Host
    Yêu cầu: Remote Host phải được cấu hình (không phải <none>)
    """
    print(f"\n=== Kiểm tra CIS 4.2 trên host {host} ===")
    cmd = "esxcli system syslog config get"
    out = run_ssh_command(host, username, password, cmd, port=port, key_path=key_path)
    config = parse_syslog_config(out)
    
    remote_host = config.get("Remote Host", "<none>")
    print(f"[{host}] Remote Host: {remote_host}")
    
    if remote_host and remote_host != "<none>":
        ok = True
    else:
        ok = False
        
    print(f"[{host}] KẾT LUẬN CIS 4.2: {'ĐẠT' if ok else 'KHÔNG ĐẠT'}")
    return {"host": host, "cis_4_2_ok": ok, "detail": {"remote_host": remote_host}}


def fix_4_2_for_host(host, username, password, port=22, key_path=None):
    """Sửa lỗi CIS 4.2: Cấu hình Remote Syslog Host."""
    print(f"[{host}] Đang sửa lỗi CIS 4.2 (Set Remote Host)...")
    
    example = "tcp://192.168.1.10:514"
    user_val = input(f"    >> Nhập địa chỉ Remote Syslog (ví dụ {example}): ").strip()
    
    if not user_val:
        print(f"    -> Sử dụng mặc định: {example}")
        loghost = example
    else:
        loghost = user_val

    cmd = f"esxcli system syslog config set --loghost='{loghost}'"
    run_ssh_command(host, username, password, cmd, port=port, key_path=key_path)
    
    # Reload syslog to apply changes
    run_ssh_command(host, username, password, "esxcli system syslog reload", port=port, key_path=key_path)
    return True
