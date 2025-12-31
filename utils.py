"""
Hàm tiện ích dùng chung: SSH connection
"""

import paramiko
import os


def run_ssh_command(host, username, password=None, command="", port=22, timeout=10, key_path=None):
    """
    Chạy lệnh SSH và trả về stdout (str).
    
    Hỗ trợ 2 phương thức xác thực:
    - Password: Truyền password
    - SSH Key: Truyền key_path (đường dẫn đến private key)
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        if key_path:
            # Xác thực bằng SSH key
            key_path = os.path.expanduser(key_path)  # Hỗ trợ ~ trong đường dẫn
            
            # Thử load key với các định dạng khác nhau
            pkey = None
            key_types = [
                (paramiko.RSAKey, "RSA"),
                (paramiko.Ed25519Key, "Ed25519"),
                (paramiko.ECDSAKey, "ECDSA"),
            ]
            
            for key_class, key_name in key_types:
                try:
                    pkey = key_class.from_private_key_file(key_path, password=password)
                    break
                except paramiko.ssh_exception.SSHException:
                    continue
            
            if pkey is None:
                raise ValueError(f"Không thể đọc private key từ: {key_path}")
            
            client.connect(
                hostname=host,
                port=port,
                username=username,
                pkey=pkey,
                look_for_keys=False,
                allow_agent=False,
                timeout=timeout,
            )
        else:
            # Xác thực bằng password
            client.connect(
                hostname=host,
                port=port,
                username=username,
                password=password,
                look_for_keys=False,
                allow_agent=False,
                timeout=timeout,
            )
        
        stdin, stdout, stderr = client.exec_command(command)
        out = stdout.read().decode("utf-8", errors="ignore")
        err = stderr.read().decode("utf-8", errors="ignore")
        if err.strip():
            print(f"[{host}] CẢNH BÁO: stderr trả về:\n{err}")
        return out
    finally:
        client.close()

