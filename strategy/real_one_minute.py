import logging
import sys
from PyQt5.QtWidgets import *
from PyQt5.QAxContainer import *
import datetime
import my_telegram as telegram
from datetime import datetime
import py_trade_util
import my_mongo
import json
import numpy


def make_logger():
    log_name = 'one_minute'
    log_instance = logging.getLogger(name=log_name)
    log_instance.setLevel(logging.DEBUG)
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


def make_now_hhmmss():
    now_time = int(datetime.today().strftime("%H%M%S"))
    return now_time


def one_minute_data_to_msg(one_minute_data):
    return (f'이름 : {one_minute_data["name"]}\n'
            f'현재가 : {one_minute_data["cur_price"]}원\n'
            f'10선 : {one_minute_data["ave10_price"]}원\n'
            f'20선 : {one_minute_data["ave20_price"]}원\n'
            f'60선 : {one_minute_data["ave60_price"]}원\n')


def get_score_serialize_price(prices, search_count):
    find_count = search_count + 1 if search_count + 1 <= len(prices) else len(prices)
    last_price = 0
    score = 0
    for i, price in enumerate(prices[-find_count:]):
        if 0 < i:
            if last_price < price:
                score += 1
            elif last_price > price:
                score -= 1
        last_price = price
    return score


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
        self.stock_db = my_mongo.get_database("stock")
        self.tracking_code_list = ["095340",
                                   "028050",
                                   "006730",
                                   "018290",
                                   "069460",
                                   "071970",
                                   "208370",
                                   "257720",
                                   "335890",
                                   "014620",
                                   "033100",
                                   "066910",
                                   "018290",
                                   "056080"]

        self.traking_date = 230810
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
        one_minute["total_volume"] = real_data["total_volume"]

        if 0 == one_minute["start_price"]:
            one_minute["start_price"] = real_data["start_price"]

        if 0 == one_minute["last_total_volume"]:
            one_minute["last_total_volume"] = real_data["total_volume"]

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
        if time <= self.update_time_per_minite:
            return

        self.update_time_per_minite += 100

        diff_time = int((self.update_time_per_minite - self.trade_start_time) / 100)
        diff_minute = int((diff_time / 100)) * 60 + diff_time % 100

        self.logger.info(
            f'per_one_minite_logic, update_time_per_minite:{self.update_time_per_minite}, diff_minute :{diff_minute}')

        # 이평선 계산 작업 수행
        for code, one_minute in self.one_minutes.items():
            one_minute['prices'].append(one_minute["cur_price"])
            # 혹시 데이터가 모자르다면 데이터를 현재가로 추가 합니다.
            while len(one_minute['prices']) < diff_minute:
                one_minute['prices'].append(one_minute["cur_price"])

            # 거래량 구하는 두번째 방법
            one_minute["tick_volume"] = one_minute["total_volume"] - one_minute["last_total_volume"]
            one_minute["last_total_volume"] = one_minute["total_volume"]

            one_minute['volumes'].append(one_minute["tick_volume"])
            while len(one_minute['volumes']) < diff_minute:
                one_minute['volumes'].append(one_minute["tick_volume"])

            # tick 데이터 초기화
            one_minute["tick_volume"] = 0

            one_minute['ave5_price'] = self.make_average(5, one_minute['prices'], one_minute['yesterday_prices'])
            one_minute['ave10_price'] = self.make_average(10, one_minute['prices'], one_minute['yesterday_prices'])
            one_minute['ave20_price'] = self.make_average(20, one_minute['prices'], one_minute['yesterday_prices'])
            one_minute['ave60_price'] = self.make_average(60, one_minute['prices'], one_minute['yesterday_prices'])

            self.logger.info(
                f'make ave, name:{one_minute["name"]}, ave5 :{one_minute["ave5_price"]}, ave10 :{one_minute["ave10_price"]}, ave20 :{one_minute["ave20_price"]}, ave60 :{one_minute["ave60_price"]}')

            # mongoDB 업데이트 수행
            key = {"code": code, "date": self.traking_date}
            my_mongo.upsert_to_database(self.stock_db, self.collection_name, key, one_minute)

            # mongoDB log collect에 업데이트 수행
            log_key = {"code": code, "date": self.traking_date, "time": self.update_time_per_minite}
            one_minute_log = one_minute.copy()
            one_minute_log["time"] = self.update_time_per_minite
            one_minute_log.pop("_id")
            one_minute_log.pop("yesterday_prices")
            one_minute_log.pop("prices")
            one_minute_log.pop("volumes")
            one_minute_log.pop("tick_volume")
            my_mongo.upsert_to_database(self.stock_db, self.log_collection_name, log_key, one_minute_log)

            if one_minute["past_ave_volume"] == 0:
                one_minute["past_ave_volume"] = numpy.mean(one_minute['volumes'])

            last_volume = one_minute['volumes'][-1]
            ave_volume = numpy.mean(one_minute['volumes']) + one_minute["past_ave_volume"]

            if one_minute["buy_check"] < 3:
                # 전략 1
                # 로직 체크
                # 어제 고점 돌파
                # 의미 있는 거래량 증가
                # 시가 보다 높음
                if (one_minute["yesterday_high_price"] < one_minute["cur_price"] and (ave_volume * 2) < last_volume
                        and one_minute['ave20_price'] < one_minute["cur_price"]
                        and one_minute['start_price'] < one_minute["cur_price"]):
                    one_minute["high_price"] = one_minute["cur_price"]
                    one_minute["buy_check"] += 1
                    telegram.send_bot_message(self.bot,
                                              f'[매수 포착][어제 고점 - 거래량 - 시가] buy_check:{one_minute["buy_check"]}, {one_minute_data_to_msg(one_minute)}')
            elif one_minute["sell_check"] < 1:
                # 전략 1 최근 15분봉의 상승 추세 확인
                serialize_price_score_long = get_score_serialize_price(one_minute['prices'], 15)
                serialize_price_score_short = get_score_serialize_price(one_minute['prices'], 7)
                if serialize_price_score_short < 0 or serialize_price_score_short < serialize_price_score_long:
                    one_minute["sell_check"] += 1
                    telegram.send_bot_message(self.bot,
                                              f'[매도 포착][15분봉의 하락 추세] sell_check:{one_minute["sell_check"]}, {one_minute_data_to_msg(one_minute)}')

                # 전략 2 20일선이 깨지는지 먼저 체크 합니다.
                if one_minute["cur_price"] < one_minute["ave20_price"] and int(ave_volume / 2) < last_volume:
                    one_minute["sell_check"] += 1
                    telegram.send_bot_message(self.bot,
                                              f'[매도 포착][20일선 추락] sell_check:{one_minute["sell_check"]}, {one_minute_data_to_msg(one_minute)}')
            # 두번째는 60일선이 깨지는지 먼저 체크 합니다.
            elif one_minute["sell_check"] < 3:
                if one_minute["cur_price"] < one_minute["ave60_price"]:
                    one_minute["sell_check"] += 1
                    telegram.send_bot_message(self.bot,
                                              f'[매도 포착][60일선 추락] sell_check:{one_minute["sell_check"]}, {one_minute_data_to_msg(one_minute)}')

    def make_code_data(self):
        self.one_minutes = {}
        cur_time = make_now_hhmmss()
        self.update_time_per_minite = cur_time - (cur_time % 100) + 100
        if self.update_time_per_minite < 90100:
            self.update_time_per_minite = 90100

        self.logger.info(f'update_time_per_minite : {self.update_time_per_minite}')

        self.logger.info(f'[감시 목록]')
        for code in self.tracking_code_list:
            # mongo에서 데이터 가져오기
            self.one_minutes[code] = my_mongo.find_one_to_database(self.stock_db, self.collection_name,
                                                                   {"code": code, "date": self.traking_date})

            # 데이터 보정
            if None == self.one_minutes[code].get("yesterday_high_price"):
                self.one_minutes[code]["yesterday_high_price"] = self.one_minutes[code]["high_price"]

            if None == self.one_minutes[code].get("volumes"):
                self.one_minutes[code]['volumes'] = []

            for key in ["tick_volume", "total_volume", "last_total_volume", "past_ave_volume", "start_price"]:
                self.one_minutes[code][key] = 0

            if len(self.one_minutes[code]["prices"]) == 0:
                self.one_minutes[code]["prices"].append(self.one_minutes[code]["cur_price"])
            self.logger.info(f' - {self.one_minutes[code]["name"]} ')

    def _handler_real_data(self, code, real_type, data):
        if real_type == "주식체결":
            real_data = {
                "code": code,
                "time": int(self.GetCommRealData(code, 20)),  # 체결 시간
                "cur_price": abs(int(self.GetCommRealData(code, 10))),  # 현재가
                "sell_quote": abs(int(self.GetCommRealData(code, 27))),  # 매도호가
                "buy_quote": abs(int(self.GetCommRealData(code, 28))),  # 매수호가
                "volume": abs(int(self.GetCommRealData(code, 15))),  # 거래량
                "total_volume": abs(int(self.GetCommRealData(code, 13))),  # 누적 거래량
                "start_price": abs(int(self.GetCommRealData(code, 16))),  # 시가
                "high_price": abs(int(self.GetCommRealData(code, 17))),  # 고가
                "low_price": abs(int(self.GetCommRealData(code, 18))),  # 저가
                "volume_ratio": abs(int(self.GetCommRealData(code, 851))),  # 전일비 거래량 비율
            }

            self.logger.info(f' log real_date : {json.dumps(real_data)}')

            self.data_update(real_data)
            self.per_one_minite_logic(int(real_data["time"]))

    def btn_clicked(self):
        code_list_str = make_code_list_str(self.tracking_code_list)
        self.SetRealReg("1000", code_list_str, "20;10;27;28;13;16;17;18;851", "0")

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
