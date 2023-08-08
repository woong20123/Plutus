pyinstaller --onefile --console ..\lion.py
cp dist\lion.exe ../lion.exe
rmdir /s /q build
rmdir /s /q dist
rm lion.spec