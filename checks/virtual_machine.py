"""
CIS VMware ESXi 8 - Section 7: Virtual Machine Checks
- 7.6: RemoteDisplay.maxConnections = 1
- 7.21: isolation.tools.diskShrink.disable = TRUE
- 7.22: isolation.tools.diskWiper.disable = TRUE
- 7.24: tools.guestlib.enableHostInfo = FALSE
- 7.26: log.keepOld = 10
- 7.27: log.rotateSize = 1000000
"""

from utils import run_ssh_command

def parse_vms_list(output: str):
    """Parse 'vim-cmd vmsvc/getallvms' output."""
    vms = []
    lines = output.splitlines()
    data_lines = [line for line in lines if line.strip() and not line.strip().startswith("Vmid")]
    
    for line in data_lines:
        parts = line.split()
        if not parts:
            continue
        
        try:
            vmid = parts[0]
            int(vmid)
            
            path_start_idx = -1
            for i, p in enumerate(parts):
                if p.startswith("["):
                    path_start_idx = i
                    break
            
            if path_start_idx != -1:
                name = " ".join(parts[1:path_start_idx])
                line_rest = " ".join(parts[path_start_idx:])
                
                if ".vmx" in line_rest:
                    raw_path = line_rest.split(".vmx")[0] + ".vmx"
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

def check_vm_setting_in_file(host, username, password, file_path, setting_key, port=22, key_path=None):
    """Kiểm tra một setting trong file .vmx của VM."""
    cmd = f'grep "{setting_key}" "{file_path}"'
    output = run_ssh_command(host, username, password, cmd, port=port, key_path=key_path)
    
    val = None
    for line in output.splitlines():
        line = line.strip()
        if not line.startswith("#") and line.startswith(setting_key) and "=" in line:
            parts = line.split("=", 1)
            if len(parts) == 2:
                raw_val = parts[1].strip().replace('"', '')
                val = raw_val
                break
    return val

def _get_failed_vms_for_setting(host, username, password, setting_key, expected_value, port=22, case_insensitive=False, key_path=None):
    """Helper function để lấy danh sách VMs không đạt yêu cầu cho một setting."""
    out = run_ssh_command(host, username, password, "vim-cmd vmsvc/getallvms", port=port, key_path=key_path)
    vms = parse_vms_list(out)
    
    failed_vms = []
    for vm in vms:
        val = check_vm_setting_in_file(host, username, password, vm['path'], setting_key, port, key_path=key_path)
        if val is None:
            vm['current_value'] = None
            failed_vms.append(vm)
        else:
            compare_val = val.lower() if case_insensitive else val
            compare_expected = expected_value.lower() if case_insensitive else expected_value
            if compare_val != compare_expected:
                vm['current_value'] = val
                failed_vms.append(vm)
    
    return vms, failed_vms

def _select_vms_to_fix(host, failed_vms):
    """Helper function để người dùng chọn VMs cần sửa."""
    print(f"[{host}] Danh sách VM cần sửa:")
    for i, vm in enumerate(failed_vms):
        print(f"  {i+1}. {vm['name']}")
    
    print("\nChọn VM để sửa (nhập số thứ tự cách nhau bởi dấu phẩy, hoặc 'all' để sửa tất cả):")
    choice = input("Lựa chọn: ").strip()
    
    if choice.lower() == 'all':
        return failed_vms
    else:
        selected_vms = []
        indices = choice.replace(",", " ").split()
        for idx in indices:
            if idx.isdigit():
                i = int(idx) - 1
                if 0 <= i < len(failed_vms):
                    selected_vms.append(failed_vms[i])
        return selected_vms

def fix_vm_setting(host, username, password, vm, setting_key, setting_value, port=22, key_path=None):
    """Sửa một setting trong file .vmx của VM."""
    # Xóa setting cũ
    cmd_del = f'sed -i "/{setting_key}/d" "{vm["path"]}"'
    run_ssh_command(host, username, password, cmd_del, port=port, key_path=key_path)
    
    # Thêm setting mới
    cmd_add = f'echo \'{setting_key} = "{setting_value}"\' >> "{vm["path"]}"'
    run_ssh_command(host, username, password, cmd_add, port=port, key_path=key_path)
    
    # Reload VM config
    run_ssh_command(host, username, password, f"vim-cmd vmsvc/reload {vm['vmid']}", port=port, key_path=key_path)

# ==================== CIS 7.6 ====================

