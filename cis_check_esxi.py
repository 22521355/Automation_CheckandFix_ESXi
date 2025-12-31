

import paramiko

ALLOWED_LEVELS = {"VMwareCertified", "VMwareAccepted", "PartnerSupported"}
DCUI_TIMEOUT_MAX_SECONDS = 600
SHELL_IDLE_TIMEOUT_MAX_SECONDS = 300

def run_ssh_command(host, username, password, command, port=22, timeout=10):
    """Chạy lệnh SSH và trả về stdout (str)."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=host,
            port=port,
            username=username,
            password=password,
            look_for_keys=False,
            allow_agent=False,
            timeout=timeout,
        )
        stdout, stderr = client.exec_command(command)
        out = stdout.read().decode("utf-8", errors="ignore")
        err = stderr.read().decode("utf-8", errors="ignore")
        if err.strip():
            # Một số lệnh trả về stderr warning nhưng vẫn chạy OK
            print(f"[{host}] CẢNH BÁO: stderr trả về:\n{err}")
            # pass
        return out
    finally:
        client.close()

"""
CIS VMware ESXi 8 - 2.4 (L1)
Host image profile acceptance level must be PartnerSupported or higher (Automated)

Kiểm tra:
1. Mức acceptance level chung của host (esxcli software acceptance get)
   Phải là một trong: VMwareCertified, VMwareAccepted, PartnerSupported
2. Từng VIB trên host (esxcli software vib list)
   Mỗi VIB cũng phải có Acceptance Level thuộc 3 mức trên
