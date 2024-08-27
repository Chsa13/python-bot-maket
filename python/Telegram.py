import Toolbox
import Telegram
import Messages
import json
import time
import uuid
import Database
import traceback
import threading
from functools import lru_cache
from telebot import types
import telebot
import logging
TELEGRAM_TOKEN = None

class TelegramExceptionHandler:
  def handle(self, e):
    if str(e).startswith('Request timeout'):
      Toolbox.LogWarning('Warning in Telegram: ' + str(e))
    elif str(e).startswith('A request to the Telegram API was unsuccessful'):
      Toolbox.LogWarning('Warning in Telegram: ' + str(e))
    else:
      Toolbox.LogError('Error in Telegram: ' + str(e) + "\n" + str(traceback.format_exc()))
    return True

def bot_init():
  #Функция создаёт бота
  import telebot
  import logging
  telebot.logger.setLevel(logging.ERROR) # Outputs debug messages to console.
  bot = telebot.TeleBot(token=TELEGRAM_TOKEN, exception_handler=TelegramExceptionHandler())
  return bot

@lru_cache(maxsize=4096) # Кешируем результат
def getUser(user_id = 0, chat_id=0):
  #Функция позволяет найте пользователя в базе дынных по user_id или chat_id
  #Здесь можно посмотреть пример обращения к базе данных для получения информации
  with Database.open() as db:
    if user_id: u = db.select("users", "*", condition="user_id=%s", params=[user_id])
    elif chat_id: u = db.select("users", "*", condition="chat_id=%s", params=[chat_id])
  if len(u):
    return u[0]
  else: return None
  
def IsSubscriber(bot, user_id):
  #Функция позволяет проверить подписку конкертного пользователя на канал
  #Работает только если бот является адиином канала
  #Здесь канала @stark_invest, можно заменить на любой другой, а лучше вынести это в config
  try : status = bot.get_chat_member("@stark_invest", user_id).status
  except: status = False
  if status == "member" or status == "administrator" or status == "creator" or status == "restricted": subscriber =  True
  else: subscriber = False
  with Database.open() as db:
        db.update("users", {"subscriber": 1 if subscriber else 0}, condition="user_id=%s", params=[user_id])
  return subscriber
  
def AreSubscribers(users):
  #Функция проверяет каждого пользователя из массива users на наличие подписки на канал
  #Возвращает обновлённый массив users с изменённым значением subscriber
  import telebot
  bot = telebot.TeleBot(token=TELEGRAM_TOKEN, exception_handler=TelegramExceptionHandler())
  for i in users:
    try : status = bot.get_chat_member("@stark_invest", i["user_id"]).status
    except: status = False
    if status == "member" or status == "administrator" or status == "creator" or status == "restricted": subscriber =  True
    else: subscriber = False
    i["subscriber"] = subscriber
    Toolbox.LogWarning(str(subscriber))
  bot.stop_bot()
  return users

