# -*- coding: utf-8 -*-
import os
import time
import json
import random
import typing
import shutil
import sqlite3
import hashlib
import collections
from .datatype import DynamicObject, str2float, str2number, DynamicObjectError
from typing import Any, Optional, Union, List, Tuple, Sequence, Dict, Callable
from ..misc.settings import UiInputSetting, UiIntegerInput, UiDoubleInput

try:
    from pysqlcipher3 import dbapi2 as sqlcipher
except ImportError:
    import sqlite3 as sqlcipher

__all__ = ['SQLiteDatabase', 'SQLCipherDatabase', 'SQLiteUserPasswordDatabase', 'SQLiteDatabaseError',
           'SQLiteDatabaseCreator', 'SQLiteGeneralSettingsItem',
           'DBItemType', 'DBItemSearchAttr', 'DBTable', 'DBColumn',
           'SQLiteUIElementScheme', 'SQLiteUITableScheme', 'SQLiteUIScheme', 'sqlite_create_tables']


class SQLiteDatabaseError(Exception):
    pass


DBItemType = collections.namedtuple('DBItemType', 'int real text blob')(*'INTEGER REAL TEXT BLOB'.split())
DBItemSearchAttr = collections.namedtuple('DBItemSubtype', 'Normal Timestamp Enum Fuzzy')(*(0x1, 0x2, 0x4, 0x8))


class DBColumn(DynamicObject):
    _properties = {'name', 'type', 'attr', 'display', 'default_value', 'stretch', 'annotate', 'search_attr'}

    def __init__(self, **kwargs):
        kwargs.setdefault('attr', '')
        kwargs.setdefault('stretch', 0.0)
        kwargs.setdefault('display', True)
        kwargs.setdefault('default_value', None)
        kwargs.setdefault('annotate', kwargs.get('name'))
        kwargs.setdefault('search_attr', DBItemSearchAttr.Normal)
        super(DBColumn, self).__init__(**kwargs)

    def __repr__(self):
        return ' '.join([self.name, self.type, self.attr]).strip()

    def is_type(self, t: str) -> bool:
        return t.upper() == self.type.upper()

    def hasattr(self, attr: str) -> bool:
        return attr.upper() in self.attr.upper()

    def is_pk(self) -> bool:
        return self.hasattr('PRIMARY KEY')

    def is_int(self) -> bool:
        return self.is_type(DBItemType.int)

    def is_text(self) -> bool:
        return self.is_type(DBItemType.text)

    def is_real(self) -> bool:
        return self.is_type(DBItemType.real)

    def is_blob(self) -> bool:
        return self.is_type(DBItemType.blob)

    def is_unique(self) -> bool:
        return self.hasattr('UNIQUE')

    def is_autoinc(self) -> bool:
        return self.hasattr('AUTOINCREMENT')

    def get_default_value(self) -> typing.Any:
        if self.default_value is not None:
            return self.default_value

        return {
            DBItemType.int: 0,
            DBItemType.text: '',
            DBItemType.real: 0.0,
            DBItemType.blob: '""',
        }.get(self.type.upper(), '')


class DBTable:
    def __init__(self, name: str, scheme: typing.Sequence[DBColumn],
                 readonly: bool = False, init_records: typing.Sequence[typing.Dict[str, typing.Any]] = None):
        self.name = name
        self.scheme = scheme
        self.readonly = readonly
        self.init_records = init_records or list()

    @property
    def pk(self) -> str:
        try:
            return [x.name for x in self.scheme if x.is_pk()][0]
        except IndexError:
            return ''

    @property
    def is_autoincrement(self) -> bool:
        return any(x.is_autoinc() for x in self.scheme)

    def columns_name(self) -> typing.Tuple[str, ...]:
        return tuple([x.name for x in self.scheme if not x.is_autoinc()])

    def columns_annotation(self) -> typing.Tuple[str, ...]:
        return tuple([x.annotate for x in self.scheme if x.display])

    def columns_stretch(self) -> typing.Tuple[float, ...]:
        return tuple([x.stretch for x in self.scheme if x.display])

    def display_columns(self) -> typing.Tuple[str, ...]:
        return tuple([x.name for x in self.scheme if x.display])

    def default_values(self) -> typing.Dict[str, typing.Any]:
        return {x.name: x.get_default_value() for x in self.scheme if not x.is_autoinc()}

    def get_column_from_name(self, name: str) -> typing.Optional[DBColumn]:
        try:
            return [x for x in self.scheme if x.name == name][0]
        except IndexError:
            return None

    def get_column_annotate_from_name(self, name: str) -> str:
        try:
            return self.get_column_from_name(name).annotate
        except AttributeError:
            return ''

    def get_column_index_from_name(self, name: str) -> int:
        try:
            return self.scheme.index(self.get_column_from_name(name))
        except ValueError:
            return -1

    def get_enumeration_columns(self) -> typing.List[int]:
        return [i for i, c in enumerate(self.scheme) if c.search_attr & DBItemSearchAttr.Enum]

    def get_timestamp_columns(self) -> typing.List[int]:
        return [i for i, c in enumerate(self.scheme) if c.search_attr & DBItemSearchAttr.Timestamp]

    def get_fuzzy_columns(self) -> typing.List[int]:
        return [i for i, c in enumerate(self.scheme) if c.search_attr & DBItemSearchAttr.Fuzzy]

    def get_create_sentence(self) -> str:
        return f'CREATE TABLE {self.name} ({", ".join([str(x) for x in self.scheme])});'

    def get_placeholder_sentence(self) -> str:
        return self.get_inert_sentence(self.default_values())

    def get_inert_sentence(self, record: typing.Dict[str, typing.Any]) -> str:
        v = [f'"{record.get(x.name)}"' if x.is_text() else f'{record.get(x.name)}'
             for x in self.scheme if x.name in record and not x.is_autoinc()]
        return f'INSERT INTO {self.name} ({", ".join(self.columns_name())}) VALUES({", ".join(v)})'

    def get_update_sentence(self, record: typing.Dict[str, typing.Any], cond: str) -> str:
        v = [f'{x.name} = "{record.get(x.name)}"' if x.is_text() else f'{x.name} = {record.get(x.name)}'
             for x in self.scheme if x.name in record and not x.is_autoinc()]
        return f'UPDATE {self.name} SET {", ".join(v)} WHERE {cond}'


