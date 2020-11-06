#-*-coding:utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
import csv

import json
from PyQt5.QAxContainer import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from connect_sqlite.ConnectSqlite import *
from connect_sqlite.SqliteLogic import *


class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Plutus')
        self.setGeometry(200, 200, 1200, 800)

        # 키움 OpenAPI 라이브러리 추가 
        self.kiwoom = QAxWidget('KHOPENAPI.KHOpenAPICtrl.1')
        self.kiwoom.dynamicCall('CommConnect()')

        self.text_edit = QTextEdit(self)
        self.text_edit.setGeometry(10, 260, 560, 200)
        self.text_edit.setEnabled(False)

        ######## [입력] ########

        # 코드 검색용 UI 인터페이스
        label = QLabel('종목코드 : ', self)
        label.setGeometry(20, 20, 150, 30)

        self.code_edit = QLineEdit(self)
        self.code_edit.move(150, 20)
        self.code_edit.setText('039490')

        ######## [계좌 정보 조회] ########
        label = QLabel('[계좌 정보 조회] ', self)
        label.setGeometry(10, 120, 150, 30)
        # 버튼 
        getAccountbtn = QPushButton('계좌 정보 셋팅', self)
        getAccountbtn.move(20, 150)
        getAccountbtn.clicked.connect(self.getAccountbtn_clicked)


        ######## [주식당 매입 금액] ########
        label = QLabel('[주식당 매입기준금액] ', self)
        label.setGeometry(10, 60, 150, 30)

        self.stock_per_purchase_edit = QLineEdit(self)
        self.stock_per_purchase_edit.setGeometry(20, 90, 80, 30)
        self.stock_per_purchase_edit.setText('280')

        # 버튼 
        stock_per_purchase_btn = QPushButton('주식당 매입 금액 셋팅', self)
        stock_per_purchase_btn.setGeometry(120, 90, 150, 30)
        stock_per_purchase_btn.clicked.connect(self.stock_per_purchase_btn_clicked)

        ######## [버튼] ########

        # 버튼 
        findbtn = QPushButton('조회', self)
        findbtn.move(600, 20)
        findbtn.clicked.connect(self.findbtn_clicked)

        # 버튼 
        getCodebtn = QPushButton('종목코드 얻기', self)
        getCodebtn.move(600, 60)
        getCodebtn.clicked.connect(self.getCodebtn_clicked)

        

        self.listWidget = QListWidget(self)
        self.listWidget.setGeometry(700, 60, 170, 130)

        # 콜백이벤트 등록
        self.kiwoom.OnEventConnect.connect(self.on_connect)
        self.kiwoom.OnReceiveTrData.connect(self.on_receiveTr)

        # sqlite conn
        self.conn = SqliteConn(os.getcwd() + '/DataBase/Plutus.sqlite3')

    def __del__(self):
        self.conn.close()

    # 검색용 버튼 클릭 이벤트 함수
    def findbtn_clicked(self):
        code = self.code_edit.text()
        self.text_edit.append('종목코드: ' + code)

        # SetInputValue
        self.kiwoom.dynamicCall('SetInputValue(QString, QString)', '종목코드', code)

        # CommRqData
        self.kiwoom.dynamicCall('CommRqData(QString, QString, int, QString)', '주식기본정보조회', 'opt10001', 0, '10001')

    def getAccountbtn_clicked(self):
        self.kiwoom.dynamicCall('SetInputValue(QString, QString)', '계좌번호', self.account_num.rstrip(';'))
        self.kiwoom.dynamicCall('CommRqData(QString, QString, int, QString)', '실시간잔고', 'opt10085', 0, '10002')

    # 마켓 정보 가져오기 버튼
    def getCodebtn_clicked(self):
        stockInfoList = self.get_StockListInfo(self.kospi_market_list)
        self.text_edit.append('kospi MarkerCode Count = ' +  str(len(stockInfoList)))

        # to csv 파일
        with open('C:/Users/Kim/Documents/Plutus/DataBase/StockInfo.csv','w+' , encoding='utf-8', newline='') as f :            
            writer = csv.writer(f)
            for stockInfo in stockInfoList:
                writer.writerow(stockInfo)

    def stock_per_purchase_btn_clicked(self):
        stock_per_purchase_base = int(self.stock_per_purchase_edit.text())
        stock_per_purchase_list = []

        stock_per_purchase_metas = [('상', 1.5),('중', 0.9),('하', 0.6)]
        for meta in stock_per_purchase_metas:
            stock_per_purchase = {}
            stock_per_purchase['type'] = meta[0]
            stock_per_purchase['purchase'] = stock_per_purchase_base * meta[1]
            stock_per_purchase_list.append(stock_per_purchase)

        stock_per_purchase_json = json.dumps(stock_per_purchase_list, ensure_ascii=False)

        self.text_edit.append(InsertPurchasePerStockFromJson(self.conn, stock_per_purchase_json))

    # 마켓 정보리스트 가져오기
    def get_MarketList(self, marketType):
        callRet = ''
        if marketType == 'kospi':
            callRet = self.kiwoom.dynamicCall('GetCodeListByMarket(QString)', ['0'])
        elif marketType == 'kosdaq':
            callRet = self.kiwoom.dynamicCall('GetCodeListByMarket(QString)', ['10'])

        code_list = callRet.split(';')
        return code_list;

    def get_StockListInfo(self, stock_list):
        stockInfoList =[]
        for x in stock_list :
            name = self.kiwoom.dynamicCall('GetMasterCodeName(QString)', [x])
            stockInfoList.append([x,name])
        return stockInfoList


    # 접속 이벤트 콜백 함수
    def on_connect(self, err_code):
        if err_code == 0:
            self.text_edit.append('Login On')
            self.kospi_market_list = self.get_MarketList('kospi')
            self.kosdaq_market_list = self.get_MarketList('kosdaq')
            self.account_num = self.kiwoom.dynamicCall("GetLoginInfo(QString)", ["ACCNO"])
            self.text_edit.append("계좌번호: " + self.account_num.rstrip(';'))
        else: 
            self.text_edit.append('Login Fail err =' +  err_code)

    # Tr 이벤트 콜백 함수
    def on_receiveTr(self, screen_no, rqname, trcode, recordname, prev_next, data_len, err_code, msg1, msg2):
        # 종목 정보 조회
        if rqname == '주식기본정보조회':
            stock_data = {}
            stock_data['name'] = self.kiwoom.dynamicCall('CommGetData(QString, QString, QString, int, QString)', trcode, '', rqname, 0, '종목명').strip()
            stock_data['volume'] = self.kiwoom.dynamicCall('CommGetData(QString, QString, QString, int, QString)', trcode, '', rqname, 0, '거래량').strip()
            stock_data['ROE'] = self.kiwoom.dynamicCall('CommGetData(QString, QString, QString, int, QString)', trcode, '', rqname, 0, 'ROE').strip()
            stock_data_json = json.dumps(stock_data, ensure_ascii=False)
            self.text_edit.append('종목정보: ' + stock_data_json)
        elif rqname == '실시간잔고':
            stock_dataList = []
            data_count = self.kiwoom.dynamicCall("GetRepeatCnt(QString, QString)", trcode, rqname)
            for i in range(data_count):
                stock_data = {}
                stock_data['code']= self.kiwoom.dynamicCall('CommGetData(QString, QString, QString, int, QString)', trcode, '', rqname, i, '종목코드')
                stock_data['name']= self.kiwoom.dynamicCall('CommGetData(QString, QString, QString, int, QString)', trcode, '', rqname, i, '종목명').strip()
                stock_data['buy_total_price']= self.kiwoom.dynamicCall('CommGetData(QString, QString, QString, int, QString)', trcode, '', rqname, i, '매입금액').strip()
                stock_data['cur_price']= self.kiwoom.dynamicCall('CommGetData(QString, QString, QString, int, QString)', trcode, '', rqname, i, '현재가').replace('-','').strip()
                stock_data['hava_count']= self.kiwoom.dynamicCall('CommGetData(QString, QString, QString, int, QString)', trcode, '', rqname, i, '보유수량').strip()
                stock_dataList.append(stock_data)
            stock_data_json = json.dumps(stock_dataList, ensure_ascii=False)
            self.text_edit.append(InsertHaveStockInfoFromJson(self.conn, stock_data_json))

if __name__ == '__main__' :
    app = QApplication(sys.argv)
    mywindow = MyWindow()
    mywindow.show()
    app.exec_()
