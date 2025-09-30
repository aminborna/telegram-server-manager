import paramiko
import socket

SSH_CONNECT_TIMEOUT = 10.0  # ثانیه

def run_ssh_command(host: str, port: int, username: str, password: str, command: str, key_path: str = None, timeout: float = SSH_CONNECT_TIMEOUT) -> str:
    """
    Connects to host and runs command, returns combined stdout+stderr as str.
    If key_path provided, uses key-based auth; otherwise uses password.
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        if key_path:
            pkey = None
            try:
                pkey = paramiko.RSAKey.from_private_key_file(key_path)
            except Exception:
                # try ed25519
                try:
                    pkey = paramiko.Ed25519Key.from_private_key_file(key_path)
                except Exception:
                    pkey = None
            client.connect(hostname=host, port=int(port), username=username, pkey=pkey, timeout=timeout, banner_timeout=timeout, auth_timeout=timeout)
        else:
            client.connect(hostname=host, port=int(port), username=username, password=password, timeout=timeout, banner_timeout=timeout, auth_timeout=timeout)

        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        out = stdout.read().decode(errors="ignore")
        err = stderr.read().decode(errors="ignore")
        return (out + err).strip()
    except (paramiko.SSHException, socket.timeout, OSError) as e:
        return f"❌ SSH error: {e}"
    finally:
        try:
            client.close()
        except Exception:
            pass