class SQLiteDatabase(object):
    SpcSequenceTBLName = 'sqlite_sequence'
    TYPE_INTEGER, TYPE_REAL, TYPE_TEXT, TYPE_BLOB = list(range(4))
    TBL_CID, TBL_NAME, TBL_TYPE, TBL_REQUIRED, TBL_DEF, TBL_PK = list(range(6))

    def __init__(self, db_path: str,
                 timeout: int = 20,
                 check_same_thread: bool = True,
                 conn: Optional[sqlite3.Connection] = None):

        if isinstance(conn, sqlite3.Connection):
            self._conn = conn
        else:
            if not os.path.isfile(db_path):
                raise IOError("{} do not exist".format(db_path))

            self._conn = sqlite3.connect(db_path, timeout=timeout, check_same_thread=check_same_thread)

        self._cursor = self._conn.cursor()

    @property
    def raw_cursor(self) -> sqlite3.Cursor:
        return self._cursor

    @property
    def raw_connect(self) -> sqlite3.Connection:
        return self._conn

    @staticmethod
    def conditionFormat(k: str, v: Any, t: Optional[int] = None) -> str:
        t = SQLiteDatabase.str2type(t) if isinstance(t, str) else SQLiteDatabase.detectDataType(v)
        return '{} = "{}"'.format(k, v) if t == SQLiteDatabase.TYPE_TEXT else '{} = {}'.format(k, v)

    @staticmethod
    def searchConditionFormat(k: str, v: Any, t: Optional[int] = None) -> str:
        t = SQLiteDatabase.str2type(t) if isinstance(t, str) else SQLiteDatabase.detectDataType(v)
        return '{} LIKE "%{}%"'.format(k, v) if t == SQLiteDatabase.TYPE_TEXT else '{} LIKE %{}%'.format(k, v)

    @staticmethod
    def globalSearchConditionFormat(k: str, v: Any, t: Optional[int] = None) -> str:
        t = SQLiteDatabase.str2type(t) if isinstance(t, str) else SQLiteDatabase.detectDataType(v)
        return '{} GLOB "*{}*"'.format(k, v) if t == SQLiteDatabase.TYPE_TEXT else '{} LIKE *{}*'.format(k, v)

    @staticmethod
    def detectDataType(data: Any) -> int:
        if isinstance(data, (int, bool)):
            return SQLiteDatabase.TYPE_INTEGER
        elif isinstance(data, str):
            return SQLiteDatabase.TYPE_TEXT
        elif isinstance(data, float):
            return SQLiteDatabase.TYPE_REAL
        else:
            return SQLiteDatabase.TYPE_BLOB

    @staticmethod
    def str2type(type_str: str) -> int:
        try:
            if type_str.find("INT") != -1:
                return SQLiteDatabase.TYPE_INTEGER
            elif type_str.find("CHAR") != -1 or type_str in ("TEXT", 'CLOB'):
                return SQLiteDatabase.TYPE_TEXT
            elif type_str in ("REAL", "DOUBLE", "DOUBLE PRECISION", "FLOAT"):
                return SQLiteDatabase.TYPE_REAL
            else:
                return SQLiteDatabase.TYPE_BLOB
        except AttributeError:
            return SQLiteDatabase.TYPE_BLOB

    @staticmethod
    def type2str(type_: int) -> str:
        if type_ == SQLiteDatabase.TYPE_BLOB:
            return "BLOB"
        elif type_ == SQLiteDatabase.TYPE_REAL:
            return "REAL"
        elif type_ == SQLiteDatabase.TYPE_TEXT:
            return "TEXT"
        elif type_ == SQLiteDatabase.TYPE_INTEGER:
            return "INTEGER"
        else:
            return "UNKNOWN"

    @staticmethod
    def columns2str(columns: typing.Sequence[str]):
        try:
            return ', '.join(columns)
        except TypeError:
            return '*'

    def rawExecute(self, sql: str):
        try:
            self._cursor.execute(sql)
            self._conn.commit()
            return self._cursor.fetchall()
        except sqlite3.DatabaseError as error:
            raise SQLiteDatabaseError(error)

    def getTableList(self) -> List[str]:
        """Get database table name list

        :return: table name list (utf-8)
        """
        self._cursor.execute(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name != \'{self.SpcSequenceTBLName}\';"
        )
        tables = [i[0] for i in self._cursor.fetchall()]
        return tables

    def getTableInfo(self, name: str) -> dict:
        """Get table info

        :param name:  table name
        :return: table column name, table column type list
        """
        self._cursor.execute("PRAGMA table_info({})".format(name))
        table_info = self._cursor.fetchall()
        column_list = [x[self.TBL_NAME] for x in table_info]
        return dict(list(zip(column_list, table_info)))

    def getColumnCount(self, name: str) -> int:
        self._cursor.execute(f'SELECT COUNT(*) FROM {name};')
        return self._cursor.fetchall()[0][0]

    def getColumnList(self, name: str) -> List[str]:
        """Get table column name list

        :param name: table name
        :return: table column name list
        """
        self._cursor.execute("PRAGMA table_info({})".format(name))
        table_info = self._cursor.fetchall()
        return [x[self.TBL_NAME] for x in table_info]

    def getColumnType(self, name: str) -> List[int]:
        """Get table column data type

        :param name: table name
        :return: column data type
        """
        try:
            self._cursor.execute("PRAGMA table_info({})".format(name))
            table_info = self._cursor.fetchall()
            return [self.str2type(x[self.TBL_TYPE]) for x in table_info]
        except (TypeError, AttributeError, IndexError):
            return []

    def getColumnTypeStr(self, name: str) -> List[str]:
        return list(map(self.type2str, self.getColumnType(name)))

    def getColumnIndex(self, table_name: str, column_name: str):
        """Get table specify column index

        :param table_name: table name
        :param column_name: column name
        :return: column index
        """
        try:
            table_info = self.getTableInfo(table_name)
            return table_info.get(column_name)[self.TBL_CID]
        except (TypeError, AttributeError, IndexError):
            return -1

    def getTableDefault(self, name: str) -> List[Any]:
        table_info = self.getTableInfo(name)
        column_names = self.getColumnList(name)
        return [table_info.get(n)[self.TBL_DEF] for n in column_names]

    def getLimitRowData(self, name: str, count: int, order: str,
                        columns: typing.Sequence[str] = None, latest: bool = False) -> List[Tuple]:
        columns = self.columns2str(columns)
        orientation = "DESC" if latest else ""

        try:
            self._cursor.execute(f'SELECT {columns} FROM {name} ORDER BY {order} {orientation} LIMIT {count}')
        except (TypeError, ValueError, sqlite3.DatabaseError) as error:
            raise SQLiteDatabaseError("getLimitRowData error: {}".format(error))
        else:
            return self._cursor.fetchall()

    def getTablePrimaryKey(self, name: str) -> Tuple[int, str, type]:
        """Get table primary key column, don't have pk will return 0

        :param name: table name
        :return: (primary key column, primary key name, primary key data type)
        """
        self._cursor.execute("PRAGMA table_info({})".format(name))
        table_info = self._cursor.fetchall()
        for i, schema in enumerate(table_info):
            if schema[self.TBL_PK] == 1:
                return i, schema[self.TBL_NAME], schema[self.TBL_TYPE]
        else:
            return 0, table_info[0][self.TBL_NAME], Any

    def getTableData(self, name: str, columns: typing.Sequence[str] = None) -> list:
        try:
            self._cursor.execute(f"SELECT {self.columns2str(columns)} from {name}")
            return self._cursor.fetchall()
        except sqlite3.DatabaseError:
            return list()

    def createTable(self, name: str, columns: int):
        try:

            if not isinstance(columns, (list, tuple)):
                raise TypeError("columns require list or tuple")

            if not len(columns):
                raise ValueError("table at least needs one column")

            data = list()
            for column, type_, is_null, default, pk in columns:
                default = "DEFAULT {}".format(default) if default else ""
                if is_null:
                    data_format = "{} {} {}".format(column, type_, default)
                else:
                    data_format = "{} {} NOT NULL {}".format(column, type_, default)

                if pk:
                    data_format += " PRIMARY KEY"

                data.append(data_format)

            # print("CREATE TABLE {} ({});".format(name, ",".join(data)))
            self._cursor.execute("CREATE TABLE {} ({});".format(name, ",".join(data)))
            self._conn.commit()
        except (TypeError, ValueError, sqlite3.DatabaseError) as error:
            raise SQLiteDatabaseError("Create table error:{}".format(error))

    def getAutoincrementSeq(self, name: str) -> int:
        return self.selectRecord(self.SpcSequenceTBLName, ['seq'], self.conditionFormat('name', name))[0][0]

    def deleteRecord(self, name: str, condition: str):
        """Delete records from table, when conditions matched

        :param name: table name
        :param condition: conditions
        :return: error raise an exception
        """
        try:
            self._cursor.execute("DELETE FROM {} WHERE {};".format(name, condition))
            self._conn.commit()
        except sqlite3.DatabaseError as error:
            raise SQLiteDatabaseError("Delete error:{}".format(error))

    def insertRecord(self, name: str, record: Union[list, tuple]):
        """Insert a record to table

        :param name: table name
        :param record: recode data
        :return: success return true else return false
        """
        try:
            if not isinstance(record, (list, tuple)):
                raise TypeError("recode require list or tuple type")

            # Get column names and types
            column_names = self.getColumnList(name)
            if len(column_names) != len(record):
                raise ValueError("recode length dis-matched")

            # Pre-process placeholder
            placeholder = ", ".join(['?'] * len(record))

            # Insert to sqlite and save
            self._cursor.execute("INSERT INTO {} VALUES({})".format(name, placeholder), record)
            self._conn.commit()
        except sqlite3.DatabaseError as error:
            raise SQLiteDatabaseError(error)

    def updateRecord(self, name: str, record: Union[list, tuple, dict], condition: Optional[str] = None):
        """Update exist recode

        :param name: table name
        :param record: recode data could be list or dict (with column name and data)
        :param condition: update record condition after WHERE
        :return: error raise DatabaseError
        """
        try:
            condition = condition or ""

            if not isinstance(record, (list, tuple, dict)):
                raise TypeError("recode require list or tuple or dict type")

            if not isinstance(condition, str):
                raise TypeError("condition require string object")

            # Get column name list and types
            column_names = self.getColumnList(name)

            # Check data length
            if isinstance(record, (list, tuple)) and len(column_names) != len(record):
                raise ValueError("recode length dis-matched")

            # Pre-process record
            recode_data = list()
            blob_records = list()

            # Update all data by sequence
            if isinstance(record, (list, tuple)):
                for column, data in zip(column_names, record):
                    blob_records.append(data)
                    recode_data.append("{} = ?".format(column, data))
            # Update particular data by column name
            else:
                for column_name, data in list(record.items()):
                    blob_records.append(data)
                    recode_data.append("{} = ?".format(column_name, data))

            recode_data = ", ".join(recode_data)

            # Update and save
            if not condition:
                self._cursor.execute('UPDATE {} SET {};'.format(name, recode_data), blob_records)
            else:
                self._cursor.execute('UPDATE {} SET {} WHERE {};'.format(name, recode_data, condition), blob_records)
            self._conn.commit()
        except (ValueError, TypeError, IndexError, sqlite3.DatabaseError) as error:
            raise SQLiteDatabaseError("Update error:{}".format(error))

    def selectRecord(self, name: str, columns: Optional[List[str]] = None, condition: Optional[str] = None):
        """Select record from table and matches conditions

        :param name: table name
        :param columns: columns name
        :param condition: conditions
        :return: return a list of records
        """
        try:

            columns = columns or list()
            condition = condition or ""

            if not isinstance(columns, (list, tuple)):
                raise TypeError("columns require list or tuple")

            if not isinstance(condition, str):
                raise TypeError("conditions require string object")

            # Pre-process
            columns = ", ".join(columns) or "*"

            # SQL
            if not condition:
                self._cursor.execute("SELECT {} FROM {};".format(columns, name))
            else:
                self._cursor.execute("SELECT {} FROM {} WHERE {};".format(columns, name, condition))

            return self._cursor.fetchall()
        except (TypeError, ValueError, sqlite3.DatabaseError) as error:
            raise SQLiteDatabaseError("Select error:{}".format(error))


