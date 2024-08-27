#Создаётся база данных НИЧЕГО НЕ МЕНЯТЬ!

import sqlite3
import os
import traceback
from abc import ABC, abstractmethod
import psycopg2
import psycopg2.extras
import psycopg2.pool
import Toolbox

# from psycopg2.pool import ThreadedConnectionPool

# Блокируем выполнение, если в пуле подключений не осталось свободных подключений
from threading import Semaphore
from psycopg2.pool import ThreadedConnectionPool as _ThreadedConnectionPool
class ThreadedConnectionPool(_ThreadedConnectionPool):
    def __init__(self, minconn, maxconn, *args, **kwargs):
        self._semaphore = Semaphore(maxconn)
        super().__init__(minconn, maxconn, *args, **kwargs)

    def getconn(self, *args, **kwargs):
        self._semaphore.acquire() # Вот эта строка ждет, пока в семафоре появится свободный слот
        try:
            return super().getconn(*args, **kwargs)
        except:
            self._semaphore.release()
            raise

    def putconn(self, *args, **kwargs):
        try:
            super().putconn(*args, **kwargs)
        finally:
            self._semaphore.release()


DATABASE_CONNECTION = None
DATABASE_POSTGRESQL = False
DATABASE_SQLITE = False

def dict_factory(cursor, row):
    fields = [column[0].lower() for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}

def print_exception(message, e: Exception):
    Toolbox.LogError(str(message))
    Toolbox.LogError(str(e))
    Toolbox.LogError(str(traceback.format_exc()))

class SQLColumnType(ABC):
    def __init__(self, column_name: str, data_type: str):
        self.data_type = data_type
        self.column_name = column_name

    def __str__(self):
        return self.column_name + " " + self.data_type.upper()

    def __repr__(self):
        return self.column_name + " " + self.data_type.upper()


class Database(ABC):
    @abstractmethod
    def create_table(self, table_name: str, column_data: list, if_not_exists: bool = True):
        pass

    @abstractmethod
    def drop_table(self, table_name: str, if_exists: bool = True):
        pass

    @abstractmethod
    def create_index(self, table_name: str, column: str, if_not_exists: bool = True):
        pass

    @abstractmethod
    def drop_index(self, table_name: str, column: str, if_exists: bool = True):
        pass

    @abstractmethod
    def rename_table(self, table_name: str, new_name: str):
        pass

    @abstractmethod
    def add_column(self, table_name: str, column_data: SQLColumnType):
        pass

    @abstractmethod
    def rename_column(self, table_name: str, column_name: str, new_name: str):
        pass

    @abstractmethod
    def drop_column(self, table_name: str, column_name: str):
        pass

    @abstractmethod
    def insert(self, table_name: str, data: dict, returning: str = ""):
        pass

    @abstractmethod
    def select(self, table_name: str, columns, 
              condition: str = "", params: list = [],
              distinct: bool = False,
              order_by: str = "", limit_and_offset: tuple = ()) -> list:
        pass

    @abstractmethod
    def update(self, table_name: str, update_data: dict, condition: str = "", params: list = []):
        pass

    @abstractmethod
    def delete(self, table_name: str, condition: str = "", params: list = []):
        pass

    @abstractmethod
    def select_table_names(self) -> list:
        pass

    def execute(self, query: str, params: list = []):
        pass


class SQLiteColumnType(SQLColumnType):
    def __init__(self, column_name: str, data_type: str, primary_key: bool = False, autoincrement: bool = False,
                 unique: bool = False, not_null: bool = False, default = None):
        """
        Инициализирует тип столбца SQLite.
        @param column_name: Имя столбца
        @param data_type: Тип столбца
        @param primary_key: Первичный ключ
        @param autoincrement: Автоинкремент
        @param unique: Уникальный
        @param not_null: Не пустой
        @param default: Значение по умолчанию
        """
        super(SQLiteColumnType, self).__init__(column_name, data_type)
        self.primary_key = primary_key
        self.autoincrement = autoincrement
        self.unique = unique
        self.not_null = not_null
        self.default = default

    def __str__(self):
        """
        Строковое представление типа столбца SQLite
        :return: SQLite код для создания столбца
        """
        row_type_str_parts = [super(SQLiteColumnType, self).__str__()]
        if self.primary_key or self.autoincrement:
            row_type_str_parts.append("PRIMARY KEY")
        if self.autoincrement:
            row_type_str_parts.append("AUTOINCREMENT")
        if self.unique:
            row_type_str_parts.append("UNIQUE")
        if self.not_null:
            row_type_str_parts.append("NOT NULL")
        if self.default != None:
            row_type_str_parts.append("DEFAULT " + str(self.default))
        return " ".join(row_type_str_parts)


