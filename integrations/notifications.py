import sys
import subprocess

def notify(title: str, message: str, sound: str = "Glass"):
    if sys.platform != "darwin":
        return

    clean_title = title.replace('"', '\\"')
    clean_msg = message.replace('"', '\\"')
    script = f'display notification "{clean_msg}" with title "{clean_title}" sound name "{sound}"'
    try:
        subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)
    except Exception:
        pass
