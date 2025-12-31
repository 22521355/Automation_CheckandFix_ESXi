"""
CIS VMware ESXi 8 Benchmark Checker
Main entry point - kết nối tất cả các module kiểm tra
"""

import sys
import os
import getpass

# Thêm thư mục gốc vào path để import được các module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

AVAILABLE_SECTIONS = [
    "2.4", "2.10",                          # Base
    "3.3", "3.7", "3.8", "3.9", "3.12", "3.13",  # Management
    "4.2",                                   # Logging
    "5.6", "5.7", "5.8", "5.9", "5.10",      # Network
    "7.6", "7.21", "7.22", "7.24", "7.26", "7.27"  # Virtual Machine
]

from checks import (
    # Base checks (Section 2)
    check_2_4_for_host, fix_2_4_for_host,
    check_2_10_for_host, fix_2_10_for_host,
    # Management checks (Section 3)
    check_3_3_for_host, fix_3_3_for_host,
    check_3_7_for_host, fix_3_7_for_host,
    check_3_8_for_host, fix_3_8_for_host,
    check_3_9_for_host, fix_3_9_for_host,
    check_3_12_for_host, fix_3_12_for_host,
    check_3_13_for_host, fix_3_13_for_host,
    # Logging checks (Section 4)
    check_4_2_for_host, fix_4_2_for_host,
    # Network checks (Section 5)
    check_5_6_for_host, fix_5_6_for_host,
    check_5_7_for_host, fix_5_7_for_host,
    check_5_8_for_host, fix_5_8_for_host,
    check_5_9_and_5_10_for_host, fix_5_9_and_5_10_for_host,
    # Virtual Machine checks (Section 7)
    check_7_6_for_host, fix_7_6_for_host,
    check_7_21_for_host, fix_7_21_for_host,
    check_7_22_for_host, fix_7_22_for_host,
    check_7_24_for_host, fix_7_24_for_host,
    check_7_26_for_host, fix_7_26_for_host,
    check_7_27_for_host, fix_7_27_for_host,
)


# Mapping từ section ID sang check function
CHECK_FUNCS = {
    "2.4": check_2_4_for_host,
    "2.10": check_2_10_for_host,
    "3.3": check_3_3_for_host,
    "3.7": check_3_7_for_host,
    "3.8": check_3_8_for_host,
    "3.9": check_3_9_for_host,
    "3.12": check_3_12_for_host,
    "3.13": check_3_13_for_host,
    "4.2": check_4_2_for_host,
    "5.6": check_5_6_for_host,
    "5.7": check_5_7_for_host,
    "5.8": check_5_8_for_host,
    "5.9": check_5_9_and_5_10_for_host,
    "5.10": check_5_9_and_5_10_for_host,
    "7.6": check_7_6_for_host,
    "7.21": check_7_21_for_host,
    "7.22": check_7_22_for_host,
    "7.24": check_7_24_for_host,
    "7.26": check_7_26_for_host,
    "7.27": check_7_27_for_host,
}

# Mapping từ section ID sang fix function
FIX_FUNCS = {
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
    "7.27": fix_7_27_for_host,
}

# Mapping từ section ID sang result key
RESULT_KEYS = {
    "2.4": "cis_2_4_ok",
    "2.10": "cis_2_10_ok",
    "3.3": "cis_3_3_ok",
    "3.7": "cis_3_7_ok",
    "3.8": "cis_3_8_ok",
    "3.9": "cis_3_9_ok",
    "3.12": "cis_3_12_ok",
    "3.13": "cis_3_13_ok",
    "4.2": "cis_4_2_ok",
    "5.6": "cis_5_6_ok",
    "5.7": "cis_5_7_ok",
    "5.8": "cis_5_8_ok",
    "5.9": "cis_5_9_and_5_10_ok",
    "5.10": "cis_5_9_and_5_10_ok",
    "7.6": "cis_7_6_ok",
    "7.21": "cis_7_21_ok",
    "7.22": "cis_7_22_ok",
    "7.24": "cis_7_24_ok",
    "7.26": "cis_7_26_ok",
    "7.27": "cis_7_27_ok",
}