class PostgreSQLColumnType(SQLColumnType):
    def __init__(self, column_name: str, data_type: str, primary_key: bool = False, autoincrement: bool = False,
                 unique: bool = False, not_null: bool = False, default = None):
        """
        Инициализирует тип столбца PostgreSQL.

        :param column_name: Имя столбца
        :param data_type: Тип данных
        :param primary_key: Первичный ключ
        :param unique: Уникальный
        :param not_null: Не пустой
        :param default: Значение по умолчанию
        """
        if autoincrement:
            data_type = 'SERIAL'
        super(PostgreSQLColumnType, self).__init__(column_name, data_type)
        self.primary_key = primary_key
        self.unique = unique
        self.not_null = not_null
        self.default = default

    def __str__(self):
        """
        Строковое представление типа столбца PostgreSQL

        :return: PostgreSQL код для создания столбца
        """
        row_type_str_parts = [super(PostgreSQLColumnType, self).__str__()]
        if self.primary_key:
            row_type_str_parts.append("PRIMARY KEY")
        if self.unique:
            row_type_str_parts.append("UNIQUE")
        if self.not_null:
            row_type_str_parts.append("NOT NULL")
        if self.default != None:
            row_type_str_parts.append("DEFAULT " + str(self.default))
        return " ".join(row_type_str_parts)


