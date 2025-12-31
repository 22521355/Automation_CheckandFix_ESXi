"""
CIS VMware ESXi 8 - Section 5: Network Checks
- 5.6: Reject Forged Transmits on vSwitch
- 5.7: Reject MAC Address Changes on vSwitch
- 5.8: Reject Promiscuous Mode on vSwitch
- 5.9 & 5.10: Port Group VLAN checks (không dùng VLAN 0, 1, 4095)
"""

from utils import run_ssh_command


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


def get_standard_portgroups(host, username, password, port=22, key_path=None):
    """Lấy danh sách standard port groups từ ESXi."""
    cmd = "esxcli network vswitch standard portgroup list"
    out = run_ssh_command(host, username, password, cmd, port=port, key_path=key_path)
    
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


# ==================== CIS 5.6 ====================

def check_5_6_for_host(host: str, username: str, password: str, port: int = 22, key_path: str = None) -> dict:
    """
    CIS 5.6: Kiểm tra Allow Forged Transmits trên vSwitch0
    Yêu cầu: phải là false
    """
    print(f"\n=== Kiểm tra CIS 5.6 trên host {host} ===")
    cmd = "esxcli network vswitch standard policy security get -v vSwitch0"
    out = run_ssh_command(host, username, password, cmd, port=port, key_path=key_path)
    
    allow_forged = parse_vswitch_policy(out, "Allow Forged Transmits")
    
    ok = False
    if allow_forged is None:
        print(f"[{host}] KHÔNG đọc được giá trị Allow Forged Transmits.")
    else:
        print(f"[{host}] Allow Forged Transmits: {allow_forged}")
        if not allow_forged:
            ok = True
            
    print(f"[{host}] KẾT LUẬN CIS 5.6: {'ĐẠT' if ok else 'KHÔNG ĐẠT'}")
    return {"host": host, "cis_5_6_ok": ok, "detail": {"allow_forged_transmits": allow_forged}}


def fix_5_6_for_host(host, username, password, port=22, key_path=None):
    """Sửa lỗi CIS 5.6: Disable Allow Forged Transmits trên vSwitch0."""
    print(f"[{host}] Đang sửa lỗi CIS 5.6 (Disable Allow Forged Transmits on vSwitch0)...")
    cmd = "esxcli network vswitch standard policy security set -v vSwitch0 -f false"
    run_ssh_command(host, username, password, cmd, port=port, key_path=key_path)
    return True


# ==================== CIS 5.7 ====================

def check_5_7_for_host(host: str, username: str, password: str, port: int = 22, key_path: str = None) -> dict:
    """
    CIS 5.7: Kiểm tra Allow MAC Address Changes trên vSwitch0
    Yêu cầu: phải là false
    """
    print(f"\n=== Kiểm tra CIS 5.7 trên host {host} ===")
    cmd = "esxcli network vswitch standard policy security get -v vSwitch0"
    out = run_ssh_command(host, username, password, cmd, port=port, key_path=key_path)
    
    allow_mac_change = parse_vswitch_policy(out, "Allow MAC Address Change")
    
    ok = False
    if allow_mac_change is None:
        print(f"[{host}] KHÔNG đọc được giá trị MAC Address Changes.")
    else:
        print(f"[{host}] Allow MAC Address Changes: {allow_mac_change}")
        if not allow_mac_change:
            ok = True
            
    print(f"[{host}] KẾT LUẬN CIS 5.7: {'ĐẠT' if ok else 'KHÔNG ĐẠT'}")
    return {"host": host, "cis_5_7_ok": ok, "detail": {"allow_mac_change": allow_mac_change}}


def fix_5_7_for_host(host, username, password, port=22, key_path=None):
    """Sửa lỗi CIS 5.7: Disable MAC Address Changes trên vSwitch0."""
    print(f"[{host}] Đang sửa lỗi CIS 5.7 (Disable MAC Address Changes on vSwitch0)...")
    cmd = "esxcli network vswitch standard policy security set -v vSwitch0 -m false"
    run_ssh_command(host, username, password, cmd, port=port, key_path=key_path)
    return True


# ==================== CIS 5.8 ====================

def check_5_8_for_host(host: str, username: str, password: str, port: int = 22, key_path: str = None) -> dict:
    """
    CIS 5.8: Kiểm tra Allow Promiscuous Mode trên vSwitch0
    Yêu cầu: phải là false
    """
    print(f"\n=== Kiểm tra CIS 5.8 trên host {host} ===")
    cmd = "esxcli network vswitch standard policy security get -v vSwitch0"
    out = run_ssh_command(host, username, password, cmd, port=port, key_path=key_path)
    
    allow_promiscuous = parse_vswitch_policy(out, "Allow Promiscuous")
    
    ok = False
    if allow_promiscuous is None:
        print(f"[{host}] KHÔNG đọc được giá trị Allow Promiscuous.")
    else:
        print(f"[{host}] Allow Promiscuous: {allow_promiscuous}")
        if not allow_promiscuous:
            ok = True
            
    print(f"[{host}] KẾT LUẬN CIS 5.8: {'ĐẠT' if ok else 'KHÔNG ĐẠT'}")
    return {"host": host, "cis_5_8_ok": ok, "detail": {"allow_promiscuous": allow_promiscuous}}


def fix_5_8_for_host(host, username, password, port=22, key_path=None):
    """Sửa lỗi CIS 5.8: Disable Allow Promiscuous trên vSwitch0."""
    print(f"[{host}] Đang sửa lỗi CIS 5.8 (Disable Allow Promiscuous on vSwitch0)...")
    cmd = "esxcli network vswitch standard policy security set -v vSwitch0 -p false"
    run_ssh_command(host, username, password, cmd, port=port, key_path=key_path)
    return True


# ==================== CIS 5.9 & 5.10 ====================

def check_5_9_and_5_10_for_host(host: str, username: str, password: str, port: int = 22, key_path: str = None) -> dict:
    """
    CIS 5.9 & 5.10: Kiểm tra VLAN của các Port Groups
    Yêu cầu: không dùng VLAN 0, 1, hoặc 4095
    """
    print(f"\n=== Kiểm tra CIS 5.9 và 5.10 trên host {host} ===")
    pgs = get_standard_portgroups(host, username, password, port, key_path=key_path)
    
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


def fix_5_9_and_5_10_for_host(host, username, password, port=22, key_path=None):
    """Sửa lỗi CIS 5.9 & 5.10: Cập nhật VLAN ID cho các Port Groups vi phạm."""
    print(f"[{host}] Đang tìm kiếm các Port Group vi phạm để sửa lỗi CIS 5.9 và 5.10...")
    pgs = get_standard_portgroups(host, username, password, port, key_path=key_path)
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
        run_ssh_command(host, username, password, cmd_fix, port=port, key_path=key_path)
        
    return True