def get_user_sections(available_sections):
    """Cho người dùng chọn các section cần kiểm tra."""
    print("\n" + "=" * 60)
    print("CÁC PHẦN KIỂM TRA KHẢ DỤNG:")
    print("=" * 60)
    print("\n[BASE - Phần 2]")
    print("  2.4  - Host image profile acceptance level")
    print("  2.10 - Mem.ShareForceSalting")
    print("\n[MANAGEMENT - Phần 3]")
    print("  3.3  - Disable Managed Object Browser (MOB)")
    print("  3.7  - DCUI timeout")
    print("  3.8  - ESXi Shell Interactive Timeout")
    print("  3.9  - ESXi Shell Timeout")
    print("  3.12 - Account Lock Failures")
    print("  3.13 - Account Unlock Time")
    print("\n[LOGGING - Phần 4]")
    print("  4.2  - Remote Syslog")
    print("\n[NETWORK - Phần 5]")
    print("  5.6  - Reject Forged Transmits")
    print("  5.7  - Reject MAC Address Changes")
    print("  5.8  - Reject Promiscuous Mode")
    print("  5.9  - VLAN Configuration (không dùng VLAN 1)")
    print("  5.10 - VLAN Configuration (không dùng VLAN 4095)")
    print("\n[VIRTUAL MACHINE - Phần 7]")
    print("  7.6  - RemoteDisplay.maxConnections")
    print("  7.21 - Disable disk shrinking")
    print("  7.22 - Disable disk wiping")
    print("  7.24 - Disable host info to guest")
    print("  7.26 - Log keepOld")
    print("  7.27 - Log rotateSize")
    print("=" * 60)
    
    print("\nChọn các phần kiểm tra (cách nhau bởi dấu phẩy/khoảng trắng)")
    print("Hoặc nhấn Enter để chọn tất cả:")
    choice_input = input(">> Nhập phần cần kiểm tra: ").strip()
    
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


def run_checks(hosts, sections_to_run):
    """Chạy kiểm tra trên tất cả các hosts."""
    all_results = {}
    
    for info in hosts:
        host = info["host"]
        all_results[host] = {}
        
        print(f"\n{'=' * 60}")
        print(f"KIỂM TRA HOST: {host}")
        print('=' * 60)
        
        for sec_id in sorted(sections_to_run, key=lambda x: [int(n) for n in x.split('.')]):
            if sec_id in CHECK_FUNCS:
                # Với 5.9 và 5.10, chúng dùng chung 1 function
                if sec_id == "5.10" and "5.9" in all_results[host]:
                    all_results[host]["5.10"] = all_results[host]["5.9"]
                    continue
                    
                res = CHECK_FUNCS[sec_id](host, info["username"], info["password"], key_path=info.get("key_path"))
                all_results[host][sec_id] = res
    
    return all_results


def display_summary(all_results):
    """Hiển thị tổng hợp kết quả kiểm tra."""
    print("\n\n" + "=" * 60)
    print("                   TỔNG HỢP KẾT QUẢ")
    print("=" * 60)
    
    failed_checks = []
    
    for host, sections in all_results.items():
        print(f"\nHOST: {host}")
        sorted_sections = sorted(sections.keys(), key=lambda x: [int(n) for n in x.split('.')])
        
        for sec_id in sorted_sections:
            data = sections[sec_id]
            result_key = RESULT_KEYS.get(sec_id)
            
            if result_key and result_key in data:
                is_ok = data[result_key]
                status_str = "ĐẠT" if is_ok else "KHÔNG ĐẠT"
                print(f"  - {sec_id}: {status_str}")
                
                if not is_ok:
                    failed_checks.append((host, sec_id))
    
    return failed_checks


def run_fixes(hosts, all_results, failed_checks, sections_to_fix):
    """Chạy sửa lỗi cho các mục không đạt."""
    print("\n>>> TIẾN HÀNH SỬA LỖI...\n")
    
    for host, sec_id in failed_checks:
        if sec_id in sections_to_fix:
            if sec_id in FIX_FUNCS:
                func = FIX_FUNCS[sec_id]
                creds = next((h for h in hosts if h["host"] == host), None)
                
                if creds:
                    try:
                        key_path = creds.get("key_path")
                        # Với các mục 7.x, truyền thêm danh sách failed_vms
                        if sec_id.startswith("7.") and host in all_results and sec_id in all_results[host]:
                            failed_vms = all_results[host][sec_id].get("detail", {}).get("failed_vms", None)
                            func(host, creds["username"], creds["password"], failed_vms=failed_vms, key_path=key_path)
                        else:
                            func(host, creds["username"], creds["password"], key_path=key_path)
                        print(f"   -> Đã gửi lệnh sửa cho {sec_id} trên {host}.")
                    except Exception as e:
                        print(f"   -> LỖI khi sửa {sec_id} trên {host}: {e}")
            else:
                print(f"[{host}] Mục {sec_id} chưa có script tự động sửa.")