class SQLiteDatabase(Database):
    def __init__(self, db_path: str):
        try:
            self.connection = sqlite3.connect(db_path)
        except Exception as e:
            print_exception("Can't connect to database " + db_path, e)

    def close(self):
      return self.connection.close()

    def execute(self, query: str, params: list = []):
        self.connection.row_factory = dict_factory;
        cursor = self.connection.cursor()
        query = query.replace('%s','?')
        cursor.execute(query, params)
        res = cursor.fetchall()
        cursor.close()
        self.connection.commit()
        return res

    def create_table(self, table_name: str, column_data: list, if_not_exists: bool = True):
        create_table_query = ["CREATE TABLE"]
        if if_not_exists:
            create_table_query.append("IF NOT EXISTS")
        create_table_query.append(table_name)
        create_table_query.append("(")
        for column in column_data[:-1]:
            create_table_query.append(str(column) + ", ")
        create_table_query.append(column_data[-1])
        create_table_query.append(");")
        cursor = self.connection.cursor()
        cursor.execute(" ".join(list(map(lambda x: str(x), create_table_query))))
        self.connection.commit()
        cursor.close()

    def drop_table(self, table_name: str, if_exists: bool = True):
        drop_table_query = ["DROP TABLE"]
        if if_exists:
            drop_table_query.append("IF EXISTS")
        drop_table_query.append(table_name + ";")
        cursor = self.connection.cursor()
        cursor.execute(" ".join(drop_table_query))
        self.connection.commit()
        cursor.close()

    def create_index(self, table_name: str, column: str, if_not_exists: bool = True):
        query = ["CREATE INDEX"]
        if if_not_exists:
            query.append("IF NOT EXISTS")
        query.append(table_name + "_" + column)
        query.append("ON")
        query.append(table_name)
        query.append("(")
        query.append(column)
        query.append(");")
        cursor = self.connection.cursor()
        cursor.execute(" ".join(query))
        self.connection.commit()
        cursor.close()

    def drop_index(self, table_name: str, column: str, if_exists: bool = True):
        query = ["DROP INDEX"]
        if if_exists:
            query.append("IF EXISTS")
        query.append(table_name + "_" + column)
        query.append(";")
        cursor = self.connection.cursor()
        cursor.execute(" ".join(query))
        self.connection.commit()
        cursor.close()

    def rename_table(self, table_name: str, new_name: str):
        rename_table_query = ["ALTER TABLE", table_name, "RENAME TO", new_name + ";"]
        cursor = self.connection.cursor()
        cursor.execute(" ".join(rename_table_query))
        self.connection.commit()
        cursor.close()

    def add_column(self, table_name: str, column_data: SQLColumnType):
        add_column_query = ["ALTER TABLE", table_name, "ADD COLUMN", str(column_data) + ";"]
        cursor = self.connection.cursor()
        cursor.execute(" ".join(add_column_query))
        self.connection.commit()
        cursor.close()

    def rename_column(self, table_name: str, column_name: str, new_name: str):
        rename_table_query = ["ALTER TABLE", table_name, "RENAME COLUMN", column_name, "TO", new_name + ";"]
        cursor = self.connection.cursor()
        cursor.execute(" ".join(rename_table_query))
        self.connection.commit()
        cursor.close()

    def drop_column(self, table_name: str, column_name: str):
        # Штатного удаления колонки в SQLite нет
        cursor = self.connection.cursor()
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        res_query = cursor.fetchall()[0][0]
        copy_table_query_list = []
        res_query_list = res_query.split("(", 1)
        copy_table_query_list.append(res_query_list[0].strip())
        data_part = res_query_list[1].strip()
        if data_part[-1] == ";":
            data_part = data_part[:-1]
        if data_part[-1] == ")":
            data_part = data_part[:-1]
        data_part_list = list(map(lambda x: x.strip(), data_part.split(",")))
        for i in range(len(data_part_list)):
            if data_part_list[i].startswith(column_name):
                del data_part_list[i]
                break
        copy_table_query_list.append("(")
        for i in range(len(data_part_list)):
            if i == len(data_part_list) - 1:
                copy_table_query_list.append(data_part_list[i])
            else:
                copy_table_query_list.append(data_part_list[i])
                copy_table_query_list.append(",")
        copy_table_query_list.append(");")
        copy_table_query = " ".join(copy_table_query_list)
        self.connection.row_factory = sqlite3.Row
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM " + table_name + ";")
        res = cursor.fetchall()
        cursor.close()
        self.drop_table(table_name)
        cursor = self.connection.cursor()
        cursor.execute(copy_table_query)
        cursor.close()
        for row in res:
            row_data = {}
            for col_name in row.keys():
                if col_name != column_name:
                    row_data[col_name] = row[col_name]
            self.insert(table_name, row_data)
        self.connection.row_factory = None

    def insert(self, table_name: str, data: dict, returning: str = ""):
        self.connection.row_factory = dict_factory
        insert_query = ["INSERT INTO", table_name, "("]
        for col_name in data.keys():
            insert_query.append(col_name + ', ')
        insert_query[-1] = insert_query[-1][:-2]
        insert_query.append(")")
        insert_query.append("VALUES(")
        questions = "?," * len(data.values())
        questions = questions[:-1]
        insert_query.append(questions)
        insert_query.append(")")
        if returning:
            insert_query.extend(["RETURNING", returning])
        insert_query.append(";")
        cursor = self.connection.cursor()
        cursor.execute(" ".join(insert_query), tuple(data.values()))
        if returning:
            res = cursor.fetchall()
        cursor.close()
        self.connection.commit()
        if returning:
            return res

    def select(self, table_name: str, columns = "*", 
                          condition: str = "", params: list = [], 
                          distinct: bool = False,
                          order_by: str = "", limit_and_offset: tuple = ()) -> list:
        self.connection.row_factory = dict_factory;
        params1 = []
        select_query = ["SELECT"]
        if distinct:
            select_query.append("DISTRICT")
        if isinstance(columns, str):
            select_query.append(columns)
        else:
            for i in range(len(columns)):
                if i == len(columns) - 1:
                    select_query.append(columns[i])
                else:
                    select_query.append(columns[i] + ",")
        select_query.append("FROM" + " " + table_name)
        if condition:
            select_query.extend(["WHERE", condition.replace('%s','?')])
            params1.extend(params)
        if order_by:
            select_query.extend(["ORDER BY", order_by])
        if limit_and_offset:
            select_query.extend(["LIMIT", str(limit_and_offset[0]), "OFFSET", str(limit_and_offset[1])])
        select_query.append(";")
        cursor = self.connection.cursor()
        cursor.execute(" ".join(select_query), params1)
        result = cursor.fetchall()
        cursor.close()
        self.connection.commit()
        return result

    def update(self, table_name: str, update_data: dict, condition: str = "", params: list = []):
        update_query = ["UPDATE", table_name, "SET"]
        params1 = []
        for col, val in update_data.items():
            update_query.extend([col, "= ?,"])
            params1.append(val)
        update_query[-1] = update_query[-1][:-1]
        if condition:
            update_query.extend(["WHERE", condition.replace('%s','?')])
            params1.extend(params)
        update_query.append(";")
        cursor = self.connection.cursor()
        cursor.execute(" ".join(update_query), params1)
        self.connection.commit()
        cursor.close()

    def delete(self, table_name: str, condition: str = "", params: list = []):
        delete_query = ["DELETE FROM", table_name]
        if condition:
            delete_query.extend(["WHERE", condition.replace('%s','?')])
        delete_query.append(";")
        cursor = self.connection.cursor()
        cursor.execute(" ".join(delete_query), params)
        self.connection.commit()
        cursor.close()

    def select_table_names(self) -> list:
        select_query = "SELECT name FROM sqlite_master WHERE type ='table' AND name NOT LIKE 'sqlite_%';"
        cursor = self.connection.cursor()
        cursor.execute(select_query)
        res = cursor.fetchall()
        cursor.close()
        return res

    def get_dump_script(self) -> str:
        dump_script_list = []
        for line in self.connection.iterdump():
            dump_script_list.append(line)
        return "\n".join(dump_script_list)