class SQLCipherDatabase(SQLiteDatabase):
    def __init__(self, db_path: str, key: str, timeout: int = 20, check_same_thread: bool = True):
        super(SQLCipherDatabase, self).__init__(db_path, timeout, check_same_thread)
        self._conn.close()
        self._conn = sqlcipher.connect(db_path, timeout=timeout, check_same_thread=check_same_thread)
        self._cursor = self._conn.cursor()
        self._cursor.execute("PRAGMA key='{}'".format(key))


class SQLiteUserPasswordDatabase(object):
    DEF_PATH = "cipher.db"
    MAGIC_STR = "SQLiteUserPasswordDatabase"

    USER_TBL = "user"
    CIPHER_TBL = "cipher"

    USER_ID_KEY = "id"
    USER_NAME_KEY = "name"
    USER_DESC_KEY = "note"

    CIPHER_KEY = "cipher"
    CIPHER_LEVEL_KEY = "level"

    def __init__(self, magic: str = MAGIC_STR, path: str = DEF_PATH, self_check: bool = True):
        """SQLite base user password database
        c1 = c1_encrypt_func(raw_password)
        c2 = c2_encrypt_func(c1 + magic)
        c3 = c3_encrypt_func(c1 + c2)

        :param magic: magic string
        :param path: database path
        :param self_check: self check when database is opened
        """
        try:
            self.magic = magic
            self.db = SQLiteDatabase(path)
            if self_check:
                self.selfTest()
        except OSError:
            raise RuntimeError("打开密码数据库错误，数据库不存在！！！")
        except SQLiteDatabaseError as error:
            raise RuntimeError("打开密码数据库错误，{}".format(error))

    @classmethod
    def _c1_encrypt_func(cls, x: bytes) -> str:
        return hashlib.sha256(x).hexdigest()

    @classmethod
    def _c2_encrypt_func(cls, x: bytes) -> str:
        return hashlib.sha3_256(x).hexdigest()

    @classmethod
    def _c3_encrypt_func(cls, x: bytes) -> str:
        return hashlib.shake_256(x).hexdigest(32)

    def selfTest(self) -> bool:
        try:
            _, pk, _ = self.db.getTablePrimaryKey(self.CIPHER_TBL)
            for user in self.getUserList():
                level1, level2, level3 = self.getCipherLevel(user)

                c1 = self.db.selectRecord(self.CIPHER_TBL, [self.CIPHER_KEY], self.db.conditionFormat(pk, level1))[0][0]
                c2 = self.db.selectRecord(self.CIPHER_TBL, [self.CIPHER_KEY], self.db.conditionFormat(pk, level2))[0][0]
                c3 = self.db.selectRecord(self.CIPHER_TBL, [self.CIPHER_KEY], self.db.conditionFormat(pk, level3))[0][0]
                r2 = c1 + self.magic
                r3 = c1 + c2
                if self._c2_encrypt_func(r2.encode()) != c2 or self._c3_encrypt_func(r3.encode()) != c3:
                    raise RuntimeError("密码数据库自检错误，密码可能被他人非法篡改，请联系维护人员进行修复！！！")

                return True
        except IndexError:
            raise RuntimeError("读取密码数据库错误，数据库可能被损坏，请联系维护人员进行修复！！！")
        except SQLiteDatabaseError as error:
            raise RuntimeError("数据库读取错误：{}".format(error))

    def getUserList(self) -> List[str]:
        return [user[0] for user in self.db.selectRecord(self.USER_TBL, [self.USER_NAME_KEY])]

    def getCipherLevel(self, username: str):
        try:
            _, pk, _ = self.db.getTablePrimaryKey(self.USER_TBL)
            uid = self.db.selectRecord(self.USER_TBL, [pk], self.db.conditionFormat(self.USER_NAME_KEY, username))[0][0]
            return uid * 3 - 2, uid * 3 - 1, uid * 3
        except IndexError:
            raise RuntimeError("数据库读取错误：无此用户「{}」！！！".format(username))

    def getUserPassword(self, username: str):
        try:
            level, _, _ = self.getCipherLevel(username)
            _, pk, _ = self.db.getTablePrimaryKey(self.CIPHER_TBL)
            return self.db.selectRecord(self.CIPHER_TBL, [self.CIPHER_KEY], self.db.conditionFormat(pk, level))[0][0]
        except IndexError:
            raise RuntimeError("数据库读取错误：无此用户「{}」！！！".format(username))
        except SQLiteDatabaseError as error:
            raise RuntimeError("数据库读取错误：{}".format(error))

    def getUserDescriptor(self, username: str):
        try:
            condition = self.db.conditionFormat(self.USER_NAME_KEY, username)
            return self.db.selectRecord(self.USER_TBL, [self.USER_DESC_KEY], condition)[0][0]
        except IndexError:
            raise RuntimeError("数据库读取错误：无此用户「{}」！！！".format(username))

    def generateC1(self, password: bytes) -> str:
        return self._c1_encrypt_func(password)

    def checkPassword(self, username: str, c1: str):
        return c1 == self.getUserPassword(username)

    def updatePassword(self, username: str, c1: str):
        try:
            r2 = c1 + self.magic
            c2 = self._c2_encrypt_func(r2.encode())
            c3 = self._c3_encrypt_func((c1 + c2).encode())

            level1, level2, level3 = self.getCipherLevel(username)
            _, pk, _ = self.db.getTablePrimaryKey(self.CIPHER_TBL)

            self.db.updateRecord(self.CIPHER_TBL, {self.CIPHER_KEY: c1}, self.db.conditionFormat(pk, level1))
            self.db.updateRecord(self.CIPHER_TBL, {self.CIPHER_KEY: c2}, self.db.conditionFormat(pk, level2))
            self.db.updateRecord(self.CIPHER_TBL, {self.CIPHER_KEY: c3}, self.db.conditionFormat(pk, level3))
            self.selfTest()
        except IndexError:
            raise RuntimeError("数据库读取错误：无此用户「{}」！！！".format(username))
        except SQLiteDatabaseError as error:
            raise RuntimeError("数据库读取错误：{}".format(error))

    def addUser(self, user: str, password: str, desc: str = ""):
        try:

            # Calc uid
            uid = len(self.getUserList()) + 1

            # First add user
            self.db.insertRecord(self.USER_TBL, [uid, user, desc])

            # Second get user level
            level1, level2, level3 = self.getCipherLevel(user)

            # Create user cipher
            self.db.insertRecord(self.CIPHER_TBL, [level1, ""])
            self.db.insertRecord(self.CIPHER_TBL, [level2, ""])
            self.db.insertRecord(self.CIPHER_TBL, [level3, ""])

            # Finally, update user password
            self.updatePassword(user, password)
        except SQLiteDatabaseError as error:
            raise RuntimeError("添加用户「{}」,失败：{}！！！".format(user, error))

    def deleteUser(self, user: str):
        try:
            # First get user level
            level1, level2, level3 = self.getCipherLevel(user)

            # Delete cipher with specified level
            self.db.deleteRecord(self.CIPHER_TBL, self.db.conditionFormat(self.CIPHER_LEVEL_KEY, level1))
            self.db.deleteRecord(self.CIPHER_TBL, self.db.conditionFormat(self.CIPHER_LEVEL_KEY, level2))
            self.db.deleteRecord(self.CIPHER_TBL, self.db.conditionFormat(self.CIPHER_LEVEL_KEY, level3))

            # Finally delete user
            self.db.deleteRecord(self.USER_TBL, self.db.conditionFormat(self.USER_NAME_KEY, user))
        except SQLiteDatabaseError as error:
            raise RuntimeError("删除用户「{}」失败：{}！！！".format(user, error))

    @classmethod
    def create_database(cls, name: str):
        db = sqlite3.connect(name)
        cursor = db.cursor()
        cursor.execute("CREATE TABLE {}("
                       "{} INTEGER PRIMARY KEY AUTOINCREMENT,"
                       "{} TEXT NOT NULL UNIQUE,"
                       "{} TEXT DEFAULT '');".format(cls.USER_TBL,
                                                     cls.USER_ID_KEY, cls.USER_NAME_KEY, cls.USER_DESC_KEY))

        cursor.execute("CREATE TABLE {}("
                       "{} INTEGER PRIMARY KEY AUTOINCREMENT,"
                       "{} TEXT NOT NULL)".format(cls.CIPHER_TBL, cls.CIPHER_LEVEL_KEY, cls.CIPHER_KEY))
        db.commit()


