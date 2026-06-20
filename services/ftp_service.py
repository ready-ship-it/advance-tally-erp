"""FTP / FTPS upload service."""
import os
from ftplib import FTP, FTP_TLS, error_perm
from config import Config


def upload_to_ftp(local_path: str) -> tuple[bool, str]:
    if not Config.FTP_HOST:
        return False, "FTP not configured (set FTP_HOST, FTP_USER, FTP_PASSWORD env vars)"
    if not os.path.exists(local_path):
        return False, f"Local file not found: {local_path}"
    try:
        ftp = FTP_TLS() if Config.FTP_USE_TLS else FTP()
        ftp.connect(Config.FTP_HOST, Config.FTP_PORT, timeout=30)
        ftp.login(Config.FTP_USER, Config.FTP_PASSWORD)
        if Config.FTP_USE_TLS:
            try: ftp.prot_p()
            except Exception: pass
        # Try changing into the remote dir (best-effort)
        remote_dir = Config.FTP_REMOTE_DIR or "/"
        try:
            ftp.cwd(remote_dir)
        except error_perm:
            for part in remote_dir.strip("/").split("/"):
                if not part: continue
                try: ftp.mkd(part)
                except error_perm: pass
                ftp.cwd(part)
        fname = os.path.basename(local_path)
        with open(local_path, "rb") as f:
            ftp.storbinary(f"STOR {fname}", f)
        ftp.quit()
        return True, f"Uploaded {fname} to ftp://{Config.FTP_HOST}{remote_dir}"
    except Exception as e:
        return False, f"FTP upload failed: {e}"