class PostgreSQLDataBase(Database):
    def __init__(self):
        self.connection = DATABASE_CONNECTION.getconn()

    def close(self):
        DATABASE_CONNECTION.putconn(self.connection)

    def execute(self, query: str, params: list = []):
        cursor = self.connection.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
        cursor.execute(query, params)
        res = False
        try:
            res = cursor.fetchall()
        except:
            pass
        cursor.close()
        self.connection.commit()
        if res:
            return res

    def create_table(self, table_name: str, column_data: list, if_not_exists: bool = True):
        create_table_query = ["CREATE TABLE"]
        if if_not_exists:
            create_table_query.append("IF NOT EXISTS")
        create_table_query.append(table_name)
        create_table_query.append("(")
        columns = ", ".join(list(map(lambda x: str(x), column_data)))
        create_table_query.append(columns)
        create_table_query.append(");")
        cursor = self.connection.cursor()
        cursor.execute(" ".join(create_table_query))
        self.connection.commit()
        cursor.close()

    def drop_table(self, table_name: str, if_exists: bool = True):
        drop_query = ["DROP TABLE"]
        if if_exists:
            drop_query.append("IF EXISTS")
        drop_query.append(table_name)
        drop_query.append(";")
        cursor = self.connection.cursor()
        cursor.execute(" ".join(drop_query))
        self.connection.commit()
        cursor.close()

    def create_index(self, table_name: str, column: str, if_not_exists: bool = True):
        query = ["CREATE INDEX"]
        if if_not_exists:
            query.append("IF NOT EXISTS")
        query.append(table_name + "_" + column)
        query.append("ON")
        query.append(table_name)
        query.append("(")
        query.append(column)
        query.append(");")
        cursor = self.connection.cursor()
        cursor.execute(" ".join(query))
        self.connection.commit()
        cursor.close()

    def drop_index(self, table_name: str, column: str, if_exists: bool = True):
        query = ["DROP INDEX"]
        if if_exists:
            query.append("IF EXISTS")
        query.append(table_name + "_" + column)
        query.append(";")
        cursor = self.connection.cursor()
        cursor.execute(" ".join(query))
        self.connection.commit()
        cursor.close()

    def rename_table(self, table_name: str, new_name: str):
        rename_query = f"ALTER TABLE {table_name} RENAME TO {new_name};"
        cursor = self.connection.cursor()
        cursor.execute(rename_query)
        self.connection.commit()
        cursor.close()

    def add_column(self, table_name: str, column_data: SQLColumnType):
        add_query = f"ALTER TABLE {table_name} ADD COLUMN {str(column_data)};"
        cursor = self.connection.cursor()
        cursor.execute(add_query)
        cursor.close()
        self.connection.commit()

    def rename_column(self, table_name: str, column_name: str, new_name: str):
        rename_query = f"ALTER TABLE {table_name} RENAME COLUMN {column_name} TO {new_name};"
        cursor = self.connection.cursor()
        cursor.execute(rename_query)
        cursor.close()
        self.connection.commit()

    def drop_column(self, table_name: str, column_name: str):
        drop_query = f"ALTER TABLE {table_name} DROP COLUMN {column_name};"
        cursor = self.connection.cursor()
        cursor.execute(drop_query)
        cursor.close()
        self.connection.commit()

    def insert(self, table_name: str, data: dict, returning: str = ""):
        insert_query = f"INSERT INTO {table_name} ({', '.join(data.keys())}) VALUES ({', '.join(['%s'] * len(data.values()))})"
        if returning:
            insert_query += " RETURNING " + returning
        insert_query += ";" 
        cursor = self.connection.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
        cursor.execute(insert_query, tuple(data.values()))
        self.connection.commit()
        if returning:
            res = cursor.fetchall()
        cursor.close()
        if returning:
            return res

    def select(self, table_name: str, columns = "*", 
                          condition: str = "", params: list = [],
                          distinct: bool = False,
                          order_by: str = "", limit_and_offset: tuple = ()) -> list:
        params1 = []
        select_query = ["SELECT"]
        if distinct:
            select_query.append("DISTRICT")
        if isinstance(columns, str):
            select_query.append(columns)
        else:
            for i in range(len(columns)):
                if i == len(columns) - 1:
                    select_query.append(columns[i])
                else:
                    select_query.append(columns[i] + ",")
        select_query.append("FROM" + " " + table_name)
        if condition:
            select_query.extend(["WHERE", condition])
            params1.extend(params)
        if order_by:
            select_query.extend(["ORDER BY", order_by])
        if limit_and_offset:
            select_query.extend(["LIMIT", str(limit_and_offset[0]), "OFFSET", str(limit_and_offset[1])])
        select_query.append(";")
        cursor = self.connection.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
        cursor.execute(" ".join(select_query), params1)
        result = cursor.fetchall()
        cursor.close()
        return result

    def update(self, table_name: str, update_data: dict, condition: str = "", params: list = []):
        params1 = []
        set_part = []
        for col, val in update_data.items():
            set_part.append(col + " = %s")
            params1.append(val)
        update_query = f"UPDATE {table_name} SET {', '.join(set_part)}"
        if condition:
          update_query += f" WHERE {condition}"
          params1.extend(params)
        update_query += ";"
        cursor = self.connection.cursor()
        cursor.execute(update_query, params1)
        cursor.close()
        self.connection.commit()

    def delete(self, table_name: str, condition: str = "", params: list = []):
        delete_query = f"DELETE FROM {table_name}"
        if condition:
          delete_query += f" WHERE {condition}"
        delete_query += ";"
        cursor = self.connection.cursor()
        cursor.execute(delete_query, params)
        cursor.close()
        self.connection.commit()

    def select_table_names(self) -> list:
            select_query = "SELECT table_name FROM information_schema.tables WHERE table_type='BASE TABLE' AND table_schema='public';"
            cursor = self.connection.cursor()
            cursor.execute(select_query)
            res = cursor.fetchall()
            cursor.close()
            return res


