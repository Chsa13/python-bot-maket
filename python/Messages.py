#В этом файле нужно создавать макеты сообщения для бота
#Можно изучить примеры ниже



import Toolbox
import Telegram
from telebot import types
import requests
def Subscribe(bot, message):
  #получаем пользователя из БД
  user = Telegram.getUser(chat_id=message.chat.id)
  #создаём кнопки под сообщением
  markup = types.InlineKeyboardMarkup()
  #здесь есть пример использования функции перевода текста
  button1 = types.InlineKeyboardButton(Toolbox.lang("Check subscripion", user["language_code"]), callback_data="check-subscribe")
  markup.add(button1)
  bot.send_message(message.chat.id, Toolbox.lang("Subscribe to channel", user["language_code"]), parse_mode="HTML", disable_web_page_preview=True, reply_markup=markup)

def SubscribeSucces(bot, message):
  #получаем пользователя из БД
  user = Telegram.getUser(chat_id=message.chat.id)
  #удаляем клавиатуру
  markup = types.ReplyKeyboardRemove()
  bot.send_message(message.chat.id, Toolbox.lang("Subscribe success", user["language_code"]), parse_mode="HTML", disable_web_page_preview=True, reply_markup=markup)

def Welcome(bot, message):
  #создаём кнопки под сообщением
  markup = types.InlineKeyboardMarkup()
  button1 = types.InlineKeyboardButton(Toolbox.lang("GO", message.from_user.language_code), callback_data="subscribe")
  markup.add(button1)
  bot.send_message(message.chat.id, Toolbox.lang("Welcome", message.from_user.language_code).format(message.from_user), parse_mode="HTML", disable_web_page_preview=True, reply_markup=markup)
  
def SendAllMsg(bot,user="", msg=""):
  try:
    if user:
      language_code = user["language_code"]
      chat_id = user["chat_id"]
    markup = types.InlineKeyboardMarkup()
    #здесь есть пример использования функции перевода текста
    button1 = types.InlineKeyboardButton(Toolbox.lang("START WITH TASKS", language_code), url="https://t.me/")
    markup.add(button1)
    bot.send_message(chat_id, msg, parse_mode="HTML", reply_markup = markup)

  except Exception as e:
    #отправляем в лог ошибки
    Toolbox.LogError('Error: ' + str(e))
