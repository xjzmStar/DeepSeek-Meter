import io

files = [
    ('stable/win/src/app_win_stable.py', '2.2.2', '2.3.0'),
    ('stable/linux/src/app_linux_stable.py', '2.2.2', '2.3.0'),
    ('app/win/src/app_win_dev.py', '3.0.0-snapshots 2', '3.1.0-snapshots-1'),
    ('app/linux/src/app_linux_dev.py', '3.0.0-snapshots 2', '3.1.0-snapshots-1'),
]

for path, old, new in files:
    with io.open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    content = content.replace('APP_VERSION = "%s"' % old, 'APP_VERSION = "%s"' % new)
    with io.open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK: %s' % path)