class MyDatabase(Database):
    def __init__(self, postgre: bool = False, sqlite: bool = False, sqlite_data: dict = {}):
        """
        Инициализирует объект базы данных

        :param postgre: Используется PostgreSQL
        :param sqlite: Используется SQLite
        :param postgre_data: Параметры соединения к Postgre
        :param sqlite_data: Параметры соединения к SQLite
        """
        try:
            if postgre:
                self.database = PostgreSQLDataBase()
            elif sqlite:
                self.database = SQLiteDatabase(sqlite_data['path'])
            self.sqlite = sqlite
            self.postgre = postgre
        except Exception as e:
            print_exception("Can't open DB connection", e)

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        #Exception handling here
        self.close()

    def close(self):
        """
        Закрыть БД
        """
        return self.database.close()

    def is_sqlite(self):
        """
        Используется ли SQLite

        :return: Используется ли SQLite
        """
        return self.sqlite

    def is_postgre(self):
        """
            Используется ли PostgreSQL

            :return: Используется ли PostgreSQL
        """
        return self.postgre

    def create_table(self, table_name: str, column_data: list, if_not_exists: bool = True):
        """
        Создать таблицу

        :param table_name: Имя таблицы
        :param column_data: Список с типами столбцов
        :param if_not_exists: Создать только если таблица не существует
        """
        self.database.create_table(table_name, column_data, if_not_exists=if_not_exists)

    def drop_table(self, table_name: str, if_exists: bool = True):
        """
        Удалить таблицу

        :param table_name: Имя таблицы
        :param if_exists: Удалить только если таблица существует
        """
        self.database.drop_table(table_name, if_exists=if_exists)

    def create_index(self, table_name: str, column: str, if_not_exists: bool = True):
        """
        Создать индекс

        :param table_name: Имя таблицы
        :param column: Столбец
        :param if_not_exists: Создать только если индекс не существует
        """
        self.database.create_index(table_name, column, if_not_exists=if_not_exists)

    def drop_index(self, table_name: str, column: str, if_exists: bool = True):
        """
        Удалить индекс

        :param table_name: Имя таблицы
        :param column: Столбец
        :param if_not_exists: Удалить только если индекс существует
        """
        self.database.drop_index(table_name, column, if_exists=if_exists)

    def rename_table(self, table_name: str, new_name: str):
        """
        Переименовать таблицу

        :param table_name: Имя таблицы
        :param new_name: Новое имя таблицы
        """
        self.database.rename_table(table_name, new_name)

    def add_column(self, table_name: str, column_data: SQLColumnType):
        """
        Добавить столбцев в таблицу

        :param table_name: Имя таблицы
        :param column_data: Тип столбца
        """
        self.database.add_column(table_name, column_data)

    def rename_column(self, table_name: str, column_name: str, new_name: str):
        """
        Переименовать столбец

        :param table_name: Имя таблицы
        :param column_name: Имя столбца
        :param new_name: Новое имя столбца
        """
        self.database.rename_column(table_name, column_name, new_name)

    def drop_column(self, table_name: str, column_name: str):
        """
        Удалить столбец

        :param table_name: Имя таблицы
        :param column_name: Имя столбца
        """
        self.database.drop_column(table_name, column_name)

    def insert(self, table_name: str, data: dict, returning: str = ""):
        """
        Добавить запись в таблицу

        :param table_name: имя таблицы
        :param data: словарь с данными
        :param returning: имя поля, значение которого нужно получить в результате (обычно, id)
        """
        return self.database.insert(table_name, data, returning)

    def select(self, table_name: str, columns = "*", 
                          condition: str = "", params: list = [],
                          distinct: bool = False,
                          order_by: str = "", limit_and_offset: tuple = ()) -> list:
        """
        Выбрать значения из таблицы

        :param table_name: имя таблицы
        :param columns: список имен столбцов (строка или список), "*" если нужны все столбцы
        :param condition: строка с условием выборки (placeholder для параметра "%s")
        :param params: параметры условия выборки 
        :param distinct: Без повторений
        :param order_by: Имя столбца, по которому нужно отсортировать полученные значения
        :param limit_and_offset: Кортеж из двух чисел: ограничения по количеству записей и сдвиг относительно начала
        :return: Список кортежей с выбранными записями
        """
        return self.database.select(table_name, columns, 
                                               condition=condition, params=params, 
                                               distinct=distinct,
                                               order_by=order_by, limit_and_offset=limit_and_offset)

    def update(self, table_name: str, update_data: dict, condition: str = "", params: list = []):
        """
        Изменить запись в таблице

        :param table_name: Имя таблицы
        :param update_data: Словарь с обновленными данными
        :param condition: условие обновления (placeholder для параметра "%s")
        :param params: параметры условия обновления 
        """
        self.database.update(table_name, update_data, condition, params)

    def delete(self, table_name: str, condition: str = "", params: list = []):
        """
        Удалить запись из таблицы

        :param table_name: Имя таблицы
        :param condition: Условие удаления (placeholder для параметра "%s")
        :param params: параметры условия удаления 
        """
        self.database.delete(table_name, condition, params)

    def execute(self, query: str, params: list = []):
        """
        Выполнить запрос

        :param query: Текст запроса (placeholder для параметра "%s")
        :param params: параметры запроса
        :return: Результат выполнения запроса
        """
        return self.database.execute(query, params)

    def select_table_names(self) -> list:
        """
        Получить список названий таблиц

        :return: Список названий всех таблиц базы данных
        """
        return self.database.select_table_names()
    def column(self, column_name: str, data_type: str, is_id: bool = False, autoincrement = False,
                 primary_key: bool = False, unique: bool = False, not_null: bool = False, default = None):
        """
        Инициализирует тип столбца для базы данных.

        :param column_name: Имя столбца
        :param data_type: Тип данных
        :param is_id: Является ли id
        :param autoincrement: Автоматический инкремент
        :param primary_key: Первичный ключ
        :param unique: Уникальный
        :param not_null: Не пустой
        :param default: Значение по умолчанию
        """
        if not self.is_postgre():
            if is_id:
                column = SQLiteColumnType(column_name, "INTEGER", primary_key=True, autoincrement=True)
            else:
                column = SQLiteColumnType(column_name, data_type, primary_key=primary_key, 
                                          unique=unique, default=default, autoincrement=autoincrement,
                                          not_null=not_null)
        else:
            if is_id:
                column = PostgreSQLColumnType(column_name, "SERIAL", primary_key=True)
            else:
                column = PostgreSQLColumnType(column_name, data_type, primary_key=primary_key, 
                                              unique=unique, default=default, autoincrement=autoincrement,
                                              not_null=not_null)
        return column



