import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from connect_sqlite.ConnectSqlite import *



# Stock정보 입력
def SetStockInfo(conn):
    TruncateTable(conn, 'stock_info')
    sql = '''
    INSERT INTO stock_info ("code", "name")
    VALUES (?, ?)
    '''
    InsertFromCSV(conn,sql, os.getcwd() + '/DataBase/StockInfo.csv')

# Target Stock정보 입력
def SetTargetInfo(conn):
    TruncateTable(conn, 'target_stock_info')
    sql = '''
    INSERT INTO target_stock_info ("name", "sell_target_price", "buy_target_price", "stock_type", "current_price", "invest_grade")
    VALUES (?, ?, ?, ?, ?, ?)
    '''
    InsertFromCSV(conn,sql, os.getcwd() + + '/DataBase/target_stock.csv')

# 가지고 있는 주식 정보 Insert 

def CreateHaveStockInfo(conn):
    TruncateTable(conn, 'have_stock_info')
    sql = '''
    CREATE TABLE "have_stock_info" (
	"code"	TEXT NOT NULL,
	"name"	TEXT NOT NULL,
	"buy_total_price"	INTEGER NOT NULL,
	"cur_price"	INTEGER NOT NULL,
	"have_count"	INTEGER NOT NULL,
	PRIMARY KEY("name"));
    '''
    BasicSqlExecute(conn,sql)

InsertHaveStockInfoSQL = '''
    INSERT INTO have_stock_info ("code", "name", "buy_total_price", "cur_price", "have_count")
    VALUES (?, ?, ?, ?, ?)
    '''
def InsertHaveStockInfoFromJson(conn, jsonString):
    TruncateTable(conn, 'have_stock_info')
    return InsertFromJSON(conn,InsertHaveStockInfoSQL, jsonString)

def InsertHaveStockInfoFromCsv(conn, csv_file):
    TruncateTable(conn, 'have_stock_info')
    return InsertFromCSV(conn,InsertHaveStockInfoSQL, os.getcwd() + csv_file)

InsertPurchasePerStockSQL = '''
    INSERT INTO purchase_per_stock ("type", "purchase")
    VALUES (?, ?)
    '''
def InsertPurchasePerStockFromJson(conn, jsonString):
    TruncateTable(conn, 'purchase_per_stock')
    return InsertFromJSON(conn,InsertPurchasePerStockSQL, jsonString)
    

def SetMetaData(conn):
    TruncateTable(conn, 'meta_stock_data')
    # 주식당 할당 매입 금액
    sql = 'INSERT INTO meta_stock_data (name, value) VALUES ("alloc amount per stock", "280")'
    BasicSqlExecute(conn, sql)

if __name__ == '__main__' :
    conn = SqliteConn(os.getcwd() + '/DataBase/Plutus.sqlite3')
    
    SetStockInfo(conn)
    SetTargetInfo(conn)

    conn.close()