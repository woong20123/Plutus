import logging
import sys
from PyQt5.QtWidgets import *
from PyQt5.QAxContainer import *
import datetime
import my_telegram as telegram
from datetime import datetime

import py_trade_util as ptutil
import my_mongo
import json
import random
import numpy
from enum import Enum
import time as t


class Static(Enum):
    # 10시 30분
    STRATEGY_3MINUTE_CHECK_START_TIME = 103000


class Strategy(Enum):
    FIRST = 0
    SECOND = 1
    THIRD = 2


def make_logger():
    log_name = 'one_minute'
    log_instance = logging.getLogger(name=log_name)
    log_instance.setLevel(logging.DEBUG)
    formatter = logging.Formatter('|%(asctime)s||%(name)s||%(levelname)s|%(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S'
                                  )
    file_handler = logging.FileHandler('log/' + log_name + '_' + make_now_yymmdd() + '.log')  ## 파일 핸들러 생성
    file_handler.setFormatter(formatter)  ## 텍스트 포맷 설정
    log_instance.addHandler(file_handler)  ## 핸들러 등록
    log_instance.addHandler(logging.StreamHandler(sys.stdout))
    return log_instance


def make_code_list_str(code_list):
    result = ""
    for s in code_list:
        result += s + ";"
    return result.strip()[:-1]


def make_now_yymmdd():
    return datetime.today().strftime('%Y-%m-%d')


def make_now_hhmmss():
    return datetime.today().strftime("%H%M%S")


