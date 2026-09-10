import tkinter as _tk
import os

root = _tk.Tk()
root.withdraw()

logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src', 'app_logo.png')
print(f'Loading: {logo_path}')
print(f'Exists: {os.path.exists(logo_path)}')
print(f'Size: {os.path.getsize(logo_path)} bytes')

try:
    img = _tk.PhotoImage(file=logo_path)
    print(f'PhotoImage OK: {img.width()}x{img.height()}')
except Exception as e:
    print(f'PhotoImage FAILED: {e}')

root.destroy()
