import json

from pykiwoom.kiwoom import *
import datetime
import time
import os
import sys
import logging
import my_telegram as telegram
import my_mongo
import numpy


# code를 종목명으로 변환합니다.
def transfer_code_to_name(kiwoom, code):
    return kiwoom.GetMasterCodeName(code)


def make_logger():
    log_instance = logging.getLogger(name='make_one_minute')
    log_instance.setLevel(logging.INFO)
    formatter = logging.Formatter('|%(asctime)s||%(name)s||%(levelname)s|%(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S'
                                  )
    file_handler = logging.FileHandler('log/make_lion.log', mode='w+')  ## 파일 핸들러 생성
    file_handler.setFormatter(formatter)  ## 텍스트 포맷 설정
    log_instance.addHandler(file_handler)  ## 핸들러 등록
    log_instance.addHandler(logging.StreamHandler(sys.stdout))
    return log_instance


# 연결 상태 정보를 확인 합니다.
def check_connect_state(kiwoom):
    connect_state = ["미연결", "연결"]
    return connect_state[kiwoom.GetConnectState()]


def update_data_to_msg(update_data):
    return (f'이름 : {update_data["name"]}\n'
            f'현재가 : {update_data["current_price"]}원\n'
            f'10선 : {update_data["ave10_price"]}원\n'
            f'20선 : {update_data["ave20_price"]}원\n'
            f'60선 : {update_data["ave60_price"]}원\n')



if __name__ == "__main__":
    # 텔레그램 설정
    bot = telegram.getBot()
    # logger 생성
    logger = make_logger()

    # 로그인
    kiwoom = Kiwoom()
    kiwoom.CommConnect(block=True)

    codeList = {
        "095340": None,
        "028050": None,
        "006730": None,
        "018290": None,
        "069460": None,
        "071970": None,
        "208370": None,
        "257720": None,
        "335890": None,
        "014620": None,
        "033100": None,
        "066910": None,
        "018290": None,
        "056080": None,
    }

    # 하루 총 390분
    # 11시 이후 전날 고점을 기준으로 합니다.
    start_time = 90000
    make_date = 230810
    collection_name = 'one_minute'

    stock_db = my_mongo.get_database("stock")

    logger.info(f'{make_date}의 주식 데이터를 생성합니다')

    logger.info(f'[감시 목록]')
    for i, code in enumerate(codeList.keys()):
        codeList[code] = {"update_datas": [], "is_buy": 0, "is_sell": 0}
        logger.info(f' - {transfer_code_to_name(kiwoom, code)}')

    for i, code in enumerate(codeList.keys()):
        logger.info(f"{i + 1}/{len(codeList)} {transfer_code_to_name(kiwoom, code)}")
        df = kiwoom.block_request("opt10080",
                                  종목코드=code,
                                  틱범위="1",
                                  output="주식분봉차트조회",
                                  next=0)

        df2 = df.apply(pd.to_numeric)
        df2 = df2.abs()
        request_day = int(df2.iloc[0]["체결시간"] / 1000000)
        request_time = int(df2.iloc[0]["체결시간"] % 1000000)
        cur_price = int(df2["현재가"][0])
        yesterday_prices = df2["현재가"][:60].tolist()
        today_elapsed_min = int((request_time - start_time) / 10000) * 60 + int((request_time - start_time) / 100 % 100) - 90
        high_price = int(df2["고가"][:today_elapsed_min].max())
        ave5_price = int(df2["현재가"][:5].sum() / 5)
        ave10_price = int(df2["현재가"][:10].sum() / 10)
        ave20_price = int(df2["현재가"][:20].sum() / 20)
        ave60_price = int(df2["현재가"][:60].sum() / 60)
        past_ave_volume = int(numpy.mean(df2["거래량"]))

        stock_data = {
            "code": code,
            "name": transfer_code_to_name(kiwoom, code),
            "date": make_date,
            "last_update" : start_time,
            "prices": [],
            "cur_price": cur_price,
            "yesterday_high_price": high_price,
            "high_price": high_price,
            "volumes" : [],
            "tick_volume" : 0,
            "total_volume": 0,
            "last_total_volume" : 0,
            "ave5_price": ave5_price,
            "ave10_price": ave10_price,
            "ave20_price": ave20_price,
            "ave60_price": ave60_price,
            "past_ave_volume": past_ave_volume,
            "buy_check": 0,
            "sell_check": 0,
        }

        # 데이터를 mongoDB에 저장합니다.
        key = {"code": code, "date" : make_date}
        my_mongo.upsert_to_database(stock_db, collection_name, key, stock_data)
        logger.info(f"mongo db에 데이터 저장  key : {key}, data : {json.dumps(stock_data)}")

    logger.info(f'{make_date}의 주식 데이터를 생성을 완료 하였습니다.')