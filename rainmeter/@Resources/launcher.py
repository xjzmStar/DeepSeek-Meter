"""Launcher - starts update_state.py with no window"""
import subprocess
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
update_script = os.path.join(script_dir, "update_state.py")
pythonw = r"C:\Users\xjzm\AppData\Local\Programs\Python\Python310\pythonw.exe"

# Launch with CREATE_NO_WINDOW flag
subprocess.Popen(
    [pythonw, update_script],
    creationflags=0x08000000,  # CREATE_NO_WINDOW
    cwd=script_dir,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)