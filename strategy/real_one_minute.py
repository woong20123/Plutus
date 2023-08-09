import logging
import sys
from PyQt5.QtWidgets import *
from PyQt5.QAxContainer import *
import datetime
import my_telegram as telegram
import time
import py_trade_util
import my_mongo
import json


def make_logger():
    log_name = 'one_minute'
    log_instance = logging.getLogger(name=log_name)
    log_instance.setLevel(logging.INFO)
    formatter = logging.Formatter('|%(asctime)s||%(name)s||%(levelname)s|%(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S'
                                  )
    file_handler = logging.FileHandler('log/' + log_name + '.log', mode='w+')  ## 파일 핸들러 생성
    file_handler.setFormatter(formatter)  ## 텍스트 포맷 설정
    log_instance.addHandler(file_handler)  ## 핸들러 등록
    log_instance.addHandler(logging.StreamHandler(sys.stdout))
    return log_instance


def make_code_list_str(code_list):
    result = ""
    for s in code_list:
        result += s + ";"
    return result.strip()[:-1]


def one_minute_data_to_msg(one_minute_data):
    return (f'이름 : {one_minute_data["name"]}\n'
            f'현재가 : {one_minute_data["cur_price"]}원\n'
            f'10선 : {one_minute_data["ave10_price"]}원\n'
            f'20선 : {one_minute_data["ave20_price"]}원\n'
            f'60선 : {one_minute_data["ave60_price"]}원\n')




