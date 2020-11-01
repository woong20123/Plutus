import ConnectSqlite

basePath='C:/Users/Kim/Documents/Plutus/'

# Stock정보 입력
def SetStockInfo(conn):
    ConnectSqlite.TruncateTable(conn, 'stock_info')
    sql = '''
    INSERT INTO stock_info ("code", "name")
    VALUES (?, ?)
    '''
    ConnectSqlite.InsertFromCSV(conn,sql, basePath + 'DataBase/StockInfo.csv')

# Target Stock정보 입력
def SetTargetInfo(conn):
    ConnectSqlite.TruncateTable(conn, 'target_stock_info')
    sql = '''
    INSERT INTO target_stock_info ("name", "sell_target_price", "buy_target_price", "stock_type", "current_price", "invest_grade")
    VALUES (?, ?, ?, ?, ?, ?)
    '''
    ConnectSqlite.InsertFromCSV(conn,sql, basePath + 'DataBase/target_stock.csv')

# 가지고 있는 주식 정보 추가 
def SetHaveStockInfo(conn):
    ConnectSqlite.TruncateTable(conn, 'have_stock_info')
    sql = '''
    INSERT INTO have_stock_info ("code", "name", "buy_amount")
    VALUES (?, ?, ?)
    '''
    ConnectSqlite.InsertFromCSV(conn,sql, basePath + 'DataBase/target_stock.csv')

def SetMetaData(conn):
    ConnectSqlite.TruncateTable(conn, 'meta_stock_data')
    # 주식당 할당 매입 금액
    sql = 'INSERT INTO meta_stock_data (name, value) VALUES ("alloc amount per stock", "280")'
    ConnectSqlite.BasicSqlExecute(conn, sql)

if __name__ == '__main__' :
    conn = ConnectSqlite.SqliteConn(basePath + 'DataBase/Plutus.sqlite3')
    
    SetStockInfo(conn)
    SetTargetInfo(conn)

    conn.close()