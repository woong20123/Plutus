
pyinstaller --onefile --console ..\real_one_minute.py
cp dist\real_one_minute.exe ../real_one_minute.exe
rmdir /s /q build
rmdir /s /q dist
rm real_one_minute.spec