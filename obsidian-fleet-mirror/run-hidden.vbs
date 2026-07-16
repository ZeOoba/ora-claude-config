' run-hidden.vbs - launches write-fleet.ps1 with no visible window.
' Used by the Windows Task Scheduler job "ClaudeFleetMirror" so nothing flashes on screen.
Set sh = CreateObject("WScript.Shell")
sh.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -File ""C:\Users\Owner\.claude\obsidian-fleet-mirror\write-fleet.ps1""", 0, False
