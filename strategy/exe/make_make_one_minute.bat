pyinstaller --onefile --console ..\make_one_minute.py
cp dist\make_one_minute.exe ../make_one_minute.exe
rmdir /s /q build
rmdir /s /q dist
rm make_one_minute.spec