def check_7_6_for_host(host: str, username: str, password: str, port: int = 22, key_path: str = None) -> dict:
    """
    CIS 7.6: Kiểm tra RemoteDisplay.maxConnections
    Yêu cầu: giá trị phải là 1
    """
    print(f"\n=== Kiểm tra CIS 7.6 trên host {host} ===")
    out = run_ssh_command(host, username, password, "vim-cmd vmsvc/getallvms", port=port, key_path=key_path)
    vms = parse_vms_list(out)
    
    if not vms:
        print(f"[{host}] Không tìm thấy máy ảo nào.")
        return {"host": host, "cis_7_6_ok": True, "detail": {"vms": []}}

    failed_vms = []
    for vm in vms:
        val = check_vm_setting_in_file(host, username, password, vm['path'], "RemoteDisplay.maxConnections", port, key_path=key_path)
        if val is None:
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
    print(f"[{host}] KẾT LUẬN CIS 7.6: {'ĐẠT' if ok else 'KHÔNG ĐẠT'}")
    
    return {"host": host, "cis_7_6_ok": ok, "detail": {"failed_vms": failed_vms}}


def fix_7_6_for_host(host, username, password, port=22, failed_vms=None, key_path=None):
    """Sửa lỗi CIS 7.6: Set RemoteDisplay.maxConnections = 1."""
    print(f"[{host}] Đang sửa lỗi CIS 7.6...")
    
    if failed_vms is None:
        _, failed_vms = _get_failed_vms_for_setting(host, username, password, "RemoteDisplay.maxConnections", "1", port, key_path=key_path)
    
    if not failed_vms:
        print(f"[{host}] Không có VM nào cần sửa lỗi CIS 7.6.")
        return True

    selected_vms = _select_vms_to_fix(host, failed_vms)
    
    if not selected_vms:
        print("Không có VM nào được chọn.")
        return False
        
    for vm in selected_vms:
        print(f"   -> Đang sửa VM: {vm['name']}...")
        fix_vm_setting(host, username, password, vm, "RemoteDisplay.maxConnections", "1", port, key_path=key_path)
        
    return True


# ==================== CIS 7.21 ====================

def check_7_21_for_host(host: str, username: str, password: str, port: int = 22, key_path: str = None) -> dict:
    """
    CIS 7.21: Kiểm tra isolation.tools.diskShrink.disable
    Yêu cầu: giá trị phải là TRUE
    """
    print(f"\n=== Kiểm tra CIS 7.21 trên host {host} ===")
    out = run_ssh_command(host, username, password, "vim-cmd vmsvc/getallvms", port=port, key_path=key_path)
    vms = parse_vms_list(out)
    
    if not vms:
        print(f"[{host}] Không tìm thấy máy ảo nào.")
        return {"host": host, "cis_7_21_ok": True, "detail": {"vms": []}}

    failed_vms = []
    for vm in vms:
        val = check_vm_setting_in_file(host, username, password, vm['path'], "isolation.tools.diskShrink.disable", port, key_path=key_path)
        if val is None:
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
    print(f"[{host}] KẾT LUẬN CIS 7.21: {'ĐẠT' if ok else 'KHÔNG ĐẠT'}")
    
    return {"host": host, "cis_7_21_ok": ok, "detail": {"failed_vms": failed_vms}}


def fix_7_21_for_host(host, username, password, port=22, failed_vms=None, key_path=None):
    """Sửa lỗi CIS 7.21: Set isolation.tools.diskShrink.disable = TRUE."""
    print(f"[{host}] Đang sửa lỗi CIS 7.21...")
    
    if failed_vms is None:
        _, failed_vms = _get_failed_vms_for_setting(host, username, password, "isolation.tools.diskShrink.disable", "true", port, case_insensitive=True, key_path=key_path)
    
    if not failed_vms:
        print(f"[{host}] Không có VM nào cần sửa lỗi CIS 7.21.")
        return True

    selected_vms = _select_vms_to_fix(host, failed_vms)
    
    if not selected_vms:
        print("Không có VM nào được chọn.")
        return False
        
    for vm in selected_vms:
        print(f"   -> Đang sửa VM: {vm['name']}...")
        fix_vm_setting(host, username, password, vm, "isolation.tools.diskShrink.disable", "TRUE", port, key_path=key_path)
        
    return True


# ==================== CIS 7.22 ====================

