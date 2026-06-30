Set shell = CreateObject("WScript.Shell")
shell.CurrentDirectory = "C:\Users\yuuma\Documents\Codex\2026-06-26\new-chat-3"
shell.Run "cmd /c ""cd /d C:\Users\yuuma\Documents\Codex\2026-06-26\new-chat-3 && C:\Python314\python.exe outputs\circlematch_db_app.py >> work\circlematch_process.log 2>&1""", 0, False
