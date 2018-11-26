# -*- coding: utf-8 -*-
import os
import sqlite3
import hashlib

try:
    from pysqlcipher3 import dbapi2 as sqlcipher
except ImportError:
    import sqlite3 as sqlcipher

__all__ = ['SQLiteDatabase', 'SQLCipherDatabase', 'SQLiteUserPasswordDatabase', 'SQLiteDatabaseError']


class SQLiteDatabaseError(Exception):
    pass


class SQLiteDatabase(object):
    TYPE_INTEGER, TYPE_REAL, TYPE_TEXT, TYPE_BLOB = list(range(4))
    TBL_CID, TBL_NAME, TBL_TYPE, TBL_REQUIRED, TBL_DEF, TBL_PK = list(range(6))

    def __init__(self, db_path, timeout=20, check_same_thread=True):
        if not os.path.isfile(db_path):
            raise IOError("{} do not exist".format(db_path))

        self._conn = sqlite3.connect(db_path, timeout=timeout, check_same_thread=check_same_thread)
        self._cursor = self._conn.cursor()

    @property
    def raw_cursor(self):
        return self._cursor

    @property
    def raw_connect(self):
        return self._conn

    @staticmethod
    def conditionFormat(k, v, t=None):
        t = SQLiteDatabase.str2type(t) if isinstance(t, str) else SQLiteDatabase.detectDataType(v)
        return '{} = "{}"'.format(k, v) if t == SQLiteDatabase.TYPE_TEXT else '{} = {}'.format(k, v)

    @staticmethod
    def searchConditionFormat(k, v, t=None):
        t = SQLiteDatabase.str2type(t) if isinstance(t, str) else SQLiteDatabase.detectDataType(v)
        return '{} LIKE "%{}%"'.format(k, v) if t == SQLiteDatabase.TYPE_TEXT else '{} LIKE %{}%'.format(k, v)

    @staticmethod
    def globalSearchConditionFormat(k, v, t=None):
        t = SQLiteDatabase.str2type(t) if isinstance(t, str) else SQLiteDatabase.detectDataType(v)
        return '{} GLOB "*{}*"'.format(k, v) if t == SQLiteDatabase.TYPE_TEXT else '{} LIKE *{}*'.format(k, v)

    @staticmethod
    def detectDataType(data):
        if isinstance(data, (int, bool)):
            return SQLiteDatabase.TYPE_INTEGER
        elif isinstance(data, str):
            return SQLiteDatabase.TYPE_TEXT
        elif isinstance(data, float):
            return SQLiteDatabase.TYPE_REAL
        else:
            return SQLiteDatabase.TYPE_BLOB

    @staticmethod
    def str2type(type_str):
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
    def type2str(type_):
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

    def rawExecute(self, sql):
        try:
            self._cursor.execute(sql)
            self._conn.commit()
            return self._cursor.fetchall()
        except sqlite3.DatabaseError as error:
            raise SQLiteDatabaseError(error)

    def getTableList(self):
        """Get database table name list

        :return: table name list (utf-8)
        """
        self._cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name != \'sqlite_sequence\';")
        tables = [i[0] for i in self._cursor.fetchall()]
        return tables

    def getTableInfo(self, name):
        """Get table info

        :param name:  table name
        :return: table column name, table column type list
        """
        self._cursor.execute("PRAGMA table_info({})".format(name))
        table_info = self._cursor.fetchall()
        column_list = [x[self.TBL_NAME] for x in table_info]
        return dict(list(zip(column_list, table_info)))

    def getColumnList(self, name):
        """Get table column name list

        :param name: table name
        :return: table column name list
        """
        self._cursor.execute("PRAGMA table_info({})".format(name))
        table_info = self._cursor.fetchall()
        return [x[self.TBL_NAME] for x in table_info]

    def getColumnType(self, name):
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

    def getColumnTypeStr(self, name):
        return list(map(self.type2str, self.getColumnType(name)))

    def getColumnIndex(self, table_name, column_name):
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

    def getTableDefault(self, name):
        table_info = self.getTableInfo(name)
        column_names = self.getColumnList(name)
        return [table_info.get(n)[self.TBL_DEF] for n in column_names]

    def getTablePrimaryKey(self, name):
        """Get table primary key column if do not have pk return 0

        :param name: table name
        :return: (primary key column, primary key name, primary key data type)
        """
        self._cursor.execute("PRAGMA table_info({})".format(name))
        table_info = self._cursor.fetchall()
        for i, schema in enumerate(table_info):
            if schema[self.TBL_PK] == 1:
                return i, schema[self.TBL_NAME], schema[self.TBL_TYPE]
        else:
            return 0, table_info[0][self.TBL_NAME], schema[self.TBL_TYPE]

    def getTableData(self, name):
        try:
            self._cursor.execute("SELECT * from {}".format(name))
            return self._cursor.fetchall()
        except sqlite3.DatabaseError:
            return list()

    def createTable(self, name, columns):
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

    def insertRecord(self, name, record):
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
            column_types = self.getColumnType(name)
            if len(column_names) != len(record):
                raise ValueError("recode length dis-matched")

            # Pre-process record
            recode_data = list()
            blob_records = list()
            for column, data, type_ in zip(column_names, record, column_types):
                if type_ == self.TYPE_TEXT:
                    recode_data.append('"{}"'.format(data))
                elif type_ == self.TYPE_BLOB:
                    recode_data.append("?")
                    blob_records.append(data)
                else:
                    recode_data.append("{}".format(data))

            recode_data = ", ".join(recode_data)

            # Insert to sqlite and save
            # print("INSERT INTO {} VALUES({})".format(name, recode_data))
            self._cursor.execute("INSERT INTO {} VALUES({})".format(name, recode_data), blob_records)
            self._conn.commit()
        except sqlite3.DatabaseError as error:
                raise SQLiteDatabaseError(error)

    def updateRecord(self, name, record, condition=None):
        """Update an exist recode

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
            column_types = self.getColumnType(name)

            # Check data length
            if isinstance(record, (list, tuple)) and len(column_names) != len(record):
                raise ValueError("recode length dis-matched")

            # Pre process record
            recode_data = list()
            blob_records = list()

            # Update all data by sequence
            if isinstance(record, (list, tuple)):
                for column, data, type_ in zip(column_names, record, column_types):
                    if type_ == self.TYPE_TEXT:
                        recode_data.append('{} = "{}"'.format(column, data))
                    elif type_ == self.TYPE_BLOB:
                        blob_records.append(data)
                        recode_data.append("{} = ?".format(column, data))
                    else:
                        recode_data.append("{} = {}".format(column, data))
            # Update particular data by column name
            else:
                for column_name, data in list(record.items()):
                    type_ = column_types[column_names.index(column_name)]
                    if type_ == self.TYPE_TEXT:
                        recode_data.append('{} = "{}"'.format(column_name, data))
                    elif type_ == self.TYPE_BLOB:
                        blob_records.append(data)
                        recode_data.append("{} = ?".format(column_name, data))
                    else:
                        recode_data.append("{} = {}".format(column_name, data))

            recode_data = ", ".join(recode_data)

            # Update and save
            if not condition:
                self._cursor.execute('UPDATE {} SET {};'.format(name, recode_data), blob_records)
            else:
                self._cursor.execute('UPDATE {} SET {} WHERE {};'.format(name, recode_data, condition), blob_records)
            self._conn.commit()
        except (ValueError, TypeError, IndexError, sqlite3.DatabaseError) as error:
            raise SQLiteDatabaseError("Update error:{}".format(error))

    def deleteRecord(self, name, condition):
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

    def selectRecord(self, name, columns=None, condition=None):
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

            # Pre process
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
    def __init__(self, db_path, key, timeout=20, check_same_thread=True):
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

    def __init__(self, magic=MAGIC_STR, path=DEF_PATH, self_check=True):
        """SQLite user password database
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

    def _c1_encrypt_func(self, x):
        return hashlib.sha256(x).hexdigest()

    def _c2_encrypt_func(self, x):
        return hashlib.sha3_256(x).hexdigest()

    def _c3_encrypt_func(self, x):
        return hashlib.shake_256(x).hexdigest(32)

    def selfTest(self):
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

    def getUserList(self):
        return [user[0] for user in self.db.selectRecord(self.USER_TBL, [self.USER_NAME_KEY])]

    def getCipherLevel(self, username):
        try:
            _, pk, _ = self.db.getTablePrimaryKey(self.USER_TBL)
            uid = self.db.selectRecord(self.USER_TBL, [pk], self.db.conditionFormat(self.USER_NAME_KEY, username))[0][0]
            return uid * 3 - 2, uid * 3 - 1, uid * 3
        except IndexError:
            raise RuntimeError("数据库读取错误：无此用户「{}」！！！".format(username))

    def getUserPassword(self, username):
        try:
            level, _, _ = self.getCipherLevel(username)
            _, pk, _ = self.db.getTablePrimaryKey(self.CIPHER_TBL)
            return self.db.selectRecord(self.CIPHER_TBL, [self.CIPHER_KEY], self.db.conditionFormat(pk, level))[0][0]
        except IndexError:
            raise RuntimeError("数据库读取错误：无此用户「{}」！！！".format(username))
        except SQLiteDatabaseError as error:
            raise RuntimeError("数据库读取错误：{}".format(error))

    def getUserDescriptor(self, username):
        try:
            condition = self.db.conditionFormat(self.USER_NAME_KEY, username)
            return self.db.selectRecord(self.USER_TBL, [self.USER_DESC_KEY], condition)[0][0]
        except IndexError:
            raise RuntimeError("数据库读取错误：无此用户「{}」！！！".format(username))

    def generateC1(self, password):
        return self._c1_encrypt_func(password)

    def checkPassword(self, username, c1):
        return c1 == self.getUserPassword(username)

    def updatePassword(self, username, c1):
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

    def addUser(self, user, password, desc=""):
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

            # Finally update user password
            self.updatePassword(user, password)
        except SQLiteDatabaseError as error:
            raise RuntimeError("添加用户「{}」,失败：{}！！！".format(user, error))

    def deleteUser(self, user):
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
    def create_database(cls, name):
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