def check_7_22_for_host(host: str, username: str, password: str, port: int = 22, key_path: str = None) -> dict:
    """
    CIS 7.22: Kiểm tra isolation.tools.diskWiper.disable
    Yêu cầu: giá trị phải là TRUE
    """
    print(f"\n=== Kiểm tra CIS 7.22 trên host {host} ===")
    out = run_ssh_command(host, username, password, "vim-cmd vmsvc/getallvms", port=port, key_path=key_path)
    vms = parse_vms_list(out)
    
    if not vms:
        print(f"[{host}] Không tìm thấy máy ảo nào.")
        return {"host": host, "cis_7_22_ok": True, "detail": {"vms": []}}

    failed_vms = []
    for vm in vms:
        val = check_vm_setting_in_file(host, username, password, vm['path'], "isolation.tools.diskWiper.disable", port, key_path=key_path)
        if val is None:
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
    print(f"[{host}] KẾT LUẬN CIS 7.22: {'ĐẠT' if ok else 'KHÔNG ĐẠT'}")
    
    return {"host": host, "cis_7_22_ok": ok, "detail": {"failed_vms": failed_vms}}


def fix_7_22_for_host(host, username, password, port=22, failed_vms=None, key_path=None):
    """Sửa lỗi CIS 7.22: Set isolation.tools.diskWiper.disable = TRUE."""
    print(f"[{host}] Đang sửa lỗi CIS 7.22...")
    
    if failed_vms is None:
        _, failed_vms = _get_failed_vms_for_setting(host, username, password, "isolation.tools.diskWiper.disable", "true", port, case_insensitive=True, key_path=key_path)
    
    if not failed_vms:
        print(f"[{host}] Không có VM nào cần sửa lỗi CIS 7.22.")
        return True

    selected_vms = _select_vms_to_fix(host, failed_vms)
    
    if not selected_vms:
        print("Không có VM nào được chọn.")
        return False
        
    for vm in selected_vms:
        print(f"   -> Đang sửa VM: {vm['name']}...")
        fix_vm_setting(host, username, password, vm, "isolation.tools.diskWiper.disable", "TRUE", port, key_path=key_path)
        
    return True


# ==================== CIS 7.24 ====================

def check_7_24_for_host(host: str, username: str, password: str, port: int = 22, key_path: str = None) -> dict:
    """
    CIS 7.24: Kiểm tra tools.guestlib.enableHostInfo
    Yêu cầu: giá trị phải là FALSE
    """
    print(f"\n=== Kiểm tra CIS 7.24 trên host {host} ===")
    out = run_ssh_command(host, username, password, "vim-cmd vmsvc/getallvms", port=port, key_path=key_path)
    vms = parse_vms_list(out)
    
    if not vms:
        print(f"[{host}] Không tìm thấy máy ảo nào.")
        return {"host": host, "cis_7_24_ok": True, "detail": {"vms": []}}

    failed_vms = []
    for vm in vms:
        val = check_vm_setting_in_file(host, username, password, vm['path'], "tools.guestlib.enableHostInfo", port, key_path=key_path)
        if val is None:
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
    print(f"[{host}] KẾT LUẬN CIS 7.24: {'ĐẠT' if ok else 'KHÔNG ĐẠT'}")
    
    return {"host": host, "cis_7_24_ok": ok, "detail": {"failed_vms": failed_vms}}


def fix_7_24_for_host(host, username, password, port=22, failed_vms=None, key_path=None):
    """Sửa lỗi CIS 7.24: Set tools.guestlib.enableHostInfo = FALSE."""
    print(f"[{host}] Đang sửa lỗi CIS 7.24...")
    
    if failed_vms is None:
        _, failed_vms = _get_failed_vms_for_setting(host, username, password, "tools.guestlib.enableHostInfo", "false", port, case_insensitive=True, key_path=key_path)
    
    if not failed_vms:
        print(f"[{host}] Không có VM nào cần sửa lỗi CIS 7.24.")
        return True

    selected_vms = _select_vms_to_fix(host, failed_vms)
    
    if not selected_vms:
        print("Không có VM nào được chọn.")
        return False
        
    for vm in selected_vms:
        print(f"   -> Đang sửa VM: {vm['name']}...")
        fix_vm_setting(host, username, password, vm, "tools.guestlib.enableHostInfo", "FALSE", port, key_path=key_path)
        
    return True


# ==================== CIS 7.26 ====================

VM_LOG_KEEP_OLD = "10"