def one_minute_data_to_msg(one_minute_data):
    return (f'이름 : {one_minute_data["name"]}\n'
            f'현재가 : {one_minute_data["cur_price"]}원\n')


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
        self.update_time_per_minute = 90100
        self.setWindowTitle("real_one_minute")
        self.setGeometry(300, 300, 300, 400)

        # telegram bot 생성
        self.bot = telegram.getBot()
        # logger 생성
        self.logger = make_logger()
        # mongoDB 생성
        self.stock_db = my_mongo.get_database("stock")
        self.tracking_code_list = ptutil.Common.TRACKING_CODE_LIST.value
        self.traking_date = ptutil.Common.TRACKING_DATE.value
        self.trade_start_time = 90000
        self.collection_name = 'one_minute'
        self.log_collection_name = 'one_minute_log'

        register_btn = QPushButton("Register", self)
        register_btn.move(20, 20)
        register_btn.clicked.connect(self.register_btn_clicked)

        disconnect_btn = QPushButton("DisConnect", self)
        disconnect_btn.move(20, 100)
        disconnect_btn.clicked.connect(self.disconnect_btn_clicked)

        self.is_test = False
        btn_test = QPushButton("Test Run", self)
        btn_test.move(20, 150)
        btn_test.clicked.connect(self.bnt_test_clicked)

        btn_test = QPushButton("Test Date Clear", self)
        btn_test.move(20, 200)
        btn_test.clicked.connect(self.bnt_test_data_clear_clicked)

        self.ocx = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")
        self.ocx.OnEventConnect.connect(self._handler_login)
        self.ocx.OnReceiveRealData.connect(self._handler_real_data)
        self.CommmConnect()

    def data_update(self, real_data):
        code = real_data["code"]
        time = real_data["time"]
        one_minute = self.one_minutes[code]
        one_minute["cur_price"] = real_data["cur_price"]
        one_minute["last_update"] = real_data["time"]
        one_minute["total_volume"] = real_data["total_volume"]

        # high_price 가격 갱신
        if one_minute["high_price"] < real_data["cur_price"]:
            one_minute["high_price"] = real_data["cur_price"]

        # today_high_price 가격 갱신
        # 10시 30분 이전에 고점만 갱신합니다 - 3minute 전략
        if (one_minute["today_high_price"] < real_data["cur_price"] and
                time <= Static.STRATEGY_3MINUTE_CHECK_START_TIME.value):
            one_minute["today_high_price"] = real_data["cur_price"]

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

    def strategy_default(self, one_minute):
        self.logger.info(f'run strategy_default')

        last_volume = one_minute['volumes'][-1]
        ave_volume = numpy.mean(one_minute['volumes']) + one_minute["past_ave_volume"]

        if one_minute["buy_check"][Strategy.FIRST.value] < 3:
            # 전략 1
            # 로직 체크
            # 어제 고점 돌파
            # 의미 있는 거래량 증가
            # 시가 보다 높음
            # 20선이 60선보다 커야 됨
            if (one_minute["yesterday_high_price"] < one_minute["cur_price"] and (ave_volume * 2) < last_volume
                    and one_minute['ave20_price'] < one_minute["cur_price"]
                    and one_minute['ave60_price'] < one_minute["ave20_price"]
                    and one_minute['start_price'] < one_minute["cur_price"]):
                one_minute["buy_check"][Strategy.FIRST.value] += 1
                telegram.send_bot_message(self.bot,
                                          f'[매수 포착][어제 고점 - 거래량 - 시가] buy_check:{one_minute["buy_check"][Strategy.FIRST.value]},'
                                          f' {one_minute_data_to_msg(one_minute)}')

        # 1회라도 매수가 체크 되었으면 sell 로직을 체크 합니다.
        if 1 < one_minute["buy_check"][Strategy.FIRST.value]:
            # 전략 1 최근 15분봉의 상승 추세 확인
            # long 점수가 0보다 작거나(or) short 점수가 long 점수보다 작을 때 추세가 꺽인 걸로 확인
            if one_minute["sell_check"][Strategy.FIRST.value] < 2:
                serialize_price_score_long = get_score_serialize_price(one_minute['prices'], 15)
                serialize_price_score_short = get_score_serialize_price(one_minute['prices'], 7)
                if serialize_price_score_short < 0 or serialize_price_score_short < serialize_price_score_long:
                    one_minute["sell_check"][Strategy.FIRST.value] += 1
                    telegram.send_bot_message(self.bot,
                                              f'[매도 포착][15분봉의 하락 추세] sell_count:{one_minute["sell_check"][Strategy.FIRST.value]}, {one_minute_data_to_msg(one_minute)}')

            # 전략 2 20선이 깨지는지 체크 합니다.
            if one_minute["sell_check"][Strategy.SECOND.value] < 1:
                if one_minute["cur_price"] < one_minute["ave20_price"] and int(ave_volume / 2) < last_volume:
                    one_minute["sell_check"][Strategy.SECOND.value] += 1
                    telegram.send_bot_message(self.bot,
                                              f'[매도 포착][20일선 추락] sell_count:{one_minute["sell_check"][Strategy.SECOND.value]}, {one_minute_data_to_msg(one_minute)}')

            # 전략 3 60선이 깨지는지 먼저 체크 합니다.
            if one_minute["sell_check"][Strategy.THIRD.value] < 1:
                if one_minute["cur_price"] < one_minute["ave60_price"]:
                    one_minute["sell_check"][Strategy.THIRD.value] += 1
                    telegram.send_bot_message(self.bot,
                                              f'[매도 포착][60일선 추락] sell_check:{one_minute["sell_check"][Strategy.THIRD.value]}, {one_minute_data_to_msg(one_minute)}')

    def strategy_3minute(self, one_minute, time):
        self.logger.info(f'run strategy_3minute')

        strategy_3minute = one_minute["strategy_3minute"]

        if time < Static.STRATEGY_3MINUTE_CHECK_START_TIME.value:
            self.logger.info(f'run strategy_3minute not time yet. time: {time}')
            return

        for key in ["buy_check", "buy_send", "sell_check", "sell_send"]:
            if strategy_3minute.get(key) is None:
                strategy_3minute[key] = 0

        if 0 == strategy_3minute["buy_send"]:
            # [매수 로직 체크]
            # 당일 고점과 현재 가격을 비교 합니다.
            if (one_minute["today_high_price"] < one_minute["cur_price"] and
                    one_minute["ave180_price"] < one_minute["cur_price"]):
                strategy_3minute["buy_check"] += 1
                if strategy_3minute["buy_check"] == 2:
                    telegram.send_bot_message(self.bot,
                                              f'[매수][{ptutil.num_time_to_str(time)}][3minute]고점 돌파 준비\n'
                                              f'{one_minute_data_to_msg(one_minute)}'
                                              f'당일 고점 : {one_minute["today_high_price"]}원\n'
                                              f'40선:{one_minute["ave120_price"]}원\n'
                                              f'2% 가격 : {int(one_minute["cur_price"] * 0.02)}원')
            else:
                strategy_3minute["buy_check"] = 0

        if 1 == strategy_3minute["buy_send"] and 0 == strategy_3minute["sell_send"]:
            # [매도 로직 체크]
            # 3분봉 40선(1분 120선) 보다 현재가가 작아지면 체크합니다.
            if one_minute["cur_price"] <= one_minute["ave120_price"]:
                strategy_3minute["sell_check"] = 1

        # buy_check가 2번이상 연속으로 체크되면 메시지를 보냅니다.
        if 3 <= strategy_3minute["buy_check"]:
            strategy_3minute["buy_check"] = 0
            strategy_3minute["buy_send"] = 1
            telegram.send_bot_message(self.bot,
                                      f'[매수][{ptutil.num_time_to_str(time)}][3minute]고점 돌파 확인\n'
                                      f'{one_minute_data_to_msg(one_minute)}'
                                      f'당일 고점 : {one_minute["today_high_price"]}원\n'
                                      f'40선:{one_minute["ave120_price"]}원\n'
                                      f'2% 가격 : {int(one_minute["cur_price"] * 0.02)}원')

        # sell_check가 발견되면 메시지를 보냅니다.
        if 1 == strategy_3minute["sell_check"]:
            strategy_3minute["sell_check"] = 0
            strategy_3minute["sell_send"] = 1
            telegram.send_bot_message(self.bot,
                                      f'[매도][{ptutil.num_time_to_str(time)}][3minute]40선 추락\n'
                                      f'{one_minute_data_to_msg(one_minute)}'
                                      f'40선:{one_minute["ave120_price"]}원\n')

    def per_one_minute_logic(self, time):
        # 1분 간격으로 체크 하는 로직입니다.
        if time <= self.update_time_per_minute:
            return

        while self.update_time_per_minute < time:
            self.update_time_per_minute = ptutil.num_time_add(self.update_time_per_minute, 100)

        diff_minute = ptutil.num_time_to_minute(ptutil.num_time_sub(self.update_time_per_minute, self.trade_start_time))

        self.logger.info(
            f'per_one_minute_logic, update_time_per_minute:{self.update_time_per_minute}, diff_minute :{diff_minute}')

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
            one_minute['ave120_price'] = self.make_average(120, one_minute['prices'], one_minute['yesterday_prices'])
            one_minute['ave180_price'] = self.make_average(180, one_minute['prices'], one_minute['yesterday_prices'])

            self.logger.info(
                f'make ave, name:{one_minute["name"]}, ave5:{one_minute["ave5_price"]}, '
                f'ave10:{one_minute["ave10_price"]}, ave20:{one_minute["ave20_price"]}, '
                f'ave60:{one_minute["ave60_price"]}, ave120:{one_minute["ave120_price"]}, '
                f'ave180_price:{one_minute["ave180_price"]}')

            if one_minute["past_ave_volume"] == 0:
                one_minute["past_ave_volume"] = int(numpy.mean(one_minute['volumes']))

            # 3분 전략 수행
            if diff_minute % 3 == 1:
                self.strategy_3minute(one_minute, time)

            # default 전략 수행 - 일단 보류, 로직 참고용
            # self.strategy_default(one_minute)

            # mongoDB 업데이트 수행
            key = {"code": code, "date": self.traking_date}
            my_mongo.upsert_to_database(self.stock_db, self.collection_name, key, one_minute)

            # mongoDB log collect에 업데이트 수행
            log_key = {"code": code, "date": self.traking_date, "time": self.update_time_per_minute}
            one_minute_log = one_minute.copy()
            one_minute_log["time"] = self.update_time_per_minute
            one_minute_log.pop("_id")
            one_minute_log.pop("yesterday_prices")
            one_minute_log.pop("prices")
            one_minute_log.pop("volumes")
            one_minute_log.pop("tick_volume")
            my_mongo.upsert_to_database(self.stock_db, self.log_collection_name, log_key, one_minute_log)

    def make_code_data(self):
        self.one_minutes = {}

        if ptutil.isTradingTime():
            cur_time = int(make_now_hhmmss())
            self.update_time_per_minute = cur_time - (cur_time % 100) + 100

        self.logger.info(f'version: {ptutil.version()} traking_date: {self.traking_date} ')
        self.logger.info(f'update_time_per_minite : {self.update_time_per_minute}')
        self.logger.info(f'[감시 목록]')
        for code in self.tracking_code_list:
            # mongo에서 데이터 가져오기
            self.one_minutes[code] = my_mongo.find_one_to_database(self.stock_db, self.collection_name,
                                                                   {"code": code, "date": self.traking_date})

            if self.one_minutes[code].get("yesterday_prices") is None:
                self.one_minutes[code]["yesterday_prices"] = [self.one_minutes[code]["cur_price"]]
            # 데이터 보정
            if self.one_minutes[code].get("yesterday_high_price") is None:
                self.one_minutes[code]["yesterday_high_price"] = self.one_minutes[code]["high_price"]

            if self.one_minutes[code].get("volumes") is None:
                self.one_minutes[code]['volumes'] = []

            for key in ["tick_volume", "total_volume", "last_total_volume", "past_ave_volume", "start_price",
                        "today_high_price"]:
                if self.one_minutes[code].get(key) is None:
                    self.one_minutes[code][key] = 0

            for key in ["strategy_3minute"]:
                if self.one_minutes[code].get(key) is None:
                    self.one_minutes[code][key] = {}

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

            # self.logger.debug(f' log real_date : {json.dumps(real_data)}')

            self.data_update(real_data)
            self.per_one_minute_logic(int(real_data["time"]))

    def register_btn_clicked(self):
        code_list_str = make_code_list_str(self.tracking_code_list)
        self.SetRealReg("1000", code_list_str, "20;10;27;28;13;16;17;18;851", "0")

        telegram.send_bot_message(self.bot, f'one_minute 구독을 시작 합니다.')
        self.logger.info(f'구독 신청 완료.')

    def disconnect_btn_clicked(self):
        self.DisConnectRealData("1000")
        telegram.send_bot_message(self.bot, f'one_minute 구독을 종료 합니다.')
        self.logger.info(f'구독 해지 완료.')

    def bnt_test_clicked(self):
        self.logger.info(f'테스트 로직 is_test : {self.is_test}')

        if self.is_test:
            self.traking_date = ptutil.Common.TRACKING_DATE.value
            self.update_time_per_minute = 90100
            real_data = {
                "code": "071970",
                "time": 90001,  # 체결 시간
                "cur_price": 12490,  # 현재가
                "sell_quote": 0,  # 매도호가
                "buy_quote": 0,  # 매수호가
                "volume": 3790,  # 거래량
                "total_volume": 37900,  # 누적 거래량
                "start_price": 12500,  # 시가
                "high_price": 12700,  # 고가
                "low_price": 12400,  # 저가
                "volume_ratio": 0,  # 전일비 거래량 비율
            }

            for time in range(90001, 150001, 100):

                time_hour = int(time / 10000)
                time_minute = int(time / 100) % 100
                if time_minute > 60:
                    continue

                random_value = 50
                if time_hour == 11 or time_hour == 12:
                    random_value = 70
                if time_hour == 13 or time_hour == 14:
                    random_value = 30

                real_data["time"] = time
                diff_price = int(real_data["cur_price"] * 0.001) * random.randrange(1, 3)
                if random.randrange(1, 100) < random_value:
                    real_data["cur_price"] += diff_price
                    self.logger.info(f'test data plus')
                else:
                    real_data["cur_price"] -= diff_price
                    self.logger.info(f'test data sub')

                self.logger.info(
                    f'test data -> time:{real_data["time"]}, cur_price:{real_data["cur_price"]}, diff_price:{diff_price}, time_hour:{time_hour}')
                self.data_update(real_data)
                self.per_one_minute_logic(int(real_data["time"]))
                t.sleep(0.1)

    def bnt_test_data_clear_clicked(self):
        self.logger.info(f'테스트 Data Clear is_test : {self.is_test}')

        if self.is_test:
            # mongoDB delete 수행
            test_key = {"date": 230808}

            my_mongo.delete_many_database(self.stock_db, self.collection_name, test_key)
            my_mongo.delete_many_database(self.stock_db, self.log_collection_name, test_key)


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
