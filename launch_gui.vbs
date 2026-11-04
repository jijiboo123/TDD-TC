Option Explicit
' 启动主页面：用 wscript 调起，python 窗口隐藏，只留 GUI
Dim fso, shell, base
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
base = fso.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = base

If shell.Run("cmd /c where python >nul 2>nul", 0, True) <> 0 Then
    MsgBox "未找到 python。请先安装 Python 3.11 或以上，安装时勾选 Add python.exe to PATH。", vbExclamation, "软件测试可视化"
    WScript.Quit 1
End If

shell.Run "python tester_gui.py", 0, False