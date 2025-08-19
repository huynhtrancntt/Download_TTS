pyinstaller --noconsole --onefile --name "Download_TTS" ^
  --add-data "app;app" ^
  --add-data "images;images" ^
  --icon "images/icon.ico" ^
  main.py