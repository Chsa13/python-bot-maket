#В этом файле можно хранить разные полезные функции


import json
import os
import datetime
from functools import lru_cache

def Path():
  import pathlib
  return pathlib.Path(__file__).parent.resolve()

@lru_cache(maxsize=4096) # Кешируем результат
def GetConfiguration():
  with open(os.path.join(Path(), 'config.json'), 'r') as f:
    conf = f.read()
  return json.loads(conf)

def Log(t, prefix='E'):
  t2 = prefix + ' [' + datetime.datetime.now().strftime("%Y.%m.%d %H:%M:%S.%f") + '] ' + t
  with open(os.path.join(Path(), 'log.txt'), 'a') as f:
    f.write('\n' + t2)
  print(t2)

def LogError(t):
  Log(t, 'E')

def LogWarning(t):
  Log(t, 'W')

def LogInfo(t):
  return
  Log(t, 'I')

def GetLogs():
  with open(os.path.join(Path(), "log.txt"), "r") as f:
    lines = f.readlines()
    lines2 = lines[-10:]
  return "".join(lines2)

@lru_cache(maxsize=4096) # Кешируем результат
def LoadLangDict(lang):
  with open(os.path.join(Path(), 'lang', lang + ".json"), 'r', encoding="utf-8") as f:
    conf = f.read()
  return json.loads(conf) 

@lru_cache(maxsize=4096) # Кешируем результат
def lang(term, lang = "en"):
  if not term: return 
  langs = GetConfiguration().get("AvaliableLanguages", ["en"])
  if not lang in langs: lang = langs[0] 
  langDict = LoadLangDict(lang)
  # Если найден term в словаре, то возвращает перевод, иначе заменяет все шаблоны в term на перевод. Шаблон имеет вид: ':term:'
  if langDict.get(term) != None:
    return langDict[term]
  else:
    for key in langDict:
      term = term.replace(':' + key + ':', langDict[key])
    return term