"""

def parse_host_acceptance_level(output: str) -> str | None:
    for line in output.splitlines():
        line = line.strip()
        if line:
            return line
    return None


def parse_bad_vibs(output: str):
    bad_vibs = []
    started_data = False

    for line in output.splitlines():
        if not started_data:
            if "Acceptance Level" in line:
                started_data = True
            continue

        if not line.strip():
            continue

        if line.replace("-", "").strip() == "":
            continue

        parts = line.split()
        if len(parts) < 4:
            continue

        vib_name = parts[0]
        vib_accept = parts[3]

        if vib_accept not in ALLOWED_LEVELS:
            bad_vibs.append({"name": vib_name, "acceptance": vib_accept})

    return bad_vibs

def check_2_4_for_host(host, username, password, port=22):
    print(f"\n=== Kiểm tra 2.4 trên host {host} ===")
    out_accept = run_ssh_command(host, username, password, "esxcli software acceptance get", port=port)
    host_level = parse_host_acceptance_level(out_accept)

    if host_level is None:
        print(f"[{host}] KHÔNG đọc được acceptance level từ output:")
        print(out_accept)
        host_level_ok = False
    else:
        host_level_ok = host_level in ALLOWED_LEVELS
        status = "ĐẠT" if host_level_ok else "KHÔNG ĐẠT"
        print(f"[{host}] Host acceptance level: {host_level} -> {status}")

    out_vibs = run_ssh_command(host, username, password, "esxcli software vib list", port=port)
    bad_vibs = parse_bad_vibs(out_vibs)

    if not bad_vibs:
        print(f"[{host}] Tất cả VIB đều có Acceptance Level hợp lệ.")
        vibs_ok = True
    else:
        print(f"[{host}] PHÁT HIỆN VIB không đạt yêu cầu:")
        for vib in bad_vibs:
            print(f"   - {vib['name']} : {vib['acceptance']}")
        vibs_ok = False

    overall_ok = host_level_ok and vibs_ok
    print(f"[{host}] KẾT LUẬN CIS 2.4: {'ĐẠT' if overall_ok else 'KHÔNG ĐẠT'}")

    return {
        "host": host,
        "cis_2_4_ok": overall_ok,
        "detail": {"bad_vibs": bad_vibs}
    }

def fix_2_4_for_host(host, username, password, port=22):
    print(f"[{host}] Đang sửa lỗi CIS 2.4 (Set acceptance level = PartnerSupported)...")
    cmd = "esxcli software acceptance set --level=PartnerSupported"
    run_ssh_command(host, username, password, cmd, port=port)
    return True


def parse_mem_share_force_salting(output: str) -> tuple[int | None, str]:
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

def check_2_10_for_host(host: str, username: str, password: str, port: int = 22) -> dict:
    print(f"\n=== Kiểm tra CIS 2.10 trên host {host} ===")
    cmd = "esxcli system settings advanced list -o /Mem/ShareForceSalting"
    out = run_ssh_command(host, username, password, cmd, port=port)
    value, raw = parse_mem_share_force_salting(out)

    if value is None:
        print(f"[{host}] KHÔNG đọc được giá trị Mem.ShareForceSalting.")
        ok = False
    else:
        print(f"[{host}] Mem.ShareForceSalting (Int Value): {value}")
        ok = (value == 2)
        print(f"[{host}] KẾT LUẬN CIS 2.10: {'ĐẠT' if ok else 'KHÔNG ĐẠT'}")

    return {
        "host": host,
        "cis_2_10_ok": ok,
        "detail": {"current_value": value}
    }

def fix_2_10_for_host(host, username, password, port=22):
    print(f"[{host}] Đang sửa lỗi CIS 2.10 (Set Mem.ShareForceSalting = 2)...")
    cmd = "esxcli system settings advanced set -o /Mem/ShareForceSalting -i 2"
    run_ssh_command(host, username, password, cmd, port=port)
    return True


def parse_mob_enabled(output: str):
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

def check_3_3_for_host(host: str, username: str, password: str, port: int = 22) -> dict:
    print(f"\n=== Kiểm tra CIS 3.3 trên host {host} ===")
    cmd = "vim-cmd hostsvc/advopt/view Config.HostAgent.plugins.solo.enableMob"
    out = run_ssh_command(host, username, password, cmd, port=port)
    mob_enabled, raw = parse_mob_enabled(out)

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

def fix_3_3_for_host(host, username, password, port=22):
    print(f"[{host}] Đang sửa lỗi CIS 3.3 (Disable MOB)...")
    cmd = "vim-cmd hostsvc/advopt/update Config.HostAgent.plugins.solo.enableMob bool false"
    run_ssh_command(host, username, password, cmd, port=port)
    return True


def parse_int_value(output: str):
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

def check_3_7_for_host(host: str, username: str, password: str, port: int = 22) -> dict:
    print(f"\n=== Kiểm tra CIS 3.7 trên host {host} ===")
    cmd = "esxcli system settings advanced list -o /UserVars/DcuiTimeOut"
    out = run_ssh_command(host, username, password, cmd, port=port)
    val, raw = parse_int_value(out)

    ok = False
    if val is not None:
        print(f"[{host}] UserVars.DcuiTimeOut: {val}")
        if 0 < val <= DCUI_TIMEOUT_MAX_SECONDS:
            ok = True
        else:
            ok = False
    else:
        print(f"[{host}] Không đọc được giá trị DCUI timeout.")
    
    print(f"[{host}] KẾT LUẬN CIS 3.7: {'ĐẠT' if ok else 'KHÔNG ĐẠT'}")
    return {"host": host, "cis_3_7_ok": ok, "detail": {"dcui_timeout": val}}

def fix_3_7_for_host(host, username, password, port=22):
    print(f"[{host}] Đang sửa lỗi CIS 3.7 (Set DcuiTimeOut = {DCUI_TIMEOUT_MAX_SECONDS})...")
    cmd = f"esxcli system settings advanced set -o /UserVars/DcuiTimeOut -i {DCUI_TIMEOUT_MAX_SECONDS}"
    run_ssh_command(host, username, password, cmd, port=port)
    return True


def check_3_8_for_host(host: str, username: str, password: str, port: int = 22) -> dict:
    print(f"\n=== Kiểm tra CIS 3.8 trên host {host} ===")
    cmd = "esxcli system settings advanced list -o /UserVars/ESXiShellInteractiveTimeOut"
    out = run_ssh_command(host, username, password, cmd, port=port)
    val, raw = parse_int_value(out)

    ok = False
    if val is not None:
        print(f"[{host}] UserVars.ESXiShellInteractiveTimeOut: {val}")
        if 0 < val <= SHELL_IDLE_TIMEOUT_MAX_SECONDS:
            ok = True
        else:
            ok = False
    else:
        print(f"[{host}] Không đọc được giá trị Shell Interactive Timeout.")

    print(f"[{host}] KẾT LUẬN CIS 3.8: {'ĐẠT' if ok else 'KHÔNG ĐẠT'}")
    return {"host": host, "cis_3_8_ok": ok, "detail": {"shell_interactive_timeout": val}}

def fix_3_8_for_host(host, username, password, port=22):
    print(f"[{host}] Đang sửa lỗi CIS 3.8 (Set ESXiShellInteractiveTimeOut = {SHELL_IDLE_TIMEOUT_MAX_SECONDS})...")
    cmd = f"esxcli system settings advanced set -o /UserVars/ESXiShellInteractiveTimeOut -i {SHELL_IDLE_TIMEOUT_MAX_SECONDS}"
    run_ssh_command(host, username, password, cmd, port=port)
    return True


def check_3_9_for_host(host: str, username: str, password: str, port: int = 22) -> dict:
    print(f"\n=== Kiểm tra CIS 3.9 trên host {host} ===")
    cmd = "esxcli system settings advanced list -o /UserVars/ESXiShellTimeOut"
    out = run_ssh_command(host, username, password, cmd, port=port)
    val, raw = parse_int_value(out)

    ok = False
    if val is not None:
        print(f"[{host}] UserVars.ESXiShellTimeOut: {val}")
        if 0 < val <= 3600:
            ok = True
        else:
            ok = False
    else:
        print(f"[{host}] Không đọc được giá trị Shell Timeout.")
    
    print(f"[{host}] KẾT LUẬN CIS 3.9: {'ĐẠT' if ok else 'KHÔNG ĐẠT'}")
    return {"host": host, "cis_3_9_ok": ok, "detail": {"shell_timeout": val}}

def fix_3_9_for_host(host, username, password, port=22):
    print(f"[{host}] Đang sửa lỗi CIS 3.9 (Set ESXiShellTimeOut = 3600)...")
    cmd = "esxcli system settings advanced set -o /UserVars/ESXiShellTimeOut -i 3600"
    run_ssh_command(host, username, password, cmd, port=port)
    return True


def parse_vim_cmd_int(output: str):
    """Parse integer value from vim-cmd output (value = <int>)."""
    for line in output.splitlines():
        line = line.strip()
        # Output format example: value = 5,
        if line.startswith("value ="):
            parts = line.split("=", 1)
            if len(parts) == 2:
                val_str = parts[1].strip().rstrip(",")
                try:
                    return int(val_str)
                except ValueError:
                    pass
    return None


def check_3_12_for_host(host: str, username: str, password: str, port: int = 22) -> dict:
    print(f"\n=== Kiểm tra CIS 3.12 trên host {host} ===")
    # Sử dụng vim-cmd thay vì esxcli cho các key Security.*
    cmd = "vim-cmd hostsvc/advopt/view Security.AccountLockFailures"
    out = run_ssh_command(host, username, password, cmd, port=port)
    val = parse_vim_cmd_int(out)

    ok = False
    if val is not None:
        print(f"[{host}] Security.AccountLockFailures: {val}")
        # Theo yêu cầu user: check == 5
        if val == 5:
            ok = True
        else:
            ok = False
    else:
        print(f"[{host}] Không đọc được giá trị Security.AccountLockFailures.")
        # print(f"DEBUG RAW OUTPUT:\n{out}")
    
    print(f"[{host}] KẾT LUẬN CIS 3.12: {'ĐẠT' if ok else 'KHÔNG ĐẠT'}")
    return {"host": host, "cis_3_12_ok": ok, "detail": {"account_lock_failures": val}}

def fix_3_12_for_host(host, username, password, port=22):
    print(f"[{host}] Đang sửa lỗi CIS 3.12 (Set AccountLockFailures = 5)...")
    # Cú pháp vim-cmd update: vim-cmd hostsvc/advopt/update <Key> <Type> <Value>
    cmd = "vim-cmd hostsvc/advopt/update Security.AccountLockFailures int 5"
    run_ssh_command(host, username, password, cmd, port=port)
    return True


def check_3_13_for_host(host: str, username: str, password: str, port: int = 22) -> dict:
    print(f"\n=== Kiểm tra CIS 3.13 trên host {host} ===")
    cmd = "vim-cmd hostsvc/advopt/view Security.AccountUnlockTime"
    out = run_ssh_command(host, username, password, cmd, port=port)
    val = parse_vim_cmd_int(out)

    ok = False
    if val is not None:
        print(f"[{host}] Security.AccountUnlockTime: {val}")
        if val == 900:
            ok = True
        else:
            ok = False
    else:
        print(f"[{host}] Không đọc được giá trị Security.AccountUnlockTime.")
        # print(f"DEBUG RAW OUTPUT:\n{out}")

    print(f"[{host}] KẾT LUẬN CIS 3.13: {'ĐẠT' if ok else 'KHÔNG ĐẠT'}")
    return {"host": host, "cis_3_13_ok": ok, "detail": {"account_unlock_time": val}}

def fix_3_13_for_host(host, username, password, port=22):
    print(f"[{host}] Đang sửa lỗi CIS 3.13 (Set AccountUnlockTime = 900)...")
    cmd = "vim-cmd hostsvc/advopt/update Security.AccountUnlockTime int 900"
    run_ssh_command(host, username, password, cmd, port=port)
    return True


def parse_syslog_config(output: str):
    """Parse 'esxcli system syslog config get' output."""
    config = {}
    for line in output.splitlines():
        line = line.strip()
        if ":" in line:
            key, val = line.split(":", 1)
            config[key.strip()] = val.strip()
    return config

def check_4_2_for_host(host: str, username: str, password: str, port: int = 22) -> dict:
    print(f"\n=== Kiểm tra CIS 4.2 trên host {host} ===")
    cmd = "esxcli system syslog config get"
    out = run_ssh_command(host, username, password, cmd, port=port)
    config = parse_syslog_config(out)
    
    remote_host = config.get("Remote Host", "<none>")
    print(f"[{host}] Remote Host: {remote_host}")
    
    # Check if Remote Host is configured (not <none> and not empty)
    if remote_host and remote_host != "<none>":
        ok = True
    else:
        ok = False
        
    print(f"[{host}] KẾT LUẬN CIS 4.2: {'ĐẠT' if ok else 'KHÔNG ĐẠT'}")
    return {"host": host, "cis_4_2_ok": ok, "detail": {"remote_host": remote_host}}

def fix_4_2_for_host(host, username, password, port=22):
    print(f"[{host}] Đang sửa lỗi CIS 4.2 (Set Remote Host)...")
    
    example = "tcp://192.168.1.10:514"
    user_val = input(f"    >> Nhập địa chỉ Remote Syslog (ví dụ {example}): ").strip()
    
    if not user_val:
        print(f"    -> Sử dụng mặc định: {example}")
        loghost = example
    else:
        loghost = user_val

    cmd = f"esxcli system syslog config set --loghost='{loghost}'"
    run_ssh_command(host, username, password, cmd, port=port)
    # Reload syslog to apply changes
    run_ssh_command(host, username, password, "esxcli system syslog reload", port=port)
    return True


def parse_vswitch_policy(output: str, key="Allow Forged Transmits") -> bool | None:
    """Parse output from esxcli network vswitch standard policy security get."""
    for line in output.splitlines():
        line = line.strip()
        if line.startswith(key):
            parts = line.split(":", 1)
            if len(parts) == 2:
                val_str = parts[1].strip().lower()
                return val_str == "true"
    return None

def check_5_6_for_host(host: str, username: str, password: str, port: int = 22) -> dict:
    print(f"\n=== Kiểm tra CIS 5.6 trên host {host} ===")
    cmd = "esxcli network vswitch standard policy security get -v vSwitch0"
    out = run_ssh_command(host, username, password, cmd, port=port)
    
    # Key cần tìm: Allow Forged Transmits
    allow_forged = parse_vswitch_policy(out, "Allow Forged Transmits")
    
    ok = False
    if allow_forged is None:
        print(f"[{host}] KHÔNG đọc được giá trị Allow Forged Transmits.")
    else:
        print(f"[{host}] Allow Forged Transmits: {allow_forged}")
        # Yêu cầu: false
        if not allow_forged:
            ok = True
        else:
            ok = False
            
    print(f"[{host}] KẾT LUẬN CIS 5.6: {'ĐẠT' if ok else 'KHÔNG ĐẠT'}")
    return {"host": host, "cis_5_6_ok": ok, "detail": {"allow_forged_transmits": allow_forged}}

def fix_5_6_for_host(host, username, password, port=22):
    print(f"[{host}] Đang sửa lỗi CIS 5.6 (Disable Allow Forged Transmits on vSwitch0)...")
    cmd = "esxcli network vswitch standard policy security set -v vSwitch0 -f false"
    run_ssh_command(host, username, password, cmd, port=port)
    return True


def check_5_7_for_host(host: str, username: str, password: str, port: int = 22) -> dict:
    print(f"\n=== Kiểm tra CIS 5.7 trên host {host} ===")
    cmd = "esxcli network vswitch standard policy security get -v vSwitch0"
    out = run_ssh_command(host, username, password, cmd, port=port)
    
    # Key: MAC Address Changes
    allow_mac_change = parse_vswitch_policy(out, "Allow MAC Address Change")
    
    ok = False
    if allow_mac_change is None:
        print(f"[{host}] KHÔNG đọc được giá trị MAC Address Changes.")
    else:
        print(f"[{host}] Allow MAC Address Changes: {allow_mac_change}")
        # Yêu cầu: false
        if not allow_mac_change:
            ok = True
        else:
            ok = False
            
    print(f"[{host}] KẾT LUẬN CIS 5.7: {'ĐẠT' if ok else 'KHÔNG ĐẠT'}")
    return {"host": host, "cis_5_7_ok": ok, "detail": {"allow_mac_change": allow_mac_change}}

def fix_5_7_for_host(host, username, password, port=22):
    print(f"[{host}] Đang sửa lỗi CIS 5.7 (Disable MAC Address Changes on vSwitch0)...")
    cmd = "esxcli network vswitch standard policy security set -v vSwitch0 -m false"
    run_ssh_command(host, username, password, cmd, port=port)
    return True


def check_5_8_for_host(host: str, username: str, password: str, port: int = 22) -> dict:
    print(f"\n=== Kiểm tra CIS 5.8 trên host {host} ===")
    cmd = "esxcli network vswitch standard policy security get -v vSwitch0"
    out = run_ssh_command(host, username, password, cmd, port=port)
    
    # Key: Allow Promiscuous
    allow_promiscuous = parse_vswitch_policy(out, "Allow Promiscuous")
    
    ok = False
    if allow_promiscuous is None:
        print(f"[{host}] KHÔNG đọc được giá trị Allow Promiscuous.")
    else:
        print(f"[{host}] Allow Promiscuous: {allow_promiscuous}")
        # Yêu cầu: false
        if not allow_promiscuous:
            ok = True
        else:
            ok = False
            
    print(f"[{host}] KẾT LUẬN CIS 5.8: {'ĐẠT' if ok else 'KHÔNG ĐẠT'}")
    return {"host": host, "cis_5_8_ok": ok, "detail": {"allow_promiscuous": allow_promiscuous}}

def fix_5_8_for_host(host, username, password, port=22):
    print(f"[{host}] Đang sửa lỗi CIS 5.8 (Disable Allow Promiscuous on vSwitch0)...")
    cmd = "esxcli network vswitch standard policy security set -v vSwitch0 -p false"
    run_ssh_command(host, username, password, cmd, port=port)
    return True


def get_standard_portgroups(host, username, password, port=22):
    """Lấy danh sách standard port groups từ ESXi."""
    cmd = "esxcli network vswitch standard portgroup list"
    out = run_ssh_command(host, username, password, cmd, port=port)
    
    pgs = []
    lines = out.splitlines()
    start_parsing = False
    for line in lines:
        if line.strip().startswith("----"):
            start_parsing = True
            continue
        if not start_parsing:
            continue
        if not line.strip():
            continue
            
        parts = line.split()
        if len(parts) >= 4:
            try:
                vlan = int(parts[-1])
                name = " ".join(parts[:-3])
                pgs.append({"name": name, "vlan": vlan})
            except ValueError:
                pass
    return pgs

def check_5_9_and_5_10_for_host(host: str, username: str, password: str, port: int = 22) -> dict:
    print(f"\n=== Kiểm tra CIS 5.9 và 5.10 trên host {host} ===")
    pgs = get_standard_portgroups(host, username, password, port)
    
    bad_pgs = [pg for pg in pgs if pg['vlan'] in [0, 1, 4095]]
    
    if bad_pgs:
        print(f"[{host}] Các Port Group vi phạm (VLAN 0, 1, 4095):")
        for pg in bad_pgs:
            print(f"  - {pg['name']}: VLAN {pg['vlan']}")
        ok = False
    else:
        print(f"[{host}] Tất cả Port Group đều có VLAN hợp lệ (khác 0, 1, 4095).")
        ok = True
        
    print(f"[{host}] KẾT LUẬN CIS 5.9 và 5.10: {'ĐẠT' if ok else 'KHÔNG ĐẠT'}")
    return {"host": host, "cis_5_9_and_5_10_ok": ok, "detail": {"bad_pgs": bad_pgs}}

def fix_5_9_and_5_10_for_host(host, username, password, port=22):
    print(f"[{host}] Đang tìm kiếm các Port Group vi phạm để sửa lỗi CIS 5.9 và 5.10...")
    pgs = get_standard_portgroups(host, username, password, port)
    bad_pgs = [pg for pg in pgs if pg['vlan'] in [0, 1, 4095]]

    if not bad_pgs:
        print(f"[{host}] Không tìm thấy Port Group nào có VLAN 0, 1, 4095 để sửa.")
        return True

    print(f"[{host}] Tìm thấy {len(bad_pgs)} Port Group cần sửa:")
    for pg in bad_pgs:
        print(f"  - {pg['name']} (Hiện tại: VLAN {pg['vlan']})")
        
        while True:
            new_vlan_str = input(f"    >> Nhập VLAN ID mới cho '{pg['name']}' (ví dụ 20): ").strip()
            if new_vlan_str.isdigit():
                new_vlan = int(new_vlan_str)
                if new_vlan > 1 and new_vlan < 4095:
                    break
                else:
                    print("    !! Vui lòng nhập VLAN ID > 1 và < 4095.")
            else:
                print("    !! Vui lòng nhập số nguyên.")

        print(f"    -> Đang set VLAN {new_vlan} cho '{pg['name']}'...")
        cmd_fix = f'esxcli network vswitch standard portgroup set -p "{pg["name"]}" -v {new_vlan}'
        run_ssh_command(host, username, password, cmd_fix, port=port)
        
    return True


def parse_vms_list(output: str):
    """Parse 'vim-cmd vmsvc/getallvms' output."""
    vms = []
    lines = output.splitlines()
    # Skip header line (starts with Vmid)
    data_lines = [line for line in lines if line.strip() and not line.strip().startswith("Vmid")]
    
    for line in data_lines:
        # Heuristic parsing:
        # Vmid is first token (int)
        # File path starts with '['
        parts = line.split()
        if not parts: continue
        
        try:
            vmid = parts[0]
            int(vmid) # Check if it is number
            
            # Find where file path starts (usually with [datastore])
            path_start_idx = -1
            for i, p in enumerate(parts):
                if p.startswith("["):
                    path_start_idx = i
                    break
            
            if path_start_idx != -1:
                # Name is everything between vmid and file path
                name = " ".join(parts[1:path_start_idx])
                
                # File path might contain spaces, it ends before GuestOS column?
                # Simpler approach: File path starts with [ and ends with .vmx or .vmxf
                # Let's grep the whole line for the substring starting with [ and ending with .vmx
                # Re-construct line from parts to handle spacing
                
                # Simple extraction from tokens
                # We assume path doesn't have weird chars, but spaces are possible.
                # The columns after path are Guest OS, Version, Annotation.
                # Guest OS usually starts with 'windows', 'rhel', 'ubuntu', 'other', etc.
                # Version starts with 'vmx-'
                
                # Let's just take the part starting with [ until .vmx
                line_rest = " ".join(parts[path_start_idx:])
                if ".vmx" in line_rest:
                    raw_path = line_rest.split(".vmx")[0] + ".vmx"
                    
                    # Convert [datastore] path to /vmfs/volumes/datastore/path
                    # Example: [nvme_ssd] Windows1/Windows1.vmx -> /vmfs/volumes/nvme_ssd/Windows1/Windows1.vmx
                    path = raw_path
                    if raw_path.startswith("["):
                        ds_end = raw_path.find("]")
                        if ds_end != -1:
                            ds_name = raw_path[1:ds_end]
                            rel_path = raw_path[ds_end+1:].strip()
                            path = f"/vmfs/volumes/{ds_name}/{rel_path}"
                            
                    vms.append({"vmid": vmid, "name": name, "path": path})
        except ValueError:
            continue
            
    return vms

def check_vm_setting_in_file(host, username, password, file_path, setting_key, port=22):
    # Use grep to find the setting in .vmx file as suggested by user
    cmd = f'grep "{setting_key}" "{file_path}"'
    output = run_ssh_command(host, username, password, cmd, port=port)
    
    val = None
    for line in output.splitlines():
        line = line.strip()
        # Ignore comments and ensure assignment
        if not line.startswith("#") and line.startswith(setting_key) and "=" in line:
            parts = line.split("=", 1)
            if len(parts) == 2:
                raw_val = parts[1].strip().replace('"', '')
                val = raw_val
                break
    return val

def check_7_6_for_host(host: str, username: str, password: str, port: int = 22) -> dict:
    print(f"\n=== Kiểm tra CIS 7.6 trên host {host} ===")
    # Get VMs
    out = run_ssh_command(host, username, password, "vim-cmd vmsvc/getallvms", port=port)
    vms = parse_vms_list(out)
    
    if not vms:
        print(f"[{host}] Không tìm thấy máy ảo nào.")
        return {"host": host, "cis_7_6_ok": True, "detail": {"vms": []}}

    # Scan all VMs to check RemoteDisplay.maxConnections parameter
    failed_vms = []
    for vm in vms:
        val = check_vm_setting_in_file(host, username, password, vm['path'], "RemoteDisplay.maxConnections", port)
        if val is None:
            # Không có tham số -> cần thêm
            print(f"  - {vm['name']}: Không có tham số -> KHÔNG ĐẠT (cần thêm)")
            vm['current_value'] = None
            failed_vms.append(vm)
        elif val == "1":
            print(f"  - {vm['name']}: RemoteDisplay.maxConnections = {val} -> ĐẠT")
        else:
            print(f"  - {vm['name']}: RemoteDisplay.maxConnections = {val} -> KHÔNG ĐẠT")
            vm['current_value'] = val
            failed_vms.append(vm)
            
    ok = (len(failed_vms) == 0)
    status_str = "ĐẠT" if ok else "KHÔNG ĐẠT"
    print(f"[{host}] KẾT LUẬN CIS 7.6: {status_str}")
    
    return {"host": host, "cis_7_6_ok": ok, "detail": {"failed_vms": failed_vms}}

def fix_7_6_for_host(host, username, password, port=22, failed_vms=None):
    print(f"[{host}] Đang sửa lỗi CIS 7.6...")
    
    # Nếu không có danh sách failed_vms từ check, phải quét lại
    if failed_vms is None:
        out = run_ssh_command(host, username, password, "vim-cmd vmsvc/getallvms", port=port)
        vms = parse_vms_list(out)
        
        failed_vms = []
        for vm in vms:
            val = check_vm_setting_in_file(host, username, password, vm['path'], "RemoteDisplay.maxConnections", port)
            if val is None or val != "1":
                vm['current_value'] = val
                failed_vms.append(vm)
    
    if not failed_vms:
        print(f"[{host}] Không có VM nào cần sửa lỗi CIS 7.6.")
        return True

    # Hiển thị danh sách VM để chọn
    print(f"[{host}] Danh sách VM cần sửa:")
    for i, vm in enumerate(failed_vms):
        print(f"  {i+1}. {vm['name']}")
    
    print("\nChọn VM để sửa (nhập số thứ tự cách nhau bởi dấu phẩy, hoặc 'all' để sửa tất cả):")
    choice = input("Lựa chọn: ").strip()
    
    if choice.lower() == 'all':
        selected_vms = failed_vms
    else:
        selected_vms = []
        indices = choice.replace(",", " ").split()
        for idx in indices:
            if idx.isdigit():
                i = int(idx) - 1
                if 0 <= i < len(failed_vms):
                    selected_vms.append(failed_vms[i])
    
    if not selected_vms:
        print("Không có VM nào được chọn.")
        return False
        
    for vm in selected_vms:
        print(f"   -> Đang sửa VM: {vm['name']}...")
        cmd_del = f'sed -i "/RemoteDisplay.maxConnections/d" "{vm["path"]}"'
        run_ssh_command(host, username, password, cmd_del, port=port)
        cmd_add = f'echo \'RemoteDisplay.maxConnections = "1"\' >> "{vm["path"]}"'
        run_ssh_command(host, username, password, cmd_add, port=port)
        run_ssh_command(host, username, password, f"vim-cmd vmsvc/reload {vm['vmid']}", port=port)
        
    return True


def check_7_21_for_host(host: str, username: str, password: str, port: int = 22) -> dict:
    print(f"\n=== Kiểm tra CIS 7.21 trên host {host} ===")
    # Get VMs
    out = run_ssh_command(host, username, password, "vim-cmd vmsvc/getallvms", port=port)
    vms = parse_vms_list(out)
    
    if not vms:
        print(f"[{host}] Không tìm thấy máy ảo nào.")
        return {"host": host, "cis_7_21_ok": True, "detail": {"vms": []}}

    # Scan all VMs to check isolation.tools.diskShrink.disable parameter
    failed_vms = []
    for vm in vms:
        val = check_vm_setting_in_file(host, username, password, vm['path'], "isolation.tools.diskShrink.disable", port)
        if val is None:
            # Không có tham số -> cần thêm
            print(f"  - {vm['name']}: Không có tham số -> KHÔNG ĐẠT (cần thêm)")
            vm['current_value'] = None
            failed_vms.append(vm)
        elif val.lower() == "true":
            print(f"  - {vm['name']}: isolation.tools.diskShrink.disable = {val} -> ĐẠT")
        else:
            print(f"  - {vm['name']}: isolation.tools.diskShrink.disable = {val} -> KHÔNG ĐẠT")
            vm['current_value'] = val
            failed_vms.append(vm)
            
    ok = (len(failed_vms) == 0)
    status_str = "ĐẠT" if ok else "KHÔNG ĐẠT"
    print(f"[{host}] KẾT LUẬN CIS 7.21: {status_str}")
    
    return {"host": host, "cis_7_21_ok": ok, "detail": {"failed_vms": failed_vms}}

def fix_7_21_for_host(host, username, password, port=22, failed_vms=None):
    print(f"[{host}] Đang sửa lỗi CIS 7.21...")
    
    # Nếu không có danh sách failed_vms từ check, phải quét lại
    if failed_vms is None:
        out = run_ssh_command(host, username, password, "vim-cmd vmsvc/getallvms", port=port)
        vms = parse_vms_list(out)
        
        failed_vms = []
        for vm in vms:
            val = check_vm_setting_in_file(host, username, password, vm['path'], "isolation.tools.diskShrink.disable", port)
            if val is None or val.lower() != "true":
                vm['current_value'] = val
                failed_vms.append(vm)
    
    if not failed_vms:
        print(f"[{host}] Không có VM nào cần sửa lỗi CIS 7.21.")
        return True

    # Hiển thị danh sách VM để chọn
    print(f"[{host}] Danh sách VM cần sửa:")
    for i, vm in enumerate(failed_vms):
        print(f"  {i+1}. {vm['name']}")
    
    print("\nChọn VM để sửa (nhập số thứ tự cách nhau bởi dấu phẩy, hoặc 'all' để sửa tất cả):")
    choice = input("Lựa chọn: ").strip()
    
    if choice.lower() == 'all':
        selected_vms = failed_vms
    else:
        selected_vms = []
        indices = choice.replace(",", " ").split()
        for idx in indices:
            if idx.isdigit():
                i = int(idx) - 1
                if 0 <= i < len(failed_vms):
                    selected_vms.append(failed_vms[i])
    
    if not selected_vms:
        print("Không có VM nào được chọn.")
        return False
        
    for vm in selected_vms:
        print(f"   -> Đang sửa VM: {vm['name']}...")
        cmd_del = f'sed -i "/isolation.tools.diskShrink.disable/d" "{vm["path"]}"'
        run_ssh_command(host, username, password, cmd_del, port=port)
        cmd_add = f'echo \'isolation.tools.diskShrink.disable = "TRUE"\' >> "{vm["path"]}"'
        run_ssh_command(host, username, password, cmd_add, port=port)
        run_ssh_command(host, username, password, f"vim-cmd vmsvc/reload {vm['vmid']}", port=port)
        
    return True


def check_7_22_for_host(host: str, username: str, password: str, port: int = 22) -> dict:
    print(f"\n=== Kiểm tra CIS 7.22 trên host {host} ===")
    # Get VMs
    out = run_ssh_command(host, username, password, "vim-cmd vmsvc/getallvms", port=port)
    vms = parse_vms_list(out)
    
    if not vms:
        print(f"[{host}] Không tìm thấy máy ảo nào.")
        return {"host": host, "cis_7_22_ok": True, "detail": {"vms": []}}

    # Scan all VMs to check isolation.tools.diskWiper.disable parameter
    failed_vms = []
    for vm in vms:
        val = check_vm_setting_in_file(host, username, password, vm['path'], "isolation.tools.diskWiper.disable", port)
        if val is None:
            # Không có tham số -> cần thêm
            print(f"  - {vm['name']}: Không có tham số -> KHÔNG ĐẠT (cần thêm)")
            vm['current_value'] = None
            failed_vms.append(vm)
        elif val.lower() == "true":
            print(f"  - {vm['name']}: isolation.tools.diskWiper.disable = {val} -> ĐẠT")
        else:
            print(f"  - {vm['name']}: isolation.tools.diskWiper.disable = {val} -> KHÔNG ĐẠT")
            vm['current_value'] = val
            failed_vms.append(vm)
            
    ok = (len(failed_vms) == 0)
    status_str = "ĐẠT" if ok else "KHÔNG ĐẠT"
    print(f"[{host}] KẾT LUẬN CIS 7.22: {status_str}")
    
    return {"host": host, "cis_7_22_ok": ok, "detail": {"failed_vms": failed_vms}}

def fix_7_22_for_host(host, username, password, port=22, failed_vms=None):
    print(f"[{host}] Đang sửa lỗi CIS 7.22...")
    
    # Nếu không có danh sách failed_vms từ check, phải quét lại
    if failed_vms is None:
        out = run_ssh_command(host, username, password, "vim-cmd vmsvc/getallvms", port=port)
        vms = parse_vms_list(out)
        
        failed_vms = []
        for vm in vms:
            val = check_vm_setting_in_file(host, username, password, vm['path'], "isolation.tools.diskWiper.disable", port)
            if val is None or val.lower() != "true":
                vm['current_value'] = val
                failed_vms.append(vm)
    
    if not failed_vms:
        print(f"[{host}] Không có VM nào cần sửa lỗi CIS 7.22.")
        return True

    # Hiển thị danh sách VM để chọn
    print(f"[{host}] Danh sách VM cần sửa:")
    for i, vm in enumerate(failed_vms):
        print(f"  {i+1}. {vm['name']}")
    
    print("\nChọn VM để sửa (nhập số thứ tự cách nhau bởi dấu phẩy, hoặc 'all' để sửa tất cả):")
    choice = input("Lựa chọn: ").strip()
    
    if choice.lower() == 'all':
        selected_vms = failed_vms
    else:
        selected_vms = []
        indices = choice.replace(",", " ").split()
        for idx in indices:
            if idx.isdigit():
                i = int(idx) - 1
                if 0 <= i < len(failed_vms):
                    selected_vms.append(failed_vms[i])
    
    if not selected_vms:
        print("Không có VM nào được chọn.")
        return False
        
    for vm in selected_vms:
        print(f"   -> Đang sửa VM: {vm['name']}...")
        cmd_del = f'sed -i "/isolation.tools.diskWiper.disable/d" "{vm["path"]}"'
        run_ssh_command(host, username, password, cmd_del, port=port)
        cmd_add = f'echo \'isolation.tools.diskWiper.disable = "TRUE"\' >> "{vm["path"]}"'
        run_ssh_command(host, username, password, cmd_add, port=port)
        run_ssh_command(host, username, password, f"vim-cmd vmsvc/reload {vm['vmid']}", port=port)
        
    return True


def check_7_24_for_host(host: str, username: str, password: str, port: int = 22) -> dict:
    print(f"\n=== Kiểm tra CIS 7.24 trên host {host} ===")
    # Get VMs
    out = run_ssh_command(host, username, password, "vim-cmd vmsvc/getallvms", port=port)
    vms = parse_vms_list(out)
    
    if not vms:
        print(f"[{host}] Không tìm thấy máy ảo nào.")
        return {"host": host, "cis_7_24_ok": True, "detail": {"vms": []}}

    # Scan all VMs to check tools.guestlib.enableHostInfo parameter
    failed_vms = []
    for vm in vms:
        val = check_vm_setting_in_file(host, username, password, vm['path'], "tools.guestlib.enableHostInfo", port)
        if val is None:
            # Không có tham số -> cần thêm
            print(f"  - {vm['name']}: Không có tham số -> KHÔNG ĐẠT (cần thêm)")
            vm['current_value'] = None
            failed_vms.append(vm)
        elif val.lower() == "false":
            print(f"  - {vm['name']}: tools.guestlib.enableHostInfo = {val} -> ĐẠT")
        else:
            print(f"  - {vm['name']}: tools.guestlib.enableHostInfo = {val} -> KHÔNG ĐẠT")
            vm['current_value'] = val
            failed_vms.append(vm)
            
    ok = (len(failed_vms) == 0)
    status_str = "ĐẠT" if ok else "KHÔNG ĐẠT"
    print(f"[{host}] KẾT LUẬN CIS 7.24: {status_str}")
    
    return {"host": host, "cis_7_24_ok": ok, "detail": {"failed_vms": failed_vms}}

def fix_7_24_for_host(host, username, password, port=22, failed_vms=None):
    print(f"[{host}] Đang sửa lỗi CIS 7.24...")
    
    # Nếu không có danh sách failed_vms từ check, phải quét lại
    if failed_vms is None:
        out = run_ssh_command(host, username, password, "vim-cmd vmsvc/getallvms", port=port)
        vms = parse_vms_list(out)
        
        failed_vms = []
        for vm in vms:
            val = check_vm_setting_in_file(host, username, password, vm['path'], "tools.guestlib.enableHostInfo", port)
            if val is None or val.lower() != "false":
                vm['current_value'] = val
                failed_vms.append(vm)
    
    if not failed_vms:
        print(f"[{host}] Không có VM nào cần sửa lỗi CIS 7.24.")
        return True

    # Hiển thị danh sách VM để chọn
    print(f"[{host}] Danh sách VM cần sửa:")
    for i, vm in enumerate(failed_vms):
        print(f"  {i+1}. {vm['name']}")
    
    print("\nChọn VM để sửa (nhập số thứ tự cách nhau bởi dấu phẩy, hoặc 'all' để sửa tất cả):")
    choice = input("Lựa chọn: ").strip()
    
    if choice.lower() == 'all':
        selected_vms = failed_vms
    else:
        selected_vms = []
        indices = choice.replace(",", " ").split()
        for idx in indices:
            if idx.isdigit():
                i = int(idx) - 1
                if 0 <= i < len(failed_vms):
                    selected_vms.append(failed_vms[i])
    
    if not selected_vms:
        print("Không có VM nào được chọn.")
        return False
        
    for vm in selected_vms:
        print(f"   -> Đang sửa VM: {vm['name']}...")
        cmd_del = f'sed -i "/tools.guestlib.enableHostInfo/d" "{vm["path"]}"'
        run_ssh_command(host, username, password, cmd_del, port=port)
        cmd_add = f'echo \'tools.guestlib.enableHostInfo = "FALSE"\' >> "{vm["path"]}"'
        run_ssh_command(host, username, password, cmd_add, port=port)
        run_ssh_command(host, username, password, f"vim-cmd vmsvc/reload {vm['vmid']}", port=port)
        
    return True


def check_7_26_for_host(host: str, username: str, password: str, port: int = 22) -> dict:
    print(f"\n=== Kiểm tra CIS 7.26 trên host {host} ===")
    # Get VMs
    out = run_ssh_command(host, username, password, "vim-cmd vmsvc/getallvms", port=port)
    vms = parse_vms_list(out)
    
    if not vms:
        print(f"[{host}] Không tìm thấy máy ảo nào.")
        return {"host": host, "cis_7_26_ok": True, "detail": {"vms": []}}

    # Scan all VMs to check log.keepOld parameter
    failed_vms = []
    for vm in vms:
        val = check_vm_setting_in_file(host, username, password, vm['path'], "log.keepOld", port)
        if val is None:
            # Không có tham số -> cần thêm
            print(f"  - {vm['name']}: Không có tham số -> KHÔNG ĐẠT (cần thêm)")
            vm['current_value'] = None
            failed_vms.append(vm)
        elif val == "10":
            print(f"  - {vm['name']}: log.keepOld = {val} -> ĐẠT")
        else:
            print(f"  - {vm['name']}: log.keepOld = {val} -> KHÔNG ĐẠT")
            vm['current_value'] = val
            failed_vms.append(vm)
            
    ok = (len(failed_vms) == 0)
    status_str = "ĐẠT" if ok else "KHÔNG ĐẠT"
    print(f"[{host}] KẾT LUẬN CIS 7.26: {status_str}")
    
    return {"host": host, "cis_7_26_ok": ok, "detail": {"failed_vms": failed_vms}}

def fix_7_26_for_host(host, username, password, port=22, failed_vms=None):
    print(f"[{host}] Đang sửa lỗi CIS 7.26...")
    
    # Nếu không có danh sách failed_vms từ check, phải quét lại
    if failed_vms is None:
        out = run_ssh_command(host, username, password, "vim-cmd vmsvc/getallvms", port=port)
        vms = parse_vms_list(out)
        
        failed_vms = []
        for vm in vms:
            val = check_vm_setting_in_file(host, username, password, vm['path'], "log.keepOld", port)
            if val is None or val != "10":
                vm['current_value'] = val
                failed_vms.append(vm)
    
    if not failed_vms:
        print(f"[{host}] Không có VM nào cần sửa lỗi CIS 7.26.")
        return True

    # Hiển thị danh sách VM để chọn
    print(f"[{host}] Danh sách VM cần sửa:")
    for i, vm in enumerate(failed_vms):
        print(f"  {i+1}. {vm['name']}")
    
    print("\nChọn VM để sửa (nhập số thứ tự cách nhau bởi dấu phẩy, hoặc 'all' để sửa tất cả):")
    choice = input("Lựa chọn: ").strip()
    
    if choice.lower() == 'all':
        selected_vms = failed_vms
    else:
        selected_vms = []
        indices = choice.replace(",", " ").split()
        for idx in indices:
            if idx.isdigit():
                i = int(idx) - 1
                if 0 <= i < len(failed_vms):
                    selected_vms.append(failed_vms[i])
    
    if not selected_vms:
        print("Không có VM nào được chọn.")
        return False
        
    for vm in selected_vms:
        print(f"   -> Đang sửa VM: {vm['name']}...")
        cmd_del = f'sed -i "/log.keepOld/d" "{vm["path"]}"'
        run_ssh_command(host, username, password, cmd_del, port=port)
        cmd_add = f'echo \'log.keepOld = "10"\' >> "{vm["path"]}"'
        run_ssh_command(host, username, password, cmd_add, port=port)
        run_ssh_command(host, username, password, f"vim-cmd vmsvc/reload {vm['vmid']}", port=port)
        
    return True


def check_7_27_for_host(host: str, username: str, password: str, port: int = 22) -> dict:
    print(f"\n=== Kiểm tra CIS 7.27 trên host {host} ===")
    # Get VMs
    out = run_ssh_command(host, username, password, "vim-cmd vmsvc/getallvms", port=port)
    vms = parse_vms_list(out)
    
    if not vms:
        print(f"[{host}] Không tìm thấy máy ảo nào.")
        return {"host": host, "cis_7_27_ok": True, "detail": {"vms": []}}

    # Scan all VMs to check log.rotateSize parameter
    failed_vms = []
    for vm in vms:
        val = check_vm_setting_in_file(host, username, password, vm['path'], "log.rotateSize", port)
        if val is None:
            # Không có tham số -> cần thêm
            print(f"  - {vm['name']}: Không có tham số -> KHÔNG ĐẠT (cần thêm)")
            vm['current_value'] = None
            failed_vms.append(vm)
        elif val == "1000000":
            print(f"  - {vm['name']}: log.rotateSize = {val} -> ĐẠT")
        else:
            print(f"  - {vm['name']}: log.rotateSize = {val} -> KHÔNG ĐẠT")
            vm['current_value'] = val
            failed_vms.append(vm)
            
    ok = (len(failed_vms) == 0)
    status_str = "ĐẠT" if ok else "KHÔNG ĐẠT"
    print(f"[{host}] KẾT LUẬN CIS 7.27: {status_str}")
    
    return {"host": host, "cis_7_27_ok": ok, "detail": {"failed_vms": failed_vms}}

def fix_7_27_for_host(host, username, password, port=22, failed_vms=None):
    print(f"[{host}] Đang sửa lỗi CIS 7.27...")
    
    # Nếu không có danh sách failed_vms từ check, phải quét lại
    if failed_vms is None:
        out = run_ssh_command(host, username, password, "vim-cmd vmsvc/getallvms", port=port)
        vms = parse_vms_list(out)
        
        failed_vms = []
        for vm in vms:
            val = check_vm_setting_in_file(host, username, password, vm['path'], "log.rotateSize", port)
            if val is None or val != "1000000":
                vm['current_value'] = val
                failed_vms.append(vm)
    
    if not failed_vms:
        print(f"[{host}] Không có VM nào cần sửa lỗi CIS 7.27.")
        return True

    # Hiển thị danh sách VM để chọn
    print(f"[{host}] Danh sách VM cần sửa:")
    for i, vm in enumerate(failed_vms):
        print(f"  {i+1}. {vm['name']}")
    
    print("\nChọn VM để sửa (nhập số thứ tự cách nhau bởi dấu phẩy, hoặc 'all' để sửa tất cả):")
    choice = input("Lựa chọn: ").strip()
    
    if choice.lower() == 'all':
        selected_vms = failed_vms
    else:
        selected_vms = []
        indices = choice.replace(",", " ").split()
        for idx in indices:
            if idx.isdigit():
                i = int(idx) - 1
                if 0 <= i < len(failed_vms):
                    selected_vms.append(failed_vms[i])
    
    if not selected_vms:
        print("Không có VM nào được chọn.")
        return False
        
    for vm in selected_vms:
        print(f"   -> Đang sửa VM: {vm['name']}...")
        cmd_del = f'sed -i "/log.rotateSize/d" "{vm["path"]}"'
        run_ssh_command(host, username, password, cmd_del, port=port)
        cmd_add = f'echo \'log.rotateSize = "1000000"\' >> "{vm["path"]}"'
        run_ssh_command(host, username, password, cmd_add, port=port)
        run_ssh_command(host, username, password, f"vim-cmd vmsvc/reload {vm['vmid']}", port=port)
        
    return True


def get_user_sections(available_sections):
    print("\nChọn các phần kiểm tra (cách nhau bởi dấu phẩy/khoảng trắng) hoặc Enter để chọn tất cả:")
    choice_input = input("Nhập phần cần kiểm tra: ").strip()
    
    if not choice_input:
        return available_sections.copy()
    
    choices = choice_input.replace(",", " ").split()
    sections_to_run = set()
    
    for c in choices:
        c = c.strip()
        if c in available_sections:
            sections_to_run.add(c)
        else:
            print(f"Bỏ qua lựa chọn không hợp lệ: {c}")
            
    if not sections_to_run:
        print("Không có lựa chọn hợp lệ. Mặc định chạy tất cả.")
        return available_sections.copy()
        
    return sections_to_run

if __name__ == "__main__":
    ESXI_HOSTS = [
        {"host": "192.168.8.131", "username": "root", "password": "Khoa@3003"},
    ]
    
    AVAILABLE_SECTIONS = ["2.4", "2.10", "3.3", "3.7", "3.8", "3.9", "3.12", "3.13", "4.2", "5.6", "5.7", "5.8", "5.9", "5.10", "7.6", "7.21", "7.22", "7.24", "7.26", "7.27"]
    sections_to_run = get_user_sections(AVAILABLE_SECTIONS)
    
    print(f"\n>>> BẮT ĐẦU KIỂM TRA: {', '.join(sorted(sections_to_run))}\n")
    
    all_results = {} 
    # Structure: { host_ip: { section_id: { 'ok': bool, 'detail': ... } } }

    for info in ESXI_HOSTS:
        host = info["host"]
        all_results[host] = {}
        
        print(f"========== KIỂM TRA HOST {host} ==========")
        
        if "2.4" in sections_to_run:
            res = check_2_4_for_host(host, info["username"], info["password"])
            all_results[host]["2.4"] = res
            
        if "2.10" in sections_to_run:
            res = check_2_10_for_host(host, info["username"], info["password"])
            all_results[host]["2.10"] = res
            
        if "3.3" in sections_to_run:
            res = check_3_3_for_host(host, info["username"], info["password"])
            all_results[host]["3.3"] = res
            
        if "3.7" in sections_to_run:
            res = check_3_7_for_host(host, info["username"], info["password"])
            all_results[host]["3.7"] = res
            
        if "3.8" in sections_to_run:
            res = check_3_8_for_host(host, info["username"], info["password"])
            all_results[host]["3.8"] = res
            
        if "3.9" in sections_to_run:
            res = check_3_9_for_host(host, info["username"], info["password"])
            all_results[host]["3.9"] = res

        if "3.12" in sections_to_run:
            res = check_3_12_for_host(host, info["username"], info["password"])
            all_results[host]["3.12"] = res

        if "3.13" in sections_to_run:
            res = check_3_13_for_host(host, info["username"], info["password"])
            all_results[host]["3.13"] = res

        if "4.2" in sections_to_run:
            res = check_4_2_for_host(host, info["username"], info["password"])
            all_results[host]["4.2"] = res

        if "5.6" in sections_to_run:
            res = check_5_6_for_host(host, info["username"], info["password"])
            all_results[host]["5.6"] = res

        if "5.7" in sections_to_run:
            res = check_5_7_for_host(host, info["username"], info["password"])
            all_results[host]["5.7"] = res

        if "5.8" in sections_to_run:
            res = check_5_8_for_host(host, info["username"], info["password"])
            all_results[host]["5.8"] = res

        if "5.9" in sections_to_run or "5.10" in sections_to_run:
            res = check_5_9_and_5_10_for_host(host, info["username"], info["password"])
            if "5.9" in sections_to_run:
                all_results[host]["5.9"] = res
            if "5.10" in sections_to_run:
                all_results[host]["5.10"] = res

        if "7.6" in sections_to_run:
            res = check_7_6_for_host(host, info["username"], info["password"])
            all_results[host]["7.6"] = res

        if "7.21" in sections_to_run:
            res = check_7_21_for_host(host, info["username"], info["password"])
            all_results[host]["7.21"] = res

        if "7.22" in sections_to_run:
            res = check_7_22_for_host(host, info["username"], info["password"])
            all_results[host]["7.22"] = res

        if "7.24" in sections_to_run:
            res = check_7_24_for_host(host, info["username"], info["password"])
            all_results[host]["7.24"] = res

        if "7.26" in sections_to_run:
            res = check_7_26_for_host(host, info["username"], info["password"])
            all_results[host]["7.26"] = res

        if "7.27" in sections_to_run:
            res = check_7_27_for_host(host, info["username"], info["password"])
            all_results[host]["7.27"] = res

    # Tổng hợp kết quả
    print("\n\n============================================================")
    print("                   TỔNG HỢP KẾT QUẢ")
    print("============================================================")
    
    failed_checks = [] # List of (host, section)
    
    for host, sections in all_results.items():
        print(f"\nHOST: {host}")
        # Sắp xếp theo thứ tự số
        sorted_sections = sorted(sections.keys(), key=lambda x: [int(n) for n in x.split('.')])
        for sec_id in sorted_sections:
            data = sections[sec_id]
            # Key trong dict trả về là cis_X_X_ok, ta cần lấy giá trị đó
            # Map sec_id sang key
            is_ok = False
            if sec_id == "2.4": is_ok = data["cis_2_4_ok"]
            elif sec_id == "2.10": is_ok = data["cis_2_10_ok"]
            elif sec_id == "3.3": is_ok = data["cis_3_3_ok"]
            elif sec_id == "3.7": is_ok = data["cis_3_7_ok"]
            elif sec_id == "3.8": is_ok = data["cis_3_8_ok"]
            elif sec_id == "3.9": is_ok = data["cis_3_9_ok"]
            elif sec_id == "3.12": is_ok = data["cis_3_12_ok"]
            elif sec_id == "3.13": is_ok = data["cis_3_13_ok"]
            elif sec_id == "4.2": is_ok = data["cis_4_2_ok"]
            elif sec_id == "5.6": is_ok = data["cis_5_6_ok"]
            elif sec_id == "5.7": is_ok = data["cis_5_7_ok"]
            elif sec_id == "5.8": is_ok = data["cis_5_8_ok"]
            elif sec_id == "5.9": is_ok = data["cis_5_9_and_5_10_ok"]
            elif sec_id == "5.10": is_ok = data["cis_5_9_and_5_10_ok"]
            elif sec_id == "7.6": is_ok = data["cis_7_6_ok"]
            elif sec_id == "7.21": is_ok = data["cis_7_21_ok"]
            elif sec_id == "7.22": is_ok = data["cis_7_22_ok"]
            elif sec_id == "7.24": is_ok = data["cis_7_24_ok"]
            elif sec_id == "7.26": is_ok = data["cis_7_26_ok"]
            elif sec_id == "7.27": is_ok = data["cis_7_27_ok"]
            
            status_str = "ĐẠT" if is_ok else "KHÔNG ĐẠT"
            print(f"  - {sec_id}: {status_str}")
            
            if not is_ok:
                failed_checks.append((host, sec_id))

    if not failed_checks:
        print("\n>>> TẤT CẢ CÁC MỤC KIỂM TRA ĐỀU ĐẠT! Không cần sửa lỗi.")
        exit(0)
        
    print("\n============================================================")
    ask_fix = input("Bạn có muốn sửa các mục KHÔNG ĐẠT không? (y/n): ").strip().lower()
    
    if ask_fix != 'y':
        print("Đã kết thúc chương trình. Không thực hiện sửa đổi.")
        exit(0)
        
    print("\nNhập các phần muốn sửa (ví dụ: 3.8, 3.9) hoặc nhấn Enter để sửa TẤT CẢ các lỗi tìm thấy.")
    fix_choice = input("Lựa chọn: ").strip()
    
    sections_to_fix = set()
    if not fix_choice:
        # Fix all failures
        sections_to_fix = set([x[1] for x in failed_checks])
    else:
        choices = fix_choice.replace(",", " ").split()
        for c in choices:
            c = c.strip()
            if c in AVAILABLE_SECTIONS:
                sections_to_fix.add(c)
            else:
                print(f"Bỏ qua lựa chọn không hợp lệ hoặc không hỗ trợ fix: {c}")

    # Map section ID to fix function
    fix_funcs = {
        "2.4": fix_2_4_for_host,
        "2.10": fix_2_10_for_host,
        "3.3": fix_3_3_for_host,
        "3.7": fix_3_7_for_host,
        "3.8": fix_3_8_for_host,
        "3.9": fix_3_9_for_host,
        "3.12": fix_3_12_for_host,
        "3.13": fix_3_13_for_host,
        "4.2": fix_4_2_for_host,
        "5.6": fix_5_6_for_host,
        "5.7": fix_5_7_for_host,
        "5.8": fix_5_8_for_host,
        "5.9": fix_5_9_and_5_10_for_host,
        "5.10": fix_5_9_and_5_10_for_host,
        "7.6": fix_7_6_for_host,
        "7.21": fix_7_21_for_host,
        "7.22": fix_7_22_for_host,
        "7.24": fix_7_24_for_host,
        "7.26": fix_7_26_for_host,
        "7.27": fix_7_27_for_host
    }
    
    print("\n>>> TIẾN HÀNH SỬA LỖI...\n")
    
    for host, sec_id in failed_checks:
        if sec_id in sections_to_fix:
            if sec_id in fix_funcs:
                func = fix_funcs[sec_id]
                # Lấy thông tin credential
                creds = next((h for h in ESXI_HOSTS if h["host"] == host), None)
                if creds:
                    try:
                        # Với các mục 7.x, truyền thêm danh sách failed_vms từ kết quả kiểm tra
                        if sec_id in ["7.6", "7.21", "7.22", "7.24", "7.26", "7.27"] and host in all_results and sec_id in all_results[host]:
                            failed_vms = all_results[host][sec_id].get("detail", {}).get("failed_vms", None)
                            func(host, creds["username"], creds["password"], failed_vms=failed_vms)
                        else:
                            func(host, creds["username"], creds["password"])
                        print(f"   -> Đã gửi lệnh sửa cho {sec_id} trên {host}.")
                    except Exception as e:
                        print(f"   -> LỖI khi sửa {sec_id} trên {host}: {e}")
            else:
                print(f"[{host}] Mục {sec_id} chưa có script tự động sửa (hoặc là mục kiểm tra phức tạp).")
    
    print("\n>>> Đã hoàn tất quá trình sửa lỗi. Vui lòng chạy lại kiểm tra để xác nhận.")