class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("real_one_minute")
        self.setGeometry(300, 300, 300, 400)

        # telegram bot 생성
        self.bot = telegram.getBot()
        # logger 생성
        self.logger = make_logger()
        # mongoDB 생성
        self.stock_db = my_mongo.get_database("stock");
        self.traking_date = 230809
        self.trade_start_time = 90000
        self.collection_name = 'one_minute'
        self.log_collection_name = 'one_minute_log'

        btn = QPushButton("Register", self)
        btn.move(20, 20)
        btn.clicked.connect(self.btn_clicked)

        btn2 = QPushButton("DisConnect", self)
        btn2.move(20, 100)
        btn2.clicked.connect(self.btn2_clicked)

        self.ocx = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")
        self.ocx.OnEventConnect.connect(self._handler_login)
        self.ocx.OnReceiveRealData.connect(self._handler_real_data)
        self.CommmConnect()

    def data_update(self, real_data):
        code = real_data["code"]
        one_minute = self.one_minutes[code]
        one_minute["cur_price"] = real_data["cur_price"]
        one_minute["last_update"] = real_data["time"]
        self.logger.info(f'data_update, name:{one_minute["name"]}, time:{real_data["time"]}, cur_price:{real_data["cur_price"]}, high_price:{real_data["high_price"]}')

    def make_average(self, range, today_prices, yesterday_prices):
        ave_prices = []
        yesterday_range = range - len(today_prices) if 0 < range - len(today_prices) else 0
        today_range = range - yesterday_range

        if 0 < yesterday_range:
            for price in yesterday_prices[:yesterday_range]:
                ave_prices.append(price)

        for price in today_prices[-today_range:]:
            ave_prices.append(price)

        if range != len(ave_prices):
            self.logger.error(f'range != len(ave_prices) => {range} != {len(ave_prices)}')

        return int(sum(ave_prices) / range)

    def per_one_minite_logic(self, time):
        # 1분 간격으로 체크 하는 로직입니다.
        if time <= self.update_per_minite:
            return

        self.logger.info(
            f'run per_one_minite_logic before time : {self.update_per_minite}, after : {self.update_per_minite + 100}')
        self.update_per_minite += 100

        minute_tick_count = int((self.update_per_minite - self.trade_start_time) / 100)

        # 이평선 계산 작업 수행
        for code, one_minute in self.one_minutes.items():
            one_minute['prices'].append(one_minute["cur_price"])
            # 혹시 데이터가 모자르다면 데이터를 현재가로 추가 합니다.
            while len(one_minute['prices']) < minute_tick_count:
                one_minute['prices'].append(one_minute["cur_price"])

            one_minute['ave5_price'] = self.make_average(5, one_minute['prices'], one_minute['yesterday_prices'])
            one_minute['ave10_price'] = self.make_average(10, one_minute['prices'], one_minute['yesterday_prices'])
            one_minute['ave20_price'] = self.make_average(20, one_minute['prices'], one_minute['yesterday_prices'])
            one_minute['ave60_price'] = self.make_average(60, one_minute['prices'], one_minute['yesterday_prices'])

            # mongoDB 업데이트 수행
            key = {"code": code, "date": self.traking_date}
            my_mongo.upsert_to_database(self.stock_db, self.collection_name, key, one_minute)

            # mongoDB log collect에 업데이트 수행
            log_key = {"code": code, "date": self.traking_date, "time": self.update_per_minite}
            one_minute_log = one_minute.copy()
            one_minute_log["time"] = self.update_per_minite
            one_minute_log.pop("_id")
            my_mongo.upsert_to_database(self.stock_db, self.log_collection_name, log_key, one_minute_log)

            # 로직 체크
            if one_minute["buy_check"] < 3:
                # 어제 고가 보다 가격이 높아 지면 체크
                if one_minute["high_price"] < one_minute["cur_price"]:
                    one_minute["high_price"] = one_minute["cur_price"]
                    one_minute["buy_check"] += 1
                    telegram.send_bot_message(self.bot, f'매수 포착 {one_minute_data_to_msg(one_minute)}')
            # 첫번째는 20일선이 깨지는지 먼저 체크 합니다.
            elif one_minute["sell_check"] < 2:
                if one_minute["cur_price"] < one_minute["ave20_price"]:
                    one_minute["sell_check"] += 1
                    telegram.send_bot_message(self.bot, f'매도 포착 {one_minute_data_to_msg(one_minute)}')
            # 두번째는 60일선이 깨지는지 먼저 체크 합니다.
            elif one_minute["sell_check"] < 3:
                if one_minute["cur_price"] < one_minute["ave60_price"]:
                    one_minute["sell_check"] += 1
                    telegram.send_bot_message(self.bot, f'매도 포착 {one_minute_data_to_msg(one_minute)}')

    def make_code_data(self):
        self.tracking_code_list = ["304100", "028050", "060370", "067900", "326030", "049520", "110990", "950140"]
        self.one_minutes = {}
        self.update_per_minite = 90100
        self.logger.info(f'[감시 목록]')
        for code in self.tracking_code_list:
            # mongo에서 데이터 가져오기
            self.one_minutes[code] = my_mongo.find_one_to_database(self.stock_db, self.collection_name,
                                                                   {"code": code, "date": self.traking_date})
            if len(self.one_minutes[code]["prices"]) == 0:
                self.one_minutes[code]["prices"].append(self.one_minutes[code]["cur_price"])
            self.logger.info(f' - {self.one_minutes[code]["name"]} ')

    def _handler_real_data(self, code, real_type, data):
        if real_type == "주식체결":
            real_data = {
                "code": code,
                "time": self.GetCommRealData(code, 20),  # 체결 시간
                "cur_price": self.GetCommRealData(code, 10),  # 현재가
                "sell_quote": self.GetCommRealData(code, 27),  # 매도호가
                "buy_quote": self.GetCommRealData(code, 28),  # 매수호가
                "volume": self.GetCommRealData(code, 13),  # 누적 거래량
                "start_price": self.GetCommRealData(code, 16),  # 시가
                "high_price": self.GetCommRealData(code, 17),  # 고가
                "low_price": self.GetCommRealData(code, 18),  # 저가
                "volume_ratio": self.GetCommRealData(code, 851),  # 전일비 거래량 비율
            }

            self.data_update(real_data)
            self.per_one_minite_logic(real_data["time"])

    def btn_clicked(self):
        code_list_str = make_code_list_str(self.tracking_code_list)
        self.SetRealReg("1000", code_list_str, "20;10;27;28;13;16;17;18;851", "0")
        
        # 테스트로직
        real_data = {
            "code": "028050",
            "time": 90234,
            "cur_price": 30400,
            "sell_quote": 1,
            "buy_quote": 2,
            "volume": 200,
            "start_price": 30000,
            "high_price": 30000,
            "low_price": 30000,
            "volume_ratio": 30000,
        }

        self.data_update(real_data)
        self.per_one_minite_logic(real_data["time"])
        telegram.send_bot_message(self.bot, f'one_minute 구독을 시작 합니다.')
        self.logger.info(f'구독 신청 완료.')

    def btn2_clicked(self):
        self.DisConnectRealData("1000")
        telegram.send_bot_message(self.bot, f'one_minute 구독을 종료 합니다.')
        self.logger.info(f'구독 해지 완료.')

    def CommmConnect(self):
        self.ocx.dynamicCall("CommConnect()")
        self.statusBar().showMessage("login 중 ...")

    def _handler_login(self, err_code):
        if err_code == 0:
            self.statusBar().showMessage("login 완료")
            self.make_code_data()

    def SetRealReg(self, screen_no, code_list, fid_list, real_type):
        self.ocx.dynamicCall("SetRealReg(QString, QString, QString, QString)",
                             screen_no, code_list, fid_list, real_type)

    def DisConnectRealData(self, screen_no):
        self.ocx.dynamicCall("DisConnectRealData(QString)", screen_no)

    def GetCommRealData(self, code, fid):
        data = self.ocx.dynamicCall("GetCommRealData(QString, int)", code, fid)
        return data

    def GetMasterCordName(self, code):
        name = self.ocx.dynamicCall("GetMasterCodeName(QString)", [code])
        return name


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyWindow()
    window.show()
    app.exec_()
