#-*-coding:utf-8 -*-

# python.exe -m pip install future-fstrings 설치 필요

import sys
import os
import random

from logic.DailyLeaderStockLogic import DailyLeaderStockLogic
from logic.BaseLogic import BaseLogic
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
import csv
from time import sleep

from datetime import datetime
import json
from PyQt5.QAxContainer import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from connect_sqlite.ConnectSqlite import *
from connect_sqlite.SqliteLogic import *

class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Plutus')
        self.setGeometry(200, 200, 1200, 800)

        # 키움 OpenAPI 라이브러리 추가 
        self.kiwoom = QAxWidget('KHOPENAPI.KHOpenAPICtrl.1') 

        self.text_edit = QTextEdit(self)
        self.text_edit.setGeometry(10, 260, 560, 200)
        self.text_edit.setEnabled(False)

        label = QLabel('인덱스 : ', self)
        label.setGeometry(10, 20, 40, 20)
        self.index_text_edit = QLineEdit(self)
        self.index_text_edit.move(70, 20)
        self.index_text_edit.setText('0')

        label = QLabel('날짜 : ', self)
        label.setGeometry(10, 70, 40, 20)
        self.date_text_edit = QLineEdit(self)
        self.date_text_edit.move(70, 70)
        self.date_text_edit.setText(datetime.today().strftime("%Y%m%d"))

        # 로직 정보 셋팅
        self.LogicDic = { "BaseLogic" : BaseLogic(), "DailyLeaderStockLogic" : DailyLeaderStockLogic() }
        self.logicSelector = QListWidget(self)
        self.logicSelector.setGeometry(10, 120, 100, 80)
        for logic_name, _ in self.LogicDic.items() :
            self.logicSelector.addItem(logic_name)

        ######## [버튼] ########

        # 버튼 
        findbtn = QPushButton('조회', self)
        findbtn.move(200, 20)
        findbtn.clicked.connect(self.findbtn_clicked)


        self.listWidget = QListWidget(self)
        self.listWidget.setGeometry(200, 80, 470, 150)

        # sqlite conn
        self.conn = SqliteConn(os.getcwd() + '/DataBase/Plutus.sqlite3')

        self.logic_120day_result = {};


        # 콜백이벤트 등록
        self.kiwoom.OnEventConnect.connect(self.on_connect)
        self.kiwoom.OnReceiveTrData.connect(self._on_receiveTr)

        self.comm_connect();

    def __del__(self):
        self.conn.close()

    def getStockName(self, code) : 
        if code in self.stockInfo_list : 
            return self.stockInfo_list[code];
        return "";

    def comm_connect(self):
        self.kiwoom.dynamicCall("CommConnect()")
        self.kiwoom.login_event_loop = QEventLoop()
        self.kiwoom.login_event_loop.exec_()

    # 검색용 버튼 클릭 이벤트 함수
    def findbtn_clicked(self):
        # 초기화
        self.logic_120day_result = {}

        start_idx = int(self.index_text_edit.text())
        date = self.date_text_edit.text()


        self.day_chart_query(date, start_idx)

    def getLogic(self) :
        return self.LogicDic.get(self.logicSelector.currentItem().text())

    def getLogicName(self) :
        return self.logicSelector.currentItem().text()
        
            
    # opt10081 : 주식 일봉 차트 조회 요청 
    def day_chart_query(self, date, start_idx) :

        with open("plog.log", "a") as f:
            f.writelines(f"day_chart_query start start_idx('{start_idx}')\n")

        stockInfo_list_size = len(self.stockInfo_list)
        self.day_chart_query_idx = 0
        for code, name in self.stockInfo_list.items():
            self.day_chart_query_idx += 1;

            if self.day_chart_query_idx % 100 == 0 : 
                with open("plog.log", "a") as f:
                    f.writelines(f"day_chart_query call : '{self.day_chart_query_idx}'\n")                    

            if code == "" : 
                continue
            if self.day_chart_query_idx < start_idx  :
                continue

            ignore_check = False
            for check_name in ['(H)', 'TIGER ', 'KODEX ', 'ARIRANG ', 'KINDEX ', 'KBSTAR ', 'KOSEF ', ' ETN', 'HANARO ', 'KOSDAQ ', 'ARIRANG '] :
                if  check_name in name : 
                    print("day_chart_query fail name ("+ str(self.day_chart_query_idx) + "/" + str(stockInfo_list_size) + ")" + name)
                    ignore_check = True
                    break
            if ignore_check :
                continue

            self.kiwoom.dynamicCall('SetInputValue(QString, QString)', '종목코드', code)
            self.kiwoom.dynamicCall('SetInputValue(QString, QString)', '기준일자', date)
            self.kiwoom.dynamicCall('SetInputValue(QString, QString)', '수정주가구분', 1)

            self.comm_rq_data('opt10081_req', "opt10081",  0, '10081')        

            self.text_edit.append(f"day_chart_query call ('{str(self.day_chart_query_idx)}'/'{str(stockInfo_list_size)}')'{name}'")

    # opt10001 조회 
    def condition_search(self, code):
        #print('종목코드: ' + code)
        # SetInputValue
        self.kiwoom.dynamicCall('SetInputValue(QString, QString)', '종목코드', code)
        # CommRqData
        self.kiwoom.dynamicCall('CommRqData(QString, QString, int, QString)', '주식기본정보조회', 'opt10001', 0, '10001')

    # 마켓 정보 가져오기 버튼
    def getCodebtn_clicked(self):
        stockInfoList = self.get_StockListInfo(self.kospi_market_list)
        self.text_edit.append('kospi MarkerCode Count = ' +  str(len(stockInfoList)))

        # to csv 파일
        with open('C:/Users/Kim/Documents/Plutus/DataBase/StockInfo.csv','w+' , encoding='utf-8', newline='') as f :            
            writer = csv.writer(f)
            for stockInfo in stockInfoList:
                writer.writerow(stockInfo)


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
        stockInfoList = {}
        for code in stock_list :
            name = self.kiwoom.dynamicCall('GetMasterCodeName(QString)', [code])
            stockInfoList[code] = name
        return stockInfoList


    # 접속 이벤트 콜백 함수
    def on_connect(self, err_code):
        if err_code == 0:
            self.kospi_market_list = self.get_MarketList('kospi')
            self.kosdaq_market_list = self.get_MarketList('kosdaq')
            self.account_num = self.kiwoom.dynamicCall("GetLoginInfo(QString)", ["ACCNO"])
            self.text_edit.append("계좌번호: " + self.account_num.rstrip(';'))

            self.stockInfo_list = {}
            self.stockInfo_list.update(self.get_StockListInfo(self.kospi_market_list))
            self.stockInfo_list.update(self.get_StockListInfo(self.kosdaq_market_list))
        else: 
            self.text_edit.append('Login Fail err =' +  err_code)
        self.kiwoom.login_event_loop.exit()

    # Tr 이벤트 콜백 함수
    def _on_receiveTr(self, screen_no, rqname, trcode, record_name, next, unused1, unused2, unused3, unused4):
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
        elif rqname == 'opt10081_req':
            ok, code, stock_data = self._opt10081(screen_no, rqname, trcode)
            if ok : 
                stock_info_len = len(stock_data['stock_info']) - 121;

                # 150일이 넘으면 150으로 고정
                if stock_info_len > 350 : 
                    stock_info_len = 350
                
                folder_name = "result_" + self.date_text_edit.text()

                current_logic = self.getLogic()
                

                if not os.path.exists(folder_name) :
                    os.makedirs(folder_name)

                for i in range(0, stock_info_len) :
                    result, day = current_logic.check_logic(stock_data, i)
                    check_ok = result[0]
                    date = result[1]
                    file_name = self.getLogicName() + "_" + str(date) + "_" + str(day) + ".txt"
                    
                    if check_ok :
                        self.logic_120day_result[code] = stock_data
                        msg = f"['{str(date)}']['{str(day)}'로직] : '{str(self.day_chart_query_idx)}' = '{self.getStockName(code)}'"
                        self.listWidget.addItem(msg)                        
                        with open(folder_name+ '/' + file_name, "a") as f:
                            f.writelines(msg + "\n")

        try:
            self.kiwoom.tr_event_loop.exit()
        except AttributeError:
            pass

        sleep(0.6)
    
    # day_chart_query 응답 처리
    def _opt10081(self, screen_no, rqname, trcode) :
        data_count = self.kiwoom.dynamicCall("GetRepeatCnt(QString, QString)", trcode, rqname)
        code = self.kiwoom.dynamicCall('CommGetData(QString, QString, QString, int, QString)', trcode, '', rqname, 0, '종목코드').strip();  
        stock_data = {}
        self.text_edit.append("on_day_chart_query call " + self.getStockName(code))

        if data_count < 120 :
            return False, code, stock_data
        
        stock_data['stock_info'] = []
        stock_data['cur_prices'] = []
        # 데이터 전달 받기 
        for i in range(data_count):
            stock_info = {}
            stock_info['code'] = code
            stock_info['date']= self.kiwoom.dynamicCall('CommGetData(QString, QString, QString, int, QString)', trcode, '', rqname, i, '일자').strip()
            stock_info['cur_price'] = int(self.kiwoom.dynamicCall('CommGetData(QString, QString, QString, int, QString)', trcode, '', rqname, i, '현재가').replace('-','').strip())
            stock_info['high_price'] = int(self.kiwoom.dynamicCall('CommGetData(QString, QString, QString, int, QString)', trcode, '', rqname, i, '고가').replace('-','').strip())
            stock_info['low_price'] = int(self.kiwoom.dynamicCall('CommGetData(QString, QString, QString, int, QString)', trcode, '', rqname, i, '저가').replace('-','').strip())
            stock_info['start_price'] = int(self.kiwoom.dynamicCall('CommGetData(QString, QString, QString, int, QString)', trcode, '', rqname, i, '시가').replace('-','').strip())
            stock_info['cur_volume'] = int(self.kiwoom.dynamicCall('CommGetData(QString, QString, QString, int, QString)', trcode, '', rqname, i, '거래량').replace('-','').strip())
            stock_info['volume_cash'] = int(self.kiwoom.dynamicCall('CommGetData(QString, QString, QString, int, QString)', trcode, '', rqname, i, '거래대금').replace('-','').strip())

            # 거래량이 최고 일 때 종가가 최소 10% 이상 상승인지 체크하는 로직 추가
            stock_data['cur_prices'].append( int(stock_info['cur_price']))
            stock_data['stock_info'].append(stock_info)
        
        return True, code, stock_data;

    def comm_rq_data(self, rqname, trcode, next, screen_no):
        self.kiwoom.dynamicCall("CommRqData(QString, QString, int, QString", rqname, trcode, next, screen_no)
        self.kiwoom.tr_event_loop = QEventLoop()
        self.kiwoom.tr_event_loop.exec_()

    def _get_repeat_cnt(self, trcode, rqname):
        ret = self.kiwoom.dynamicCall("GetRepeatCnt(QString, QString)", trcode, rqname)
        return ret

if __name__ == '__main__' :
    app = QApplication(sys.argv)
    mywindow = MyWindow()
    mywindow.show()
    app.exec_()