class SQLiteGeneralSettingsItem(DynamicObject):
    _properties = {'id', 'name', 'data', 'min', 'max', 'precision', 'desc'}
    _json_dump_sequence = ('id', 'name', 'data', 'min', 'max', 'precision', 'desc')
    InitNameWithDash = ('id', 'min', 'max')

    def __init__(self, id_: int, name: str, data: Union[int, float],
                 min_: Union[int, float] = 0, max_: Union[int, float] = 0, precision: int = 0, desc: str = ""):
        """SQLite base settings item

        :param id_:  data index corresponding database row id
        :param name: settings item name
        :param data: settings data store as text, explained by application
        :param min_: settings item minimum value
        :param max_: settings item maximum value
        :param precision: settings item precision 0 means integer, others means data decimal point number
        :param desc: settings item description text help others understand
        """
        kwargs = dict()
        kwargs["id"] = id_
        kwargs["min"] = min_
        kwargs["max"] = max_
        kwargs["desc"] = desc
        kwargs["data"] = data
        kwargs["name"] = name
        kwargs["precision"] = precision
        super(SQLiteGeneralSettingsItem, self).__init__(**kwargs)

    def __repr__(self):
        # For db insert using, don't change it
        data = list()
        dict_ = self.dict
        for name in self._json_dump_sequence:
            data.append('"{}"'.format(dict_.get(name)))

        return ", ".join(data)

    @staticmethod
    def factory(dict_: dict):
        return SQLiteGeneralSettingsItem(**{f'{k}_' if k in ('id', 'min', 'max') else k: v for k, v in dict_.items()})