def open() -> MyDatabase:
    """
    Получение объекта базы данных в зависимости от указанного в конфиге

    :return: Объект базы данных
    """
    config = Toolbox.GetConfiguration()
    postgre_config = config.get("PostgreSQL", {})
    if postgre_config.get("EnableIndex", False):
        database = MyDatabase(postgre=True)
        return database
    else:
        sqlite_path = os.path.join(Toolbox.Path(), config.get("SQLitePath", "database.db"))
        database = MyDatabase(sqlite=True, sqlite_data={"path": sqlite_path})
        return database

def init():
    """
    Создание пула подключений к базе данных (при запуске сервера)
    """
    config = Toolbox.GetConfiguration()
    postgre_config = config.get("PostgreSQL", {})
    if postgre_config.get("Enabled", False):
        global DATABASE_CONNECTION, DATABASE_POSTGRESQL
        DATABASE_POSTGRESQL = True
        DATABASE_CONNECTION = ThreadedConnectionPool(1, 20, 
            host=postgre_config.get("Host", "localhost"),
            port=int(postgre_config.get("Port", 5432)),
            database=postgre_config.get("Database", "notcoin_bot"),
            user=postgre_config.get("Username", "notcoin_bot"),
            password=postgre_config.get("Password", "notcoin_bot"))

        if DATABASE_CONNECTION:
            Toolbox.LogInfo("Connection pool to PostgreSQL database opened")
        else:
            global DATABASE_SQLITE
            DATABASE_SQLITE = True
            Toolbox.LogError("Cannont create connection pool to PostgreSQL database")
    else:
        pass

def close():
    """
    Закрыте пула подключений к базе данных (при остановке сервера)
    """
    if DATABASE_POSTGRESQL:
        DATABASE_CONNECTION.closeall()
        Toolbox.LogInfo("Connection pool to PostgreSQL database closed")
    else:
        pass
