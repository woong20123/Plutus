import sqlite3
import csv
import json

# Sqlite DB 연결
def SqliteConn(sqlitePath):
    # '../DataBase/Plutus.sqlite3'
    conn = sqlite3.connect(sqlitePath)
    return conn

def GetSelectAllResult(dbconn, sql):
    cursor = dbconn.cursor()
    cursor.execute(sql)
    return cursor.fetchall()

def TruncateTable(dbconn, tableName):
    sql = 'DELETE FROM ' + tableName
    cursor = dbconn.cursor()
    cursor.execute(sql)
    dbconn.commit()

def BasicSqlExecute(dbconn, sql):
    cursor = dbconn.cursor()
    cursor.execute(sql)
    dbconn.commit()

def InsertFromList(dbconn, sql, ColList):
    for cols in ColList:
        cursor = dbconn.cursor()
        cursor.execute(sql,cols)
    dbconn.commit()
    return "insert 완료 " + sql + " from list" + " Count : " + str(len(ColList))

# CSV파일을 Mysql에 insert 합니다.
def InsertFromCSV(dbconn, sql, csvPath):
    f=open(csvPath,'r' , encoding='utf-8')
    csvReader=csv.reader(f)
    lineCount = 0
    ColList = []
    for row in csvReader :
        colCount = len(row)
        if(lineCount > 0):
            inputParam = []
            # 컬럼을 만듭니다.
            for i in range(0, colCount):
                inputParam.append(row[i])
            ColList.append(inputParam)
        lineCount+=1
    return InsertFromList(dbconn, sql, ColList)

def InsertFromJSON(dbconn, sql, jsonString):
    ColList = []
    insertDatas = json.loads(jsonString)
    for row in insertDatas :
        inputParam = []
        for key, value in row.items():
            inputParam.append(value)
        ColList.append(inputParam)
    return InsertFromList(dbconn, sql, ColList)
            