def get_esxi_hosts():
    """Cho người dùng nhập thông tin các ESXi hosts."""
    print("\n" + "=" * 60)
    print("         CIS VMware ESXi 8 Benchmark Checker")
    print("=" * 60)
    
    hosts = []
    
    while True:
        print(f"\n--- Nhập thông tin ESXi Host #{len(hosts) + 1} ---")
        
        host_ip = input(">> Địa chỉ IP của ESXi host: ").strip()
        if not host_ip:
            if hosts:
                print("Không nhập IP. Kết thúc thêm host.")
                break
            else:
                print("Bạn phải nhập ít nhất một host!")
                continue
        
        username = input(">> Username (mặc định: root): ").strip()
        if not username:
            username = "root"
        
        # Chọn phương thức xác thực
        print("\nChọn phương thức xác thực:")
        print("  1. Password")
        print("  2. SSH Key")
        auth_choice = input(">> Lựa chọn (1/2, mặc định 1): ").strip()
        
        if auth_choice == "2":
            # Xác thực bằng SSH key
            default_key = "~/.ssh/id_rsa"
            key_path = input(f">> Đường dẫn SSH private key (mặc định: {default_key}): ").strip()
            if not key_path:
                key_path = default_key
            
            # Hỏi passphrase nếu key được mã hóa
            key_passphrase = getpass.getpass(">> Passphrase cho key (Enter nếu không có): ")
            if not key_passphrase:
                key_passphrase = None
            
            hosts.append({
                "host": host_ip,
                "username": username,
                "password": key_passphrase,  # Passphrase cho key (nếu có)
                "key_path": key_path
            })
        else:
            # Xác thực bằng password
            password = getpass.getpass(">> Password: ")
            if not password:
                print("Password không được để trống!")
                continue
            
            hosts.append({
                "host": host_ip,
                "username": username,
                "password": password,
                "key_path": None
            })
        
        print(f"✓ Đã thêm host: {host_ip}")
        
        add_more = input("\nThêm host khác? (y/n, mặc định n): ").strip().lower()
        if add_more != 'y':
            break
    
    return hosts


def main():
    """Entry point chính của chương trình."""
    # Cho người dùng nhập thông tin ESXi hosts
    ESXI_HOSTS = get_esxi_hosts()
    
    if not ESXI_HOSTS:
        print("Không có host nào được cấu hình. Thoát chương trình.")
        return
    
    # Cho người dùng chọn sections cần kiểm tra
    sections_to_run = get_user_sections(AVAILABLE_SECTIONS)
    
    print(f"\n>>> BẮT ĐẦU KIỂM TRA: {', '.join(sorted(sections_to_run))}\n")
    
    # Chạy kiểm tra
    all_results = run_checks(ESXI_HOSTS, sections_to_run)
    
    # Hiển thị tổng hợp
    failed_checks = display_summary(all_results)
    
    if not failed_checks:
        print("\n>>> TẤT CẢ CÁC MỤC KIỂM TRA ĐỀU ĐẠT! Không cần sửa lỗi.")
        return
    
    # Hỏi người dùng có muốn sửa lỗi không
    print("\n" + "=" * 60)
    ask_fix = input("Bạn có muốn sửa các mục KHÔNG ĐẠT không? (y/n): ").strip().lower()
    
    if ask_fix != 'y':
        print("Đã kết thúc chương trình. Không thực hiện sửa đổi.")
        return
    
    print("\nNhập các phần muốn sửa (ví dụ: 3.8, 3.9)")
    print("Hoặc nhấn Enter để sửa TẤT CẢ các lỗi tìm thấy:")
    fix_choice = input(">> Lựa chọn: ").strip()
    
    sections_to_fix = set()
    if not fix_choice:
        sections_to_fix = set([x[1] for x in failed_checks])
    else:
        choices = fix_choice.replace(",", " ").split()
        for c in choices:
            c = c.strip()
            if c in AVAILABLE_SECTIONS:
                sections_to_fix.add(c)
            else:
                print(f"Bỏ qua lựa chọn không hợp lệ: {c}")
    
    # Chạy sửa lỗi
    run_fixes(ESXI_HOSTS, all_results, failed_checks, sections_to_fix)
    
    print("\n>>> Đã hoàn tất quá trình sửa lỗi. Vui lòng chạy lại kiểm tra để xác nhận.")


if __name__ == "__main__":
    main()

