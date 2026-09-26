"""CertEditor 启动器（PyInstaller 入口，也可直接 `python CertEditor.py` 执行）。

程序本体在 src/certeditor/。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from certeditor.app import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