def check_7_26_for_host(host: str, username: str, password: str, port: int = 22, key_path: str = None) -> dict:
    """
    CIS 7.26: Kiểm tra log.keepOld
    Yêu cầu: giá trị phải là 10
    """
    print(f"\n=== Kiểm tra CIS 7.26 trên host {host} ===")
    out = run_ssh_command(host, username, password, "vim-cmd vmsvc/getallvms", port=port, key_path=key_path)
    vms = parse_vms_list(out)
    
    if not vms:
        print(f"[{host}] Không tìm thấy máy ảo nào.")
        return {"host": host, "cis_7_26_ok": True, "detail": {"vms": []}}

    failed_vms = []
    for vm in vms:
        val = check_vm_setting_in_file(host, username, password, vm['path'], "log.keepOld", port, key_path=key_path)
        if val is None:
            print(f"  - {vm['name']}: Không có tham số -> KHÔNG ĐẠT (cần thêm)")
            vm['current_value'] = None
            failed_vms.append(vm)
        elif val == VM_LOG_KEEP_OLD:
            print(f"  - {vm['name']}: log.keepOld = {val} -> ĐẠT")
        else:
            print(f"  - {vm['name']}: log.keepOld = {val} -> KHÔNG ĐẠT")
            vm['current_value'] = val
            failed_vms.append(vm)
            
    ok = (len(failed_vms) == 0)
    print(f"[{host}] KẾT LUẬN CIS 7.26: {'ĐẠT' if ok else 'KHÔNG ĐẠT'}")
    
    return {"host": host, "cis_7_26_ok": ok, "detail": {"failed_vms": failed_vms}}


def fix_7_26_for_host(host, username, password, port=22, failed_vms=None, key_path=None):
    """Sửa lỗi CIS 7.26: Set log.keepOld = 10."""
    print(f"[{host}] Đang sửa lỗi CIS 7.26...")
    
    if failed_vms is None:
        _, failed_vms = _get_failed_vms_for_setting(host, username, password, "log.keepOld", VM_LOG_KEEP_OLD, port, key_path=key_path)
    
    if not failed_vms:
        print(f"[{host}] Không có VM nào cần sửa lỗi CIS 7.26.")
        return True

    selected_vms = _select_vms_to_fix(host, failed_vms)
    
    if not selected_vms:
        print("Không có VM nào được chọn.")
        return False
        
    for vm in selected_vms:
        print(f"   -> Đang sửa VM: {vm['name']}...")
        fix_vm_setting(host, username, password, vm, "log.keepOld", VM_LOG_KEEP_OLD, port, key_path=key_path)
        
    return True


# ==================== CIS 7.27 ====================

VM_LOG_ROTATE_SIZE = "1000000"

def check_7_27_for_host(host: str, username: str, password: str, port: int = 22, key_path: str = None) -> dict:
    """
    CIS 7.27: Kiểm tra log.rotateSize
    Yêu cầu: giá trị phải là 1000000
    """
    print(f"\n=== Kiểm tra CIS 7.27 trên host {host} ===")
    out = run_ssh_command(host, username, password, "vim-cmd vmsvc/getallvms", port=port, key_path=key_path)
    vms = parse_vms_list(out)
    
    if not vms:
        print(f"[{host}] Không tìm thấy máy ảo nào.")
        return {"host": host, "cis_7_27_ok": True, "detail": {"vms": []}}

    failed_vms = []
    for vm in vms:
        val = check_vm_setting_in_file(host, username, password, vm['path'], "log.rotateSize", port, key_path=key_path)
        if val is None:
            print(f"  - {vm['name']}: Không có tham số -> KHÔNG ĐẠT (cần thêm)")
            vm['current_value'] = None
            failed_vms.append(vm)
        elif val == VM_LOG_ROTATE_SIZE:
            print(f"  - {vm['name']}: log.rotateSize = {val} -> ĐẠT")
        else:
            print(f"  - {vm['name']}: log.rotateSize = {val} -> KHÔNG ĐẠT")
            vm['current_value'] = val
            failed_vms.append(vm)
            
    ok = (len(failed_vms) == 0)
    print(f"[{host}] KẾT LUẬN CIS 7.27: {'ĐẠT' if ok else 'KHÔNG ĐẠT'}")
    
    return {"host": host, "cis_7_27_ok": ok, "detail": {"failed_vms": failed_vms}}


def fix_7_27_for_host(host, username, password, port=22, failed_vms=None, key_path=None):
    """Sửa lỗi CIS 7.27: Set log.rotateSize = 1000000."""
    print(f"[{host}] Đang sửa lỗi CIS 7.27...")
    
    if failed_vms is None:
        _, failed_vms = _get_failed_vms_for_setting(host, username, password, "log.rotateSize", VM_LOG_ROTATE_SIZE, port, key_path=key_path)
    
    if not failed_vms:
        print(f"[{host}] Không có VM nào cần sửa lỗi CIS 7.27.")
        return True

    selected_vms = _select_vms_to_fix(host, failed_vms)
    
    if not selected_vms:
        print("Không có VM nào được chọn.")
        return False
        
    for vm in selected_vms:
        print(f"   -> Đang sửa VM: {vm['name']}...")
        fix_vm_setting(host, username, password, vm, "log.rotateSize", VM_LOG_ROTATE_SIZE, port, key_path=key_path)
        
    return True
