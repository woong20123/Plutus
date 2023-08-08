from pykiwoom.kiwoom import *
import datetime
import time
import openpyxl
import requests
import json
import os, sys
import telepot
import pprint
import logging


def send_bot_message(bot, msg):
    bot.sendMessage(chat_id=6615017798, text=msg)


# code를 종목명으로 변환합니다.
def transfer_code_to_name(kiwoom, code):
    return kiwoom.GetMasterCodeName(code)


def make_logger():
    logger = logging.getLogger(name='lionLog')
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('|%(asctime)s||%(name)s||%(levelname)s|%(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S'
                                  )
    file_handler = logging.FileHandler('lion.log', mode='w') ## 파일 핸들러 생성
    file_handler.setFormatter(formatter) ## 텍스트 포맷 설정
    logger.addHandler(file_handler) ## 핸들러 등록
    logger.addHandler(logging.StreamHandler(sys.stdout))
    return logger


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


def update_data_and_process(code_list, code, update_data, bot):
    code_data = code_list[code]
    code_data["update_datas"].append(update_data)

    if code_data["is_buy"] < 3:
        # 어제 고가 보다 가격이 높아 지면 체크
        if update_data["yesterday_high_price"] < update_data["current_price"]:
            code_data["is_buy"] += 1
            send_bot_message(bot, f'매수 포착 { update_data_to_msg(update_data) }')
    # 첫번째는 20일선이 깨지는지 먼저 체크 합니다.
    elif code_data["is_sell"] < 2:
        if update_data["current_price"] < update_data["ave20_price"]:
            code_data["is_sell"] += 1
            send_bot_message(bot, f'매도 포착 { update_data_to_msg(update_data) }')
    # 두번째는 60일선이 깨지는지 먼저 체크 합니다.
    elif code_data["is_sell"] < 3:
        if update_data["current_price"] < update_data["ave60_price"]:
            code_data["is_sell"] += 1
            send_bot_message(bot, f'매도 포착 { update_data_to_msg(update_data) }')


# 텔레그램 설정

token = os.getenv("TELE_TOKEN")
bot = telepot.Bot(token)

logger = make_logger()

cur_date = datetime.datetime.now().date()

# 로그인 
kiwoom = Kiwoom()
kiwoom.CommConnect(block=True)

codeList = {
    "304100": None,
    "028050": None,
    "060370": None,
    "067900": None,
    "326030": None,
    "049520": None,
    "110990": None,
    "950140": None,
}

# 하루 총 390분
# 11시 이후 전날 고점을 기준으로 합니다.

delay_per_code = 3.0
start_time = 90000

send_bot_message(bot, f'{cur_date}의 주식 자동 감시를 시작 합니다.')
logger.info(f'{cur_date}의 주식 자동 감시를 시작 합니다.')

logger.info(f'[감시 목록]')
for i, code in enumerate(codeList.keys()):
    codeList[code] = {"update_datas": [], "is_buy": 0, "is_sell": 0}
    logger.info(f' - {transfer_code_to_name(kiwoom, code)}')

run_count = 0
while run_count < 300:
    now = datetime.datetime.now()
    remain_sleep = 59.5

    logger.info(f'현재 시간 : {now}')
    logger.info(f'접속 상태 : {check_connect_state(kiwoom)}')

    if now.hour not in [9, 10, 11, 12, 13, 14, 15, 23]:
        logger.info(f'아직 수행 시간이 아닙니다.')
        time.sleep(remain_sleep)
        continue

    # 1분 마다 해당 code들의 정보를 가져와서 동기화 합니다.
    for i, code in enumerate(codeList.keys()):
        logger.info(f"{i+1}/{len(codeList)} {transfer_code_to_name(kiwoom, code)}")
        df = kiwoom.block_request("opt10080",
                                  종목코드=code,
                                  틱범위="1",
                                  output="주식분봉차트조회",
                                  next=0)

        df2 = df.apply(pd.to_numeric)
        df2 = df2.abs()
        request_day = int(df2.iloc[0]["체결시간"] / 1000000)
        request_time = int(df2.iloc[0]["체결시간"] % 1000000)
        current_price = int(df2.iloc[0]["현재가"])
        ave5_price = int(df2["현재가"][:5].sum() / 5)
        ave10_price = int(df2["현재가"][:10].sum() / 10)
        ave20_price = int(df2["현재가"][:20].sum() / 20)
        ave60_price = int(df2["현재가"][:60].sum() / 60)

        today_elapsed_min = int((request_time - start_time) / 10000) * 60 + int((request_time - start_time) / 100 % 100)
        yesterday_high_price = int(df2["고가"][:270 + today_elapsed_min].max())

        update_data = {
            "name": transfer_code_to_name(kiwoom, code),
            "request_day": request_day,
            "request_time": request_time,
            "current_price": current_price,
            "ave5_price": ave5_price,
            "ave10_price": ave10_price,
            "ave20_price": ave20_price,
            "ave60_price": ave60_price,
            "yesterday_high_price": yesterday_high_price,
        }

        update_data_and_process(codeList, code, update_data, bot)

        time.sleep(delay_per_code)
        remain_sleep = remain_sleep - delay_per_code
    run_count += 1

    if 0 < remain_sleep:
        time.sleep(remain_sleep)

send_bot_message(bot, f'{cur_date}의 주식 자동 감시를 종료 합니다.')
logger.info(f'{cur_date}의 주식 자동 감시를 종료 합니다.')

# 컴퓨터를 종료 합니다.
os.system('shutdown -s -f')