def Start():
  #запускается бот
  conf = Toolbox.GetConfiguration()
  if not conf.get('TelegramBot', {}).get('Enabled'): return
  key = conf.get('TelegramBot').get("Apikey", "")
  if not key: return
  global TELEGRAM_TOKEN
  TELEGRAM_TOKEN = key
  def start_():
    bot = bot_init()
    
    #обработчик команды /start
    @bot.message_handler(commands=['start'])
    def send_welcome(message):
      try:
        #получаем необходимую инфу о пользователе, чтобы потом её сохранить в базу данных
        user = {
          "chat_id": message.chat.id,
          "user_id": message.from_user.id,
          "first_name": message.from_user.first_name,
          "last_name": message.from_user.last_name,
          "username": message.from_user.username,
          "language_code": message.from_user.language_code,
          "is_bot": 1 if message.from_user.is_bot else 0,
          "is_premium": 1 if message.from_user.is_premium else 0,
          "subscriber": 1 if IsSubscriber(bot, message.from_user.id) else 0
        }
        
        with Database.open() as db: #Пытаемся найте пользователя в базе данных, который отправл команду
          u = db.select("users", "*", condition="user_id=%s", params=[message.from_user.id])
        if len(u):
          #если нашли, то обновляем информация о нём
          with Database.open() as db:
            db.update("users", user, condition="user_id=%s", params=[user['user_id']])
        else:
          #если не нашли то довабляем пользователю уникальный идентификатор и время присоединения к боту
          user['id']= str(uuid.uuid4())
          user["joined_at"] = int(time.time())
          #сохраняем в базу данных нового пользвателя
          with Database.open() as db:
            db.insert("users", user)
        #отправляем сообщение
        Messages.Welcome(bot, message)
      except Exception as e:
        #записываем в лог ошибки
        Toolbox.LogError('Error Telegram.send_welcome: ' + str(e) + "\n" + str(traceback.format_exc()))
        return
    
    #обработчик callback сообщений, который отправляются при нажатии на кнопки под сообщениями
    @bot.callback_query_handler(func=lambda call: True)
    def callback_inline(call):
      if str(call.data) == "subscribe": #здесь обрабатывается нажатие на кнопку под приветственным сообщением
        #передаём боту, что мы получили сообщение
        bot.answer_callback_query(callback_query_id = call.id, text = "", show_alert = False)
        #ищем пользователся в базе данных
        user = getUser(chat_id=call.message.chat.id)
        #проверяем его подписку на канал
        subscriber = IsSubscriber(bot, user["user_id"])
        if not subscriber:
          #если не подписчик отправляем сообщение подпишись
          Messages.Subscribe(bot=bot, message=call.message)
        else:
          #если подписчик, то отправляем сообщение о успешной подписке
          Messages.SubscribeSucces(bot=bot, message=call.message)
      elif str(call.data) == "check-subscribe": #здесь обрабатывается нажатие на кнопку под сообщением подпишись
        #передаём боту, что мы получили сообщение
        bot.answer_callback_query(callback_query_id = call.id, text = "", show_alert = False)
        #ищем пользователся в базе данных
        user = getUser(chat_id=call.message.chat.id)
        #проверяем его подписку на канал
        subscriber = IsSubscriber(bot, user["user_id"])
        if not subscriber:
          #если не подписчик то мы меняем сообщение под которым нажали на кнопку на сообщение подпишись
          markup = types.InlineKeyboardMarkup()
          button1 = types.InlineKeyboardButton(Toolbox.lang("Check subscripion", user["language_code"]), callback_data="check-subscribe")
          markup.add(button1)
          bot.edit_message_text(Toolbox.lang("Subscribe to channel", user["language_code"]), call.message.chat.id, call.message.id, parse_mode="HTML", disable_web_page_preview=True, reply_markup=markup)
        else:
          #если нподписчик то мы меняем сообщение под которым нажали на кнопку на сообщение о успешной подписке
          bot.edit_message_text(Toolbox.lang("Subscribe success", user["language_code"]), call.message.chat.id, call.message.id, parse_mode="HTML", disable_web_page_preview=True)
      else: #в любом другом случае просто отвечаем на callback
        bot.send_message(bot, call.message.chat.id, str(call.data))
        bot.answer_callback_query(callback_query_id = call.id, text = "", show_alert = False)

    #обработчик команды /log
    @bot.message_handler(commands=['log'])
    #пользователю отправляются 5 последних записей в логах
    def send_log(message):
      #получаем пользователя из базы данных
      user = getUser(message.from_user.id)
      if user and user["role"] == "admin": # проверяем является ли он админом
        #отправляем логи
        bot.send_message(bot, message.chat.id, Toolbox.GetLogs())
    
    #обработчик команды /profile
    @bot.message_handler(commands=['profile'])
    #просто макет 
    def send_log(message):
      markup = types.InlineKeyboardMarkup()
      button1 = types.InlineKeyboardButton("Сайт Хабр", callback_data="start")
      markup.add(button1)
      bot.send_message(bot, message.chat.id, "Привет, {0.first_name}! Нажми на кнопку и перейди на сайт)".format(message.from_user), reply_markup=markup)
    Toolbox.LogWarning('Telegram starting')
    #запускаем бесконечный цикл прослушивания новых сообщений от пользователей
    bot.polling(none_stop=True, interval=0)
  #эта строчка нужна чтобы можно было создавать несколько бесконечных циклов параллельно
  #можно на подобии того как организивана команда Start в этом файле и её запуск в файле main.py создавть другие бесконечные параллельные друг другу циклы
  threading.Thread(target=start_).start()
  # если запускаешь на сервере как демон, то закоментируй прошлую строку и раскомметируй предыдущую
  # threading.Thread(target=start_, daemon=True).start()

#функия для отправки сообщений через бота
#нужна чтобы отправляеть сообщения например из других файлов, циклов и тд
def send(subscriptionCheck, user_id, *args, **kwargs):
  #subscriptionCheck это нужно ли проверять пользователя на наличие подписки на канал
  def send_(*args, **kwargs):
    Toolbox.LogInfo('Sending telegram message')
    import telebot
    import logging
    telebot.logger.setLevel(logging.ERROR) # Outputs debug messages to console.
    #создаём бота
    bot = telebot.TeleBot(token=TELEGRAM_TOKEN, exception_handler=TelegramExceptionHandler())
    if (not subscriptionCheck) or IsSubscriber(bot, user_id): bot.send_message(*args, **kwargs)
    #останавливаем бота
    bot.stop_bot()
    Toolbox.LogInfo('Sending telegram message complete')
  if not TELEGRAM_TOKEN: return False
  #опять можно посмотреть как организованы бесконечные параллельные циклы
  threading.Timer(0, function = send_, args=args, kwargs=kwargs).start()

#функция отправляет какой-то текст только админам
def NotifyAdmins(text):
  with Database.open() as db:
    users = db.select("users", "*", condition = "role = %s", params = ["admin"])
  for user in users:
    Telegram.send(False, user['user_id'], user['chat_id'], text)
    
def SendAll(text):
  #получаем из базы данных всех пользователей
  with Database.open() as db:
    users = db.select("users", "*")
  #проверяем их подписку на канал
  users = AreSubscribers(users)
  Toolbox.LogInfo('Sending telegram messages')
  telebot.logger.setLevel(logging.ERROR) # Outputs debug messages to console.
  #создаём бота
  bot = telebot.TeleBot(token=TELEGRAM_TOKEN, exception_handler=TelegramExceptionHandler())
  for i in users:
    #отсылаем сообщение всем подписчикам или админом
    if i["subscriber"] or i["role"] == "admin":Messages.SendAllMsg(bot = bot, user = i, msg = text)
  #останавливаем бота
  bot.stop_bot()
  Toolbox.LogInfo('Sending telegram messages complete')