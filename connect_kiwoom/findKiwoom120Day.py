#-*-coding:utf-8 -*-

# python.exe -m pip install future-fstrings 설치 필요

import sys
import os
import random
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
import csv
from time import sleep

import json
from PyQt5.QAxContainer import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from connect_sqlite.ConnectSqlite import *
from connect_sqlite.SqliteLogic import *

# 이평선을 구합니다. 
def make_movin_average_line(arr, start_index, term) : 
    if term == 0 :
        return 0
    total = 0
    for i in range(0, term) :
        total += arr[start_index + i]
    return total / term

def get_rate_of_rise(arr, date) : 
    get_stock_info = None
    yesterday_price = 0
    yesterday_index = 0
    for stock_info in arr[:-2] :
        yesterday_index += 1
        if( stock_info['date'] == date) :
            get_stock_info = stock_info
            yesterday_price = arr[yesterday_index]['cur_price']
            break;

    if get_stock_info == None :
        return 0

    diff_price = get_stock_info['cur_price'] - yesterday_price;
    return (diff_price / yesterday_price) * 100


# 최근 거래량이 많았던 적이 있는지 체크합니다.
def find_highvolume(arr, start_index, term) : 
    high_volume = None
    avg_volume = None
    if term == 0 :
        return False, high_volume, avg_volume

    arr_volume_sort = sorted(arr[start_index:start_index+term], key=lambda x : (-x['cur_volume']))

    high_volume = arr_volume_sort[0]

    avg_sum_volume = 0
    for value in arr_volume_sort[2:] :
        avg_sum_volume += value['cur_volume']

    avg_volume = avg_sum_volume/len(arr_volume_sort[2:])

    if avg_volume < 5000 : 
        return False, high_volume, avg_volume

    if high_volume['cur_volume'] > avg_volume * 4 :
        return True, high_volume, avg_volume
    return False, high_volume, avg_volume

# 2일간 거래량이 줄고 있는지 체크
def check_volume_down(arr, start_index, avg_volume) : 
    today_vol = arr[start_index]['cur_volume']
    one_before_day_vol = arr[start_index+1]['cur_volume']
    two_before_day_vol = arr[start_index+2]['cur_volume']

    is_continue_down = False
    is_avg_volume_than_down = False

    if today_vol < one_before_day_vol and one_before_day_vol < two_before_day_vol :
        is_continue_down = True

    if  avg_volume != None and today_vol < avg_volume and one_before_day_vol < avg_volume and two_before_day_vol < avg_volume :
        is_avg_volume_than_down = True
        
    
    return is_continue_down, is_avg_volume_than_down

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

        self.index_text_edit = QLineEdit(self)
        self.index_text_edit.move(10, 20)
        self.index_text_edit.setText('0')

        ######## [버튼] ########

        # 버튼 
        findbtn = QPushButton('조회', self)
        findbtn.move(200, 20)
        findbtn.clicked.connect(self.findbtn_clicked)


        self.listWidget = QListWidget(self)
        self.listWidget.setGeometry(30, 60, 270, 150)

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

        self.day_chart_query('20210316', start_idx)
            
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

                for i in range(0, stock_info_len) :
                    result, day = self.check_day_logic(stock_data, i)
                    check_ok = result[0]
                    date = result[1]
                    file_name = "day_result_" + str(date) + "_" + str(day) + ".txt"
                    if check_ok :
                        self.logic_120day_result[code] = stock_data
                        msg = f"['{str(date)}']['{str(day)}'로직] : '{str(self.day_chart_query_idx)}' = '{self.getStockName(code)}'"
                        self.listWidget.addItem(msg)                        
                        with open('result/' + file_name, "a") as f:
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
    
    # 120일선 체크 로직 
    def check_day_logic(self, stock_data, stock_info_index) :
        cur_stockinfo = stock_data['stock_info'][stock_info_index]
        date = int(cur_stockinfo['date'])
        cur_price = int(cur_stockinfo['cur_price'])
        cur_high_price = int(cur_stockinfo['high_price'])
        cur_low_price = int(cur_stockinfo['low_price'])
        yesterday_price = int(stock_data['stock_info'][stock_info_index+1]['cur_price'])
        yesterday_high_price = int(stock_data['stock_info'][stock_info_index+1]['high_price'])
        yesterday_low_price = int(stock_data['stock_info'][stock_info_index+1]['low_price'])
        before_2day_start_price = int(stock_data['stock_info'][stock_info_index+2]['start_price'])
        result_fail = (False, date)
        result_success = (True, date)
        
        # 거래량 체크
        ishighvolume, high_volume_stock_info, avg_volume = find_highvolume(stock_data['stock_info'], stock_info_index, 15)
        if False == ishighvolume:
            return result_fail, 0

        is_continue_down, is_avg_volume_than_down = check_volume_down(stock_data['stock_info'], stock_info_index, avg_volume)
    
        if False == is_avg_volume_than_down and False == is_continue_down :
             return result_fail, 0

        ma_line_10 =  make_movin_average_line(stock_data['cur_prices'], stock_info_index, 10)
        ma_line_20 =  make_movin_average_line(stock_data['cur_prices'], stock_info_index, 20)
        ma_line_60 =  make_movin_average_line(stock_data['cur_prices'], stock_info_index, 60)
        ma_line_120 =  make_movin_average_line(stock_data['cur_prices'], stock_info_index, 120)

        if False == (ma_line_20 > ma_line_60 and ma_line_60 > ma_line_120) :
            return result_fail, 0

        # 120일 선 체크
        # if (cur_price * 1.02 > ma_line_120 and ma_line_120 > cur_price * 0.995) and ( yesterday_price > ma_line_120) :
        #     return result_success, 120

        # 60일 선 체크
        # if (cur_price * 1.02 > ma_line_60 and ma_line_60 > cur_price * 0.995) and ( yesterday_price > ma_line_60) :
        #     return result_success, 60

        high_v_rate_rise = get_rate_of_rise(stock_data['stock_info'], high_volume_stock_info['date'])
        

        # 20일 선 체크
        diff_10_20 = ma_line_10 - ma_line_20
        diff_20_60 = ma_line_20 - ma_line_60
        # if (cur_price < ma_line_10 and cur_price > ma_line_20) and ( yesterday_price > ma_line_20) and (high_v_rate_rise > 10)  :
        #     if ( ma_line_10 > ma_line_20 * 1.02 ) and ( diff_10_20 > diff_20_60 / 3.5 ):
        if (cur_price < ma_line_10 and cur_price > ma_line_20) and ( yesterday_price > ma_line_20) and (high_v_rate_rise > 10)  :
            if ( ma_line_10 > ma_line_20 * 1.01 ) and ( diff_10_20 > diff_20_60 / 4 ):
                return result_success, 20

        if (cur_price > ma_line_10 and yesterday_price > ma_line_10) and ( True == is_continue_down) and before_2day_start_price > cur_low_price and (cur_price < ma_line_10 * 1.04) :
            if ( cur_high_price > yesterday_high_price * 0.992) and ( cur_high_price < yesterday_high_price * 1.008) and (ma_line_10 > ma_line_20) :
                if ( cur_low_price > yesterday_low_price * 0.992) and ( cur_low_price < yesterday_low_price * 1.008) :
                    return result_success, 10

        return result_fail, 0

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
