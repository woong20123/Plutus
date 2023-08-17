import sys
import os
import numpy
import time
import logging
import my_mongo
import pandas as pd
import py_trade_util as ptutil
import my_kiwoon_util as mkutil
from pykiwoom.kiwoom import *
import json


def make_logger():
    log_name = 'make_daily'
    log_instance = logging.getLogger(name=log_name)
    log_instance.setLevel(logging.DEBUG)
    formatter = logging.Formatter('|%(asctime)s||%(name)s||%(levelname)s|%(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S'
                                  )
    file_handler = logging.FileHandler('log/' + log_name + '_' + ptutil.make_now_yymmdd() + '.log')  ## 파일 핸들러 생성
    file_handler.setFormatter(formatter)  ## 텍스트 포맷 설정
    log_instance.addHandler(file_handler)  ## 핸들러 등록
    log_instance.addHandler(logging.StreamHandler(sys.stdout))
    return log_instance


if __name__ == "__main__":
    # logger 생성
    logger = make_logger()

    # 로그인
    kiwoom = Kiwoom()
    kiwoom.CommConnect(block=True)

    search_date = 20190805
    search_end_date = 20140105
    last_code_index = 1713

    kospi_list = kiwoom.GetCodeListByMarket('0')
    kosdaq_list = kiwoom.GetCodeListByMarket('10')

    code_list = {}
    for kospi in kospi_list:
        code_list[kospi] = None

    for kosdaq in kosdaq_list:
        code_list[kosdaq] = None

    # etf, elw, 리츠 종목 제외
    etf_list = kiwoom.GetCodeListByMarket('8')
    elw_list = kiwoom.GetCodeListByMarket('3')
    reits_list = kiwoom.GetCodeListByMarket('6')


    for etf in etf_list:
        code_list.pop(etf, None)

    for elw in elw_list:
        code_list.pop(elw, None)

    for reits in reits_list:
        code_list.pop(reits, None)



    logger.info(f'make_daily 시작. version:{ptutil.version()} ')
    logger.info(f'주식 데이터를 생성합니다')

    stock_db = my_mongo.get_database("stock")
    collection_name = 'daily_data_v1'

    for code_index, code in enumerate(code_list.keys()):
        name = mkutil.transfer_code_to_name(kiwoom, code)
        logger.info(f"{code_index + 1}/{len(code_list)} 조회 시작 {name} code :{code}")

        base_date = search_date
        is_search_continue = True
        total_df = None

        if code_index < last_code_index:
            continue

        # ETN 종목을 제외합니다.
        if " ETN " in name or " ETN(H)" in name:
            logger.info(f" ETN 종목 제외 {name} code :{code}")
            continue

        # 종목의 상장일이 search_date보다 느리다면 제외
        stock_listing_date = kiwoom.GetMasterListedStockDate(code)
        nstock_listing_date = int(stock_listing_date.strftime('%Y%m%d'))
        if search_date <= nstock_listing_date:
            logger.info(f'nstock_listing_date({nstock_listing_date}) is later than search_date({search_date})')
            continue

        # 전체를 순회해서 데이터를 df에 모읍니다.
        while is_search_continue:
            logger.info(f'이름:{mkutil.transfer_code_to_name(kiwoom, code)} base_date : {base_date} 수행')
            df = kiwoom.block_request("opt10081",
                                      종목코드=code,
                                      기준일자=str(base_date),
                                      output="주식일봉차트조회",
                                      next="0")

            try:
                df2 = df.apply(pd.to_numeric)
                df2 = df2.abs()

                if total_df is None:
                    total_df = df2
                else:
                    total_df = pd.concat([total_df, df2[1:]], ignore_index=True)

                data_count = df2["현재가"].count()
                base_date = df2["일자"][data_count - 1]


                if data_count < 600 or base_date < search_end_date:
                    is_search_continue = False
            except Exception as e:
                logger.error(f'[에러 발생] 종목:{mkutil.transfer_code_to_name(kiwoom, code)}, code_index:{code_index}\n'
                             f'error {e}')
                break

            time.sleep(2.5)

        # total_df 데이터가 있다면 데이터를 가공합니다.
        # 가공한 데이터를 DB에 저장합니다.
        if total_df is not None:

            count_list = []
            for df_key in ["일자", "현재가", "시가", "고가", "저가", "거래량", "거래대금"]:
                count_list.append(total_df[df_key].count())

            # df가 가진 값중 가장 작은 index를 구합니다.
            df_count = min(count_list)

            logger.debug(f'df_count : {df_count}')

            for df_index in range(df_count - 200):
                data_date = int(total_df["일자"][df_index])

                if data_date < search_end_date:
                    #logger.debug(f'data_date({data_date})가 search_end_date({search_end_date})보다 작습니다. ')
                    continue

                cur_price = int(total_df["현재가"][df_index])
                start_price = int(total_df["시가"][df_index])
                high_price = int(total_df["고가"][df_index])
                low_price = int(total_df["저가"][df_index])
                volume = int(total_df["거래량"][df_index])
                ave5_price      = int(numpy.mean(total_df["현재가"][df_index:df_index + 5]))
                ave10_price     = int(numpy.mean(total_df["현재가"][df_index:df_index + 10]))
                ave20_price     = int(numpy.mean(total_df["현재가"][df_index:df_index + 20]))
                ave60_price     = int(numpy.mean(total_df["현재가"][df_index:df_index + 60]))
                ave120_price    = int(numpy.mean(total_df["현재가"][df_index:df_index + 120]))
                ave200_price    = int(numpy.mean(total_df["현재가"][df_index:df_index + 200]))
                ave30_volume    = int(numpy.mean(total_df["거래량"][df_index:df_index + 30]))
                ave120_volume   = int(numpy.mean(total_df["거래량"][df_index:df_index + 120]))
                cur_inc_rate    = 0 if total_df["현재가"][df_index + 1] == 0 else int((total_df["현재가"][df_index] / total_df["현재가"][df_index + 1] * 10000) - 10000)
                start_inc_rate  = 0 if total_df["시가"][df_index + 1] == 0 else int((total_df["시가"][df_index] / total_df["시가"][df_index + 1] * 10000) - 10000)
                high_inc_rate   = 0 if total_df["고가"][df_index + 1] == 0 else int((total_df["고가"][df_index] / total_df["고가"][df_index + 1] * 10000) - 10000)
                low_inc_rate    = 0 if total_df["저가"][df_index + 1] == 0 else int((total_df["저가"][df_index] / total_df["저가"][df_index + 1] * 10000) - 10000)
                volume_inc_rate = 10000 if total_df["거래량"][df_index + 1] == 0 else int((total_df["거래량"][df_index] / total_df["거래량"][df_index + 1] * 10000))

                stock_data = {
                    "code": code,
                    "date": data_date,
                    "cur_price": cur_price,
                    "start_price": start_price,
                    "high_price": high_price,
                    "low_price": low_price,
                    "volume": volume,
                    "ave5_price": ave5_price,
                    "ave10_price": ave10_price,
                    "ave20_price": ave20_price,
                    "ave60_price": ave60_price,
                    "ave120_price": ave120_price,
                    "ave200_price": ave200_price,
                    "ave30_volume": ave30_volume,
                    "ave120_volume": ave120_volume,
                    "cur_inc_rate": cur_inc_rate,
                    "start_inc_rate": start_inc_rate,
                    "high_inc_rate": high_inc_rate,
                    "low_inc_rate": low_inc_rate,
                    "volume_inc_rate": volume_inc_rate,
                }
                # 데이터를 mongoDB에 저장합니다.
                key = {"code": code, "date": data_date}
                my_mongo.upsert_to_database(stock_db, collection_name, key, stock_data)
                if df_index % 100 == 0:
                    logger.info(f"mongo db에 데이터 저장  key : {key}, data : {json.dumps(stock_data)}")
