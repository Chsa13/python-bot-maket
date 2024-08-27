#Основной файл, где запускается бот и возможно другие процессы

from DatabaseInit import init_database
import Telegram
import Toolbox

init_database()
Toolbox.LogWarning('Start')
Telegram.Start()

