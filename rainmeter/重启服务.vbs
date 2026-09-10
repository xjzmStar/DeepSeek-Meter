Set WshShell = CreateObject("WScript.Shell")
' Kill existing
WshShell.Run "cmd /c taskkill /f /fi ""WINDOWTITLE eq python*"" >nul 2>&1", 0, True
WScript.Sleep 1000
' Start new
WshShell.CurrentDirectory = "E:\xjzm\Documents\Rainmeter\Skins\DeepSeek-Meter\@Resources"
WshShell.Run "py launcher.py", 0, False