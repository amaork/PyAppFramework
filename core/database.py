# -*- coding: utf-8 -*-
import os
import sqlite3
__all__ = ['SQLiteDatabase', 'SQLiteDatabaseError']


class SQLiteDatabaseError(Exception):
    pass


class SQLiteDatabase(object):
    TYPE_INTEGER, TYPE_REAL, TYPE_TEXT, TYPE_BLOB = range(4)
    TBL_CID, TBL_NAME, TBL_TYPE, TBL_REQUIRED, TBL_DEF, TBL_PK = range(6)

    def __init__(self, db_path):
        if not os.path.isfile(db_path):
            raise IOError("{} do not exist".format(db_path))

        self.__conn = sqlite3.connect(db_path)
        self.__cursor = self.__conn.cursor()

    def __del__(self):
        self.__conn.commit()
        self.__conn.close()

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
        return dict(zip(column_list, table_info))

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
        """Get table primary key row if do not have pk return 0

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

    def insertRecode(self, name, record):
        """Insert a recode to table

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
                    recode_data.append(u'"{}"'.format(data))
                elif type_ == self.TYPE_BLOB:
                    recode_data.append(u"?")
                    blob_records.append(data)
                else:
                    recode_data.append(u"{}".format(data))

            recode_data = ", ".join(recode_data).encode("utf-8")

            # Insert to sqlite and save
            # print("INSERT INTO {} VALUES({})".format(name, recode_data))
            self.__cursor.execute("INSERT INTO {} VALUES({})".format(name, recode_data), blob_records)
            self.__conn.commit()
        except sqlite3.DatabaseError as error:
                raise SQLiteDatabaseError(error)

    def updateRecode(self, name, where, record):
        """Update an exist recode

        :param name: table name
        :param where: recode location
        :param record: recode data
        :return: error raise DatabaseError
        """
        try:
            if not isinstance(where, (list, tuple)):
                raise TypeError("where require list or tuple type")

            if not isinstance(record, (list, tuple)):
                raise TypeError("recode require list or tuple type")

            # Get primary key name, data and type
            pk_name, pk_data, pk_type = where

            # Get column name list and types
            column_names = self.getColumnList(name)
            column_types = self.getColumnType(name)
            if len(column_names) != len(record):
                raise ValueError("recode length dis-matched")

            # Pre process record
            recode_data = list()
            blob_records = list()
            for column, data, type_ in zip(column_names, record, column_types):
                if type_ == self.TYPE_TEXT:
                    recode_data.append(u'{} = "{}"'.format(column, data))
                elif type_ == self.TYPE_BLOB:
                    blob_records.append(data)
                    recode_data.append(u"{} = ?".format(column, data))
                else:
                    recode_data.append(u"{} = {}".format(column, data))

            pk_name = pk_name.encode("utf-8")
            recode_data = ", ".join(recode_data).encode("utf-8")
            pk_data = pk_data.encode("utf-8") if pk_type == self.TYPE_TEXT else pk_data

            # Update and save
            # print('UPDATE {} SET {} WHERE {}="{}";'.format(name, recode_data, pk_name, pk_data))
            self.__cursor.execute('UPDATE {} SET {} WHERE {}="{}";'.format(name, recode_data, pk_name, pk_data),
                                  blob_records)
            self.__conn.commit()
        except (ValueError, TypeError, sqlite3.DatabaseError) as error:
            raise SQLiteDatabaseError("Update error:{}".format(error))
