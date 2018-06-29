# -*- coding: utf-8 -*-
import os
import sqlite3
__all__ = ['SQLiteDatabase', 'SQLiteDatabaseError']


class SQLiteDatabaseError(Exception):
    pass


class SQLiteDatabase(object):
    TYPE_INTEGER, TYPE_REAL, TYPE_TEXT, TYPE_BLOB = list(range(4))
    TBL_CID, TBL_NAME, TBL_TYPE, TBL_REQUIRED, TBL_DEF, TBL_PK = list(range(6))

    def __init__(self, db_path, timeout=20):
        if not os.path.isfile(db_path):
            raise IOError("{} do not exist".format(db_path))

        self.__conn = sqlite3.connect(db_path, timeout=timeout)
        self.__cursor = self.__conn.cursor()

    @staticmethod
    def conditionFormat(k, v, t):
        t = SQLiteDatabase.detectDataType(t)
        return '{} = "{}"'.format(k, v) if t == SQLiteDatabase.TYPE_TEXT else '{} = {}'.format(k, v)

    @staticmethod
    def searchConditionFormat(k, v, t):
        t = SQLiteDatabase.detectDataType(t)
        return '{} LIKE "%{}%"'.format(k, v) if t == SQLiteDatabase.TYPE_TEXT else '{} LIKE %{}%'.format(k, v)

    @staticmethod
    def globalSearchConditionFormat(k, v, t):
        t = SQLiteDatabase.detectDataType(t)
        return '{} GLOB "*{}*"'.format(k, v) if t == SQLiteDatabase.TYPE_TEXT else '{} LIKE *{}*'.format(k, v)

    @staticmethod
    def detectDataType(type_str):
        if type_str.find("INT") != -1:
            return SQLiteDatabase.TYPE_INTEGER
        elif type_str.find("CHAR") != -1 or type_str in ("TEXT", 'CLOB'):
            return SQLiteDatabase.TYPE_TEXT
        elif type_str in ("REAL", "DOUBLE", "DOUBLE PRECISION", "FLOAT"):
            return SQLiteDatabase.TYPE_REAL
        else:
            return SQLiteDatabase.TYPE_BLOB

    def getTableList(self):
        """Get database table name list

        :return: table name list (utf-8)
        """
        self.__cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name != \'sqlite_sequence\';")
        tables = [i[0] for i in self.__cursor.fetchall()]
        return tables

    def getTableInfo(self, name):
        """Get table info

        :param name:  table name
        :return: table column name, table column type list
        """
        self.__cursor.execute("PRAGMA table_info({})".format(name))
        table_info = self.__cursor.fetchall()
        column_list = [x[self.TBL_NAME] for x in table_info]
        return dict(list(zip(column_list, table_info)))

    def getColumnList(self, name):
        """Get table column name list

        :param name: table name
        :return: table column name list
        """
        self.__cursor.execute("PRAGMA table_info({})".format(name))
        table_info = self.__cursor.fetchall()
        return [x[self.TBL_NAME] for x in table_info]

    def getColumnType(self, name):
        """Get table column data type

        :param name: table name
        :return: column data type
        """
        try:
            self.__cursor.execute("PRAGMA table_info({})".format(name))
            table_info = self.__cursor.fetchall()
            return [self.detectDataType(x[self.TBL_TYPE]) for x in table_info]
        except (TypeError, AttributeError, IndexError):
            return []

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
        self.__cursor.execute("PRAGMA table_info({})".format(name))
        table_info = self.__cursor.fetchall()
        for i, schema in enumerate(table_info):
            if schema[self.TBL_PK] == 1:
                return i, schema[self.TBL_NAME], schema[self.TBL_TYPE]
        else:
            return 0, table_info[0][self.TBL_NAME], schema[self.TBL_TYPE]

    def getTableData(self, name):
        try:
            self.__cursor.execute("SELECT * from {}".format(name))
            return self.__cursor.fetchall()
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
            self.__cursor.execute("CREATE TABLE {} ({});".format(name, ",".join(data)))
            self.__conn.commit()
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
            self.__cursor.execute("INSERT INTO {} VALUES({})".format(name, recode_data), blob_records)
            self.__conn.commit()
        except sqlite3.DatabaseError as error:
                raise SQLiteDatabaseError(error)

    def updateRecord(self, name, where, record):
        """Update an exist recode

        :param name: table name
        :param where: recode location
        :param record: recode data could be list or dict (with column name and data)
        :return: error raise DatabaseError
        """
        try:
            if not isinstance(where, (list, tuple)):
                raise TypeError("where require list or tuple type")

            if not isinstance(record, (list, tuple, dict)):
                raise TypeError("recode require list or tuple or dict type")

            # Get primary key name, data and type
            pk_name, pk_data, pk_type = where

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
            # print('UPDATE {} SET {} WHERE {}="{}";'.format(name, recode_data, pk_name, pk_data))
            self.__cursor.execute('UPDATE {} SET {} WHERE {}="{}";'.format(name, recode_data, pk_name, pk_data),
                                  blob_records)
            self.__conn.commit()
        except (ValueError, TypeError, IndexError, sqlite3.DatabaseError) as error:
            raise SQLiteDatabaseError("Update error:{}".format(error))

    def deleteRecord(self, name, conditions):
        """Delete records from table, when conditions matched

        :param name: table name
        :param conditions: conditions
        :return: error raise an exception
        """
        try:

            self.__cursor.execute("DELETE FROM {} WHERE {};".format(name, conditions))
            self.__conn.commit()
        except sqlite3.DatabaseError as error:
            raise SQLiteDatabaseError("Delete error:{}".format(error))

    def selectRecord(self, name, columns=None, conditions=None):
        """Select record from table and matches conditions

        :param name: table name
        :param columns: columns name
        :param conditions: conditions
        :return: return a list of records
        """
        try:

            columns = columns or list()
            conditions = conditions or ""

            if not isinstance(columns, (list, tuple)):
                raise TypeError("columns require list or tuple")

            if not isinstance(conditions, str):
                raise TypeError("conditions require string object")

            # Pre process
            columns = ", ".join(columns) or "*"

            # SQL
            if not conditions:
                self.__cursor.execute("SELECT {} FROM {};".format(columns, name))
            else:
                self.__cursor.execute("SELECT {} FROM {} WHERE {};".format(columns, name, conditions))

            return self.__cursor.fetchall()
        except (TypeError, ValueError, sqlite3.DatabaseError) as error:
            raise SQLiteDatabaseError("Select error:{}".format(error))
