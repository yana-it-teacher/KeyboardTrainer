@echo off
chcp 65001 > nul
echo ========================================================
echo   Збірка клавіатурного тренажера "Спритні пальчики" в EXE
echo ========================================================
echo.

echo 1. Перевірка Python та PyInstaller...
py -3.13 -m pip install pyinstaller pillow > nul 2>&1

echo 2. Генерація іконки застосунку...
py -3.13 -c "from PIL import Image, ImageDraw; img = Image.new('RGBA', (256, 256), (0, 0, 0, 0)); draw = ImageDraw.Draw(img); draw.rounded_rectangle([10, 10, 246, 246], radius=48, fill=(74, 144, 226), outline=(255, 255, 255), width=6); img.save('icon.ico', format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])"

echo 3. Компіляція автономного KeyboardTrainer.exe...
py -3.13 -m PyInstaller --noconsole --onefile --icon=icon.ico --name="KeyboardTrainer" main.py

echo.
echo ========================================================
echo   ГОТОВО!
echo   Автономний файл знаходиться у теці: dist\KeyboardTrainer.exe
echo   Цей файл можна копіювати на флешку та запускати на БУДЬ-ЯКОМУ іншому ПК!
echo ========================================================
pause