class SQLiteUIElementScheme(DynamicObject):
    _properties = {'name', 'min', 'max', 'precision'}
    _check = {
        'name': lambda x: isinstance(x, str),
        'min': lambda x: isinstance(x, (int, float)),
        'nax': lambda x: isinstance(x, (int, float)),
        'precision': lambda x: isinstance(x, int)
    }

    def getNumericalInput(self, name: str = '', readonly: bool = False) -> UiInputSetting:
        name = name or self.name
        if self.precision:
            return UiDoubleInput(
                name=name, minimum=self.min, maximum=self.max, decimals=self.precision, readonly=readonly
            )
        else:
            return UiIntegerInput(name=name, minimum=self.min, maximum=self.max, readonly=readonly)


class SQLiteUITableScheme(DynamicObject):
    COLUMN_HEADER = ('ID', '名称', '默认数据', '最小值', '最大值', '精度', '描述')
    _properties = {'name', 'maxRow', 'isMultiColumn', 'scheme', 'floating', 'readonly', 'ignoreNames'}
    _json_dump_sequence = ('maxRow', 'isMultiColumn', 'floating', 'readonly', 'scheme')

    def __init__(self, **kwargs):
        kwargs.setdefault('readonly', dict())
        kwargs.setdefault('ignoreNames', list())
        super(SQLiteUITableScheme, self).__init__(**kwargs)

    def subTitle(self) -> str:
        return f'#### 多列数据，最大行数：{self.maxRow}\n' if self.isMultiColumn else f'#### 单列数据'

    def mainTitle(self, title: str) -> str:
        return f"\n\n## {title} ({self.name})\n\n"

    def updateReadonly(self, check: Callable[[DynamicObject, str], bool]):
        for item in self.scheme.values():
            item = DynamicObject(**item)
            if check(self, item.name):
                self.readonly[item.id] = item.name

    def tableHeader(self) -> List[str]:
        header = list(self.COLUMN_HEADER) + ['权限']
        header[0] = 'Column' if self.isMultiColumn else 'Row'
        return header

    def generateMarkdownDocs(self, title: str):
        table = list()
        table.append(self.mainTitle(title))
        table.append(self.subTitle())
        table.append('|' + '|'.join(self.tableHeader()) + '|')
        table.append("----".join("|" * (len(self.tableHeader()) + 1)))

        for item in self.scheme.values():
            item = SQLiteGeneralSettingsItem.factory(item)
            if item.name in self.ignoreNames:
                continue

            rw = ['ReadOnly' if item.id in self.readonly else 'R/W']
            row_data = [f'{x}' for x in item.json.values()] + rw
            table.append('|' + '|'.join(row_data) + '|')

        return "\n".join(table)

    def getUIElementScheme(self) -> Dict[int, SQLiteUIElementScheme]:
        scheme = dict()
        for item in self.scheme.values():
            item = DynamicObject(**item)
            precision = str2number(item.precision)
            process = str2float if precision else str2number

            scheme[item.id] = SQLiteUIElementScheme(
                id=item.id,
                name=item.name, data=process(item.data),
                precision=item.precision, min=process(item.min), max=process(item.max)
            )

        return scheme


