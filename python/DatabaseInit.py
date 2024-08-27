#В этом файле можно создавать таблицы, добавлять колонки в базе данных
#При каждом изменении необходимо увеличивать версию базы данных
#Методы базы данных можно посмотреть в описании класса Database в Database.py

import Toolbox
import Database

def init_database():
  """Инициация базы данных"""
  with Database.open() as db:

    # Создаем таблицу настроек, если её ещё нет
    db.create_table("options", [
      db.column("db_version", "INTEGER"),
    ])
    options = db.select("options", ["db_version"])
    if not options:
      db.insert("options", {"db_version":0})

    # Версия БД, сохраненная в настройках
    db_version = getDBVersion(db) 

    # При необходимости обновляем БД до актуальной версии
    version = 1
    if db_version < version:
      Toolbox.LogWarning("Updating DB to version " + str(version))
      db.create_table("users", [
        db.column("id", "TEXT", primary_key=True),
        db.column("name", "TEXT"),
        db.column("joined_at", "INTEGER"),
        db.column("chat_id", "TEXT")
      ])
      Toolbox.LogWarning("Updating DB to version " + str(version) + " complete")
      setDBVersion(version, db)
      
    version = 2
    if db_version < version:
      Toolbox.LogWarning("Updating DB to version " + str(version))
      db.add_column("users", db.column("first_name", "TEXT"))
      db.add_column("users", db.column("last_name", "TEXT"))
      db.add_column("users", db.column("username", "TEXT"))
      db.add_column("users", db.column("language_code", "TEXT"))
      db.add_column("users", db.column("user_id", "TEXT"))
      db.add_column("users", db.column("is_premium", "INTEGER"))
      db.add_column("users", db.column("is_bot", "INTEGER"))
      Toolbox.LogWarning("Updating DB to version " + str(version) + " complete")
      setDBVersion(version, db)
      
    version = 3
    if db_version < version:
      Toolbox.LogWarning("Updating DB to version " + str(version))
      db.add_column("users", db.column("role", "TEXT"))
      Toolbox.LogWarning("Updating DB to version " + str(version) + " complete")
      setDBVersion(version, db)
      
    version = 4
    if db_version < version:
      Toolbox.LogWarning("Updating DB to version " + str(version))
      db.add_column("users", db.column("subscriber", "INTEGER"))
      Toolbox.LogWarning("Updating DB to version " + str(version) + " complete")
      setDBVersion(version, db)
      
def getDBVersion(db):
  data = db.select("options", ["db_version"])
  return data[0]["db_version"]

def setDBVersion(db_version: int, db):
  db.update("options", {"db_version": db_version})
