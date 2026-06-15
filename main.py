"""
英语刷题系统 - 主入口（前后端分离版）
启动后端 API 服务后，再启动前端 GUI
"""
import sys
import os
import subprocess
import time
import signal
import atexit
import socket

# 确保能导入本地模块
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

_backend_process = None


def _start_backend():
    """启动 FastAPI 后端服务"""
    global _backend_process
    # 以模块方式启动 backend 包
    _backend_process = subprocess.Popen(
        [sys.executable, '-m', 'backend.server'],
        cwd=BASE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
    )
    # 等待后端就绪（最多等 10 秒）
    for _ in range(50):
        try:
            s = socket.create_connection(('127.0.0.1', 8765), timeout=0.3)
            s.close()
            print('[后端] API 服务已启动 (127.0.0.1:8765)')
            return True
        except (ConnectionRefusedError, OSError):
            time.sleep(0.2)
    print('[后端] 启动超时，请检查 backend/server.py 是否有误')
    return False


def _stop_backend():
    """关闭后端服务"""
    global _backend_process
    if _backend_process and _backend_process.poll() is None:
        if sys.platform == 'win32':
            _backend_process.kill()
        else:
            _backend_process.terminate()
        _backend_process.wait(timeout=3)
        print('[后端] 服务已关闭')


atexit.register(_stop_backend)


def main():
    if not _start_backend():
        import tkinter.messagebox as mb
        mb.showerror('启动失败', '后端 API 服务启动失败，请检查后端依赖是否安装')
        return

    from frontend.gui import main as gui_main
    gui_main()


if __name__ == '__main__':
    main()
