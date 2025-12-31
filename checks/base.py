"""
CIS VMware ESXi 8 - Section 2: Base Checks
- 2.4: Host image profile acceptance level must be PartnerSupported or higher
- 2.10: Mem.ShareForceSalting must be set to 2
"""

from utils import run_ssh_command

ALLOWED_LEVELS = {"VMwareCertified", "VMwareAccepted", "PartnerSupported"}

def parse_host_acceptance_level(output: str) -> str | None:
    """Parse acceptance level từ output của esxcli software acceptance get."""
    for line in output.splitlines():
        line = line.strip()
        if line:
            return line
    return None


def parse_bad_vibs(output: str):
    """Parse danh sách VIB không đạt yêu cầu."""
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


def check_2_4_for_host(host, username, password, port=22, key_path=None):
    """
    CIS 2.4: Kiểm tra Host image profile acceptance level
    Phải là VMwareCertified, VMwareAccepted, hoặc PartnerSupported
    """
    print(f"\n=== Kiểm tra 2.4 trên host {host} ===")
    out_accept = run_ssh_command(host, username, password, "esxcli software acceptance get", port=port, key_path=key_path)
    host_level = parse_host_acceptance_level(out_accept)

    if host_level is None:
        print(f"[{host}] KHÔNG đọc được acceptance level từ output:")
        print(out_accept)
        host_level_ok = False
    else:
        host_level_ok = host_level in ALLOWED_LEVELS
        status = "ĐẠT" if host_level_ok else "KHÔNG ĐẠT"
        print(f"[{host}] Host acceptance level: {host_level} -> {status}")

    out_vibs = run_ssh_command(host, username, password, "esxcli software vib list", port=port, key_path=key_path)
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


def fix_2_4_for_host(host, username, password, port=22, key_path=None):
    """Sửa lỗi CIS 2.4: Set acceptance level = PartnerSupported."""
    print(f"[{host}] Đang sửa lỗi CIS 2.4 (Set acceptance level = PartnerSupported)...")
    cmd = "esxcli software acceptance set --level=PartnerSupported"
    run_ssh_command(host, username, password, cmd, port=port, key_path=key_path)
    return True


def parse_mem_share_force_salting(output: str) -> tuple[int | None, str]:
    """Parse giá trị Mem.ShareForceSalting."""
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


def check_2_10_for_host(host: str, username: str, password: str, port: int = 22, key_path: str = None) -> dict:
    """
    CIS 2.10: Kiểm tra Mem.ShareForceSalting
    Yêu cầu: giá trị phải bằng 2
    """
    print(f"\n=== Kiểm tra CIS 2.10 trên host {host} ===")
    cmd = "esxcli system settings advanced list -o /Mem/ShareForceSalting"
    out = run_ssh_command(host, username, password, cmd, port=port, key_path=key_path)
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


def fix_2_10_for_host(host, username, password, port=22, key_path=None):
    """Sửa lỗi CIS 2.10: Set Mem.ShareForceSalting = 2."""
    print(f"[{host}] Đang sửa lỗi CIS 2.10 (Set Mem.ShareForceSalting = 2)...")
    cmd = "esxcli system settings advanced set -o /Mem/ShareForceSalting -i 2"
    run_ssh_command(host, username, password, cmd, port=port, key_path=key_path)
    return True

