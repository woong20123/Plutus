import json
import sys
import logging
import my_mongo
import py_trade_util as ptutil
import my_kiwoon_util as mkutil
from pykiwoom.kiwoom import *
import datetime


def make_logger():
    log_name = 'make_trading_day'
    log_instance = logging.getLogger(name=log_name)
    log_instance.setLevel(logging.INFO)
    formatter = logging.Formatter('|%(asctime)s||%(name)s||%(levelname)s|%(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S'
                                  )
    file_handler = logging.FileHandler('log/' + log_name + '_' + ptutil.make_now_yymmdd() + '.log')  ## 파일 핸들러 생성
    file_handler.setFormatter(formatter)  ## 텍스트 포맷 설정
    log_instance.addHandler(file_handler)  ## 핸들러 등록
    log_instance.addHandler(logging.StreamHandler(sys.stdout))
    return log_instance

def default_trading_day_data(year):
    return {
        'year': year,
        'dates': []
    }

def ntime_to_year(ntime):
    return int(ntime / 10000)

if __name__ == "__main__":
    # logger 생성
    logger = make_logger()

    stock_db = my_mongo.get_database("stock")


    daily_data_collection_name = my_mongo.CollectionInfo.DAILY_DATA.value
    trading_day_collection_name = my_mongo.CollectionInfo.TRADING_DAY.value

    make_date = [19850101, 20230812]
    make_start_date = str(make_date[0])
    make_end_date = str(make_date[1])

    start_datetime = datetime.datetime.strptime(make_start_date, "%Y%m%d")
    end_datetime = datetime.datetime.strptime(make_end_date, "%Y%m%d")
    logger.info(f'start_date : {start_datetime}')

    cur_datetime = start_datetime
    trading_day_data = default_trading_day_data(ntime_to_year(make_date[0]))

    logger.info("make_trading 작업 시작")
    logger.info(f"make_start_date:{make_start_date}, make_end_date:{make_end_date}")

    while cur_datetime <= end_datetime:
        cur_datetime += datetime.timedelta(days=1)
        ncur_time = int(cur_datetime.strftime('%Y%m%d'))
        data_find_key = {"code": '005930', "date": ncur_time}
        find_count = my_mongo.find_count_to_database(stock_db, daily_data_collection_name, data_find_key)
        if find_count == 0:
            continue

        trading_day_data['dates'].append(ncur_time)

        if ntime_to_year(ncur_time) != trading_day_data['year']:
            # mongo에 데이터를 upsert 합니다.
            trading_day_key = {'year': trading_day_data['year']}
            my_mongo.upsert_to_database(stock_db, trading_day_collection_name, trading_day_key, trading_day_data)
            logger.info(f'upsert to mongo, trading_day_key: {trading_day_key}, data: {json.dumps(trading_day_data)}')

            # trading_day_data를 초기화 합니다.
            trading_day_data = default_trading_day_data(ntime_to_year(ncur_time))

    if 0 < len(trading_day_data['dates']):
        trading_day_key = {'year': trading_day_data['year']}
        find_count = my_mongo.upsert_to_database(stock_db, trading_day_collection_name, trading_day_key, trading_day_data)


    logger.info("make_trading 작업 완료")