class SQLiteUIScheme:
    _singleton = None

    def __new__(cls, *args, **kwargs):
        if not cls._singleton:
            cls._singleton = super(SQLiteUIScheme, cls).__new__(cls, *args, **kwargs)

        return cls._singleton

    def __init__(self, path: str):
        """
        Path should be a json file, generate by SQLiteDatabaseCreator {table_name: SQLiteUITableScheme}
        """
        try:
            with open(path, 'rb') as fp:
                self.__db_scheme = json.load(fp)
        except (OSError, json.decoder.JSONDecodeError, DynamicObjectError) as e:
            raise RuntimeError(f'Load {self.__class__.__name__} error: {e}')

    def get_item_scheme(self, table: str, name: str) -> Optional[SQLiteUIElementScheme]:
        table_scheme = self.get_table_scheme(table)
        try:
            return [x for x in table_scheme.values() if x.name == name][0]
        except IndexError:
            return None

    def get_table_scheme(self, table: str) -> Dict[int, SQLiteUIElementScheme]:
        if table in self.__db_scheme:
            settings = self.__db_scheme.get(table)
            settings.update(dict(name=table))
            scheme = SQLiteUITableScheme(**settings)
            return scheme.getUIElementScheme()

        return dict()


class SQLiteDatabaseCreator(object):
    DESC_ID = -5
    NAME_ID = -4
    PRECISION_ID = 100000000
    LOWER_LIMIT_ID = -1
    UPPER_LIMIT_ID = 99999999

    ENUM_TAIL_ITEM_NAME = "MaxItemNum"
    ENUM_DEFAULT_NAME = "enum DataIndex"

    CAnnotationEnd = '*/'
    ProtobufAnnotation = 'For protocol buffer'
    AutoGenerateAnnotation = "/* Auto generated by python script do not modify */\n\n"

    def __init__(self, name: str, output_dir: str = "SQLiteDatabaseCreator_output"):
        """

        :param name: database file name
        :param output_dir: database and C/C++ headers output directory
        """

        if not isinstance(name, str):
            raise TypeError("{!r} require a str type".format("name"))

        if os.path.isdir(output_dir):
            shutil.rmtree(output_dir)
            time.sleep(1)

        os.mkdir(output_dir)

        self._db_name = os.path.join(output_dir, name)
        self._db_conn = sqlite3.connect(self._db_name)
        self._db_cursor = self._db_conn.cursor()
        self._output_dir = output_dir

    def __del__(self):
        self._db_conn.commit()
        self._db_conn.close()

    def __get_header_file_name(self, name: str) -> str:
        return os.path.join(self._output_dir, "{}.h".format(name))

    def __is_table_exist(self, table_name: str) -> bool:
        self._db_cursor.execute(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name != \'{SQLiteDatabase.SpcSequenceTBLName}\';"
        )
        tables = [i[0] for i in self._db_cursor.fetchall()]
        return table_name in tables

    @property
    def db_cursor(self):
        return self._db_cursor

    @staticmethod
    def _enum_tail(table_name: str) -> str:
        return "{}{}".format(table_name.capitalize(), SQLiteDatabaseCreator.ENUM_TAIL_ITEM_NAME)

    @staticmethod
    def __format_enum_item(name: str, index: int) -> str:
        return "\t{} = {}".format(name, index)

    @staticmethod
    def __output_protobuf_items(fp, name: str, items: List[str]):
        fp.write("\n\n")
        fp.write(f"/*\n{SQLiteDatabaseCreator.ProtobufAnnotation}\n\n")
        fp.write("{}{}".format(SQLiteDatabaseCreator.ENUM_DEFAULT_NAME, name.capitalize()) + " {\n")
        fp.write(";\n".join(items))
        fp.write(";\n}\n*/")

    @staticmethod
    def get_settings_table_ui_scheme(name: str, db_path: str) -> Dict[int, SQLiteUIElementScheme]:
        try:
            db = SQLiteDatabase(db_path)
        except (OSError, SQLiteDatabaseError) as e:
            print("Load db scheme error: {}".format(e))
            return dict()

        scheme = dict()
        for item in db.getTableData(name):
            idx, name, data, min_, max_, precision, desc = item
            precision = str2number(precision)
            process = str2float if precision else str2number
            scheme[idx] = SQLiteUIElementScheme(name=name, data=process(data),
                                                precision=precision, min=process(min_), max=process(max_))

        return scheme

    @staticmethod
    def get_general_table_ui_scheme(name: str, db_path: str) -> Dict[int, SQLiteUIElementScheme]:
        try:
            db = SQLiteDatabase(db_path)
        except (OSError, SQLiteDatabaseError) as e:
            print("Load db scheme error: {}".format(e))
            return dict()

        names = db.selectRecord(
            name, condition=SQLiteDatabase.conditionFormat('id', SQLiteDatabaseCreator.NAME_ID)
        )[0][1: -1]

        lowers = db.selectRecord(
            name, condition=SQLiteDatabase.conditionFormat('id', SQLiteDatabaseCreator.LOWER_LIMIT_ID)
        )[0][1: -1]

        uppers = db.selectRecord(
            name, condition=SQLiteDatabase.conditionFormat('id', SQLiteDatabaseCreator.UPPER_LIMIT_ID)
        )[0][1: -1]

        precisions = db.selectRecord(
            name, condition=SQLiteDatabase.conditionFormat('id', SQLiteDatabaseCreator.PRECISION_ID)
        )[0][1: -1]

        scheme = dict()
        for idx in range(len(names)):
            precision = str2number(precisions[idx])
            process = str2float if precision else str2number
            scheme[idx] = SQLiteUIElementScheme(name=names[idx], precision=precision,
                                                min=process(lowers[idx]), max=process(uppers[idx]))

        return scheme

    @property
    def database_path(self) -> str:
        return self._db_name

    @property
    def output_dir(self) -> str:
        return self._output_dir

    def generate_protobuf_file(self, seq: typing.Sequence[str], filename: str = ''):
        filename = filename or os.path.basename(self._db_name).replace('db', 'proto')
        with open(os.path.join(self.output_dir, filename), 'w', encoding='utf-8') as writer:
            writer.write(self.AutoGenerateAnnotation)
            writer.write('syntax = "proto3";\n')
            for table_name in seq:
                found = False
                with open(os.path.join(self.output_dir, f'{table_name}.h'), 'r') as reader:
                    while True:
                        line = reader.readline()
                        if not line or (found and self.CAnnotationEnd in line):
                            break

                        if self.ProtobufAnnotation in line:
                            found = True
                            continue

                        if not found:
                            continue

                        writer.write(line)

    def create_settings_table(self, name: str):
        self._db_cursor.execute("CREATE TABLE {} ("
                                "id INTEGER PRIMARY KEY NOT NULL UNIQUE,"
                                "name TEXT NOT NULL,"
                                "data TEXT NOT NULL,"
                                "min TEXT DEFAULT 0,"
                                "max TEXT DEFAULT 0,"
                                "precision INTEGER DEFAULT 0,"
                                "description TEXT"
                                ");".format(name))

        return True

    def create_general_table(self, name: str, max_column: int):
        """Create a generate database table with specified name and column count

        :param name: database table name
        :param max_column: database table data maximum column
        :return:
        """
        data_sentence = ",".join(["data{} TEXT".format(idx) for idx in range(max_column)])
        self._db_cursor.execute("CREATE TABLE {} ("
                                "id INTEGER PRIMARY KEY NOT NULL UNIQUE,"
                                "{}, description TEXT);".format(name, data_sentence))

    def get_general_table_limit(self, table_name: str) -> Tuple[Tuple[Any, Any]]:
        """Get table lower and upper limit value

        :param table_name:  table name
        :return:
        """
        self._db_cursor.execute("SELECT * FROM {} where id = {}".format(table_name, self.LOWER_LIMIT_ID))
        lower_limit = self._db_cursor.fetchall()[0][1:-1]

        self._db_cursor.execute("SELECT * FROM {} where id = {}".format(table_name, self.UPPER_LIMIT_ID))
        upper_limit = self._db_cursor.fetchall()[0][1:-1]

        return tuple(zip(lower_limit, upper_limit))

    def get_general_table_precision(self, table_name: str) -> tuple:
        try:
            self._db_cursor.execute("SELECT * FROM {} where id = {}".format(table_name, self.PRECISION_ID))
            return self._db_cursor.fetchall()[0][1:]
        except IndexError:
            return ()

    def set_settings_data(self, table_name: str,
                          settings: Sequence[SQLiteGeneralSettingsItem],
                          protobuf_enum: bool = False) -> SQLiteUITableScheme:
        """Create settings table and fill settings data

        :param table_name: settings table name
        :param settings:  settings data (list)
        :param protobuf_enum: generate protobuf enum
        :return: success return true, failed return false
        """

        # If table do not exist create table first
        if not self.__is_table_exist(table_name):
            self.create_settings_table(table_name)

        # Add settings data and generate C/C++ header file
        with open(self.__get_header_file_name(table_name), "wt") as fp:
            enum_items = list()
            for item in settings:
                if not isinstance(item, SQLiteGeneralSettingsItem):
                    continue

                self._db_cursor.execute("INSERT INTO {} VALUES({})".format(table_name, item))
                enum_items.append(self.__format_enum_item(item.name, item.id))

            self._db_conn.commit()

            # Headers for C/C++
            fp.write(self.AutoGenerateAnnotation)
            fp.write("{}".format(self.ENUM_DEFAULT_NAME) + " {\n")
            fp.write(",\n".join(enum_items))
            fp.write("\n};\n")

            # For protocol buffer
            if protobuf_enum:
                self.__output_protobuf_items(fp, table_name, enum_items)

        sc = {x.id: x.json for x in settings}
        ff = {x.id: x.name for x in settings if x.precision > 0}
        return SQLiteUITableScheme(name=table_name, maxRow=-1, isMultiColumn=False, floating=ff, scheme=sc)

    def set_general_table_limit(self, table_name: str,
                                max_row: int, max_column: int,
                                limit: Sequence[SQLiteGeneralSettingsItem],
                                protobuf_enum: bool = False) -> SQLiteUITableScheme:
        try:
            print("{} data count: {}".format(table_name, len(limit)))
            with open(self.__get_header_file_name(table_name), "wt") as fp:
                enum_items = list()
                fp.write(self.AutoGenerateAnnotation)
                fp.write(self.ENUM_DEFAULT_NAME + " {\n")
                for id_, item in enumerate(limit):
                    if not isinstance(item, SQLiteGeneralSettingsItem):
                        raise RuntimeError(f'item must be {SQLiteGeneralSettingsItem.__name__!r}')
                    enum_items.append(self.__format_enum_item(item.name, id_))

                enum_items.append(self.__format_enum_item(self._enum_tail(table_name), len(enum_items)))
                fp.write(",\n".join(enum_items))
                fp.write("\n};\n")

                if protobuf_enum:
                    self.__output_protobuf_items(fp, table_name, enum_items)

            lower_limit = [self.LOWER_LIMIT_ID]
            lower_limit.extend(tuple(x.min for x in limit))
            lower_limit.extend([0] * (max_column - len(limit)))
            lower_limit.append("'最小值'")

            upper_limit = [self.UPPER_LIMIT_ID]
            upper_limit.extend(tuple(x.max for x in limit))
            upper_limit.extend([0] * (max_column - len(limit)))
            upper_limit.append("'最大值'")

            precision = [self.PRECISION_ID]
            precision.extend(tuple(x.precision for x in limit))
            precision.extend([0] * (max_column - len(limit)))
            precision.append("'小数位'")

            desc = [self.DESC_ID]
            desc.extend(tuple("'{}'".format(x.desc) for x in limit))
            desc.extend([0] * (max_column - len(limit)))
            desc.append("'描述'")

            name = [self.NAME_ID]
            name.extend(tuple("'{}'".format(x.name) for x in limit))
            name.extend([0] * (max_column - len(limit)))
            name.append("'名称'")

            desc = ", ".join(tuple(map(str, desc)))
            name = ", ".join(tuple(map(str, name)))
            precision = ", ".join(tuple(map(str, precision)))
            lower_limit = ", ".join(tuple(map(str, lower_limit)))
            upper_limit = ", ".join(tuple(map(str, upper_limit)))

            self._db_cursor.execute("INSERT INTO {} VALUES({});".format(table_name, desc))
            self._db_cursor.execute("INSERT INTO {} VALUES({});".format(table_name, name))
            self._db_cursor.execute("INSERT INTO {} VALUES({});".format(table_name, precision))
            self._db_cursor.execute("INSERT INTO {} VALUES({});".format(table_name, lower_limit))
            self._db_cursor.execute("INSERT INTO {} VALUES({});".format(table_name, upper_limit))
            self._db_conn.commit()
        except (TypeError,):
            raise RuntimeError("Error limit request a tuple list")
        else:
            # id is column index
            for column in range(len(limit)):
                limit[column].id = column

            sc = {i: x.json for i, x in enumerate(limit)}
            ff = {c: l.name for c, l in enumerate(limit) if l.precision > 0}
            return SQLiteUITableScheme(name=table_name, maxRow=max_row, isMultiColumn=True, floating=ff, scheme=sc)

    def set_general_table_data(self, table_name: str, row_count: int, fill_random_data: bool = False):
        """Create general table and fill data

        :param table_name: general table name
        :param row_count: table data row count
        :param fill_random_data: fill random data
        :return:
        """
        # First get table limit
        limit = self.get_general_table_limit(table_name)

        for i in range(row_count):
            data = [i]
            for low, high in limit:
                low = int(low)
                high = int(high)
                data.append(random.randint(low, high) if fill_random_data else low)

            data.append('"{}{}"'.format(table_name, i + 1))
            data = ", ".join(tuple(map(str, data)))
            self._db_cursor.execute("INSERT INTO {} VALUES({})".format(table_name, data))


def sqlite_create_tables(db_name: str, tables: typing.Sequence[DBTable], verbose: bool = False) -> bool:
    error = None
    db_conn = sqlite3.connect(db_name)
    db_cursor = db_conn.cursor()

    try:
        for tbl in tables:
            create_sentence = tbl.get_create_sentence()
            if verbose:
                print(create_sentence)

            db_cursor.execute(create_sentence)

            for record in tbl.init_records:
                insert_sentence = tbl.get_inert_sentence(record)
                if verbose:
                    print(insert_sentence)

                db_cursor.execute(insert_sentence)
    except sqlite3.OperationalError as e:
        error = e
    finally:
        db_conn.commit()
        db_conn.close()
        if error:
            os.unlink(db_name)
            print(f'create_tables error =========> {error}')
            return False

        return True
