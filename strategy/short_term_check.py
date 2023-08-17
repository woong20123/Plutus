import json
import sys
import logging
import my_mongo
import py_trade_util as ptutil
import my_kiwoon_util as mkutil
from pykiwoom.kiwoom import *
import statistics
from enum import Enum



    

def getTradingDay(db, start_year, end_year):
    dates = []
    trading_day_collection_name = my_mongo.CollectionInfo.TRADING_DAY.value
    for cur_year in range(start_year, end_year + 1):
        trading_day = my_mongo.find_one_to_database(db, trading_day_collection_name, {'year': cur_year})
        dates.extend(trading_day['dates'])
    return dates


def make_logger():
    log_name = 'check_jupiter'
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


class ShortTermLogicChecker():


    def __init__(self):
        super().__init__()
        self.logger = make_logger()
        self.kiwoom = Kiwoom()
        self.kiwoom.CommConnect(block=True)

        self.stock_db = my_mongo.get_database("stock")
        self.daily_data_collection_name = my_mongo.CollectionInfo.DAILY_DATA.value
        self.validation_data_collection_name = my_mongo.CollectionInfo.VALIDATION_DATA.value

        self.search_start_date = 20200101
        self.search_end_date = 20230811

        self.search_trading_dates = getTradingDay(self.stock_db, int(self.search_start_date / 10000), int(self.search_end_date / 10000))

        self.logger.info(f'get search_trading_dates size:{len(self.search_trading_dates)}')

        self.dict_logic_info = {
            'jupiter': {
                'func': self.jupiter_logic,
                'name': 'jupiter_12345-',
            }
        }


    def run(self):
        PRICE_TYPE_CURRENT = 0  # 종가
        PRICE_TYPE_START = 1  # 시가
        PRICE_TYPE_HIGH = 2  # 고가
        PRICE_TYPE_LOW = 3  # 저가

        total_mean_incs = [[], [], [], []]



        logic = self.dict_logic_info['jupiter']

        search_type = logic['name']
        for i, search_trading_date in enumerate(self.search_trading_dates):

            is_result, resuls_data = logic['func'](i, search_trading_date)
            if False is is_result:
                continue

            total_mean_incs[PRICE_TYPE_CURRENT].append(resuls_data['price_incs_mean'])
            total_mean_incs[PRICE_TYPE_START].append(resuls_data['start_price_incs_mean'])
            total_mean_incs[PRICE_TYPE_HIGH].append(resuls_data['high_price_incs_mean'])
            total_mean_incs[PRICE_TYPE_LOW].append(resuls_data['low_price_incs_mean'])

        validation_data = {
            "search_start_date": self.search_start_date,
            "search_end_date": self.search_end_date,
            "search_type": search_type,
            "total_price_incs": round(statistics.mean(total_mean_incs[PRICE_TYPE_CURRENT]), 2),
            "total_start_price_incs": round(statistics.mean(total_mean_incs[PRICE_TYPE_START]), 2),
            "total_high_price_incs": round(statistics.mean(total_mean_incs[PRICE_TYPE_HIGH]), 2),
            "total_low_price_incs": round(statistics.mean(total_mean_incs[PRICE_TYPE_LOW]), 2),
        }

        validation_key = {
            "search_start_date": self.search_start_date,
            "search_end_date": self.search_end_date,
            "search_type": search_type,
        }
        my_mongo.upsert_to_database(self.stock_db, self.validation_data_collection_name, validation_key, validation_data)

        self.logger.info(f'total_price_incs:{round(statistics.mean(total_mean_incs[PRICE_TYPE_CURRENT]), 2)}, '
                    f'total_start_price_incs:{round(statistics.mean(total_mean_incs[PRICE_TYPE_START]), 2)}, '
                    f'total_high_price_incs:{round(statistics.mean(total_mean_incs[PRICE_TYPE_HIGH]), 2)}, '
                    f'total_low_price_incs:{round(statistics.mean(total_mean_incs[PRICE_TYPE_LOW]), 2)}, ')


    def jupiter_logic(self, i, search_trading_date):
        '''
        다음과 같이 체크 하고 싶은 함수를 만듭니다.
        :param i:
        :param search_trading_date:
        :return: True 일떄 => True, {
                                        'price_incs_mean': round(statistics.mean(price_incs), 2),
                                        'start_price_incs_mean': round(statistics.mean(start_price_incs), 2),
                                        'high_price_incs_mean': round(statistics.mean(high_price_incs), 2),
                                        'low_price_incs_mean': round(statistics.mean(low_price_incs), 2),
                                    }

                False 일 때 => (False, {})
        '''
        if (search_trading_date < self.search_start_date or
                self.search_end_date < search_trading_date):
            return False, {}

        self.logger.info(f'run search_trading_date:{search_trading_date}')

        daily_data_key = {"date": search_trading_date}
        daily_data_list = my_mongo.find_to_database(self.stock_db, self.daily_data_collection_name, daily_data_key)

        find_daily_datas = []
        for daily_data in daily_data_list:
            # 0. 기본 지표 선정시 상한가 종목이나 -15% 미만 주식은 제외
            # if True is (2850 < daily_data['cur_inc_rate']) or (daily_data['cur_inc_rate'] < -1500):
            #    return False

            # 1. 현재가가 200일선, 60일선보다 높아야 합니다.
            if False is (daily_data['ave200_price'] < daily_data['cur_price']
                         and daily_data['ave60_price'] < daily_data['cur_price']):
                continue

            # 2. 주가 상승률은 9 ~ 18%의 값을 가집니다.
            if False is (900 < daily_data['cur_inc_rate'] < 1800):
                continue

            # 3. 거래량은 전일 대비 200% 이상
            if False is (20000 < daily_data['volume_inc_rate']):
                continue

            # 4. 종가와 고가 차이 - 주가 상승률 10% ~ 30% 미만
            diff_cur_high_price = (daily_data['high_price'] / daily_data['cur_price'] * 10000) - 10000
            if False is (int(daily_data['cur_inc_rate'] * 0.1) < diff_cur_high_price < int(
                    daily_data['cur_inc_rate'] * 0.3)):
                continue

            # # 5. 시가와 저가 차이 - 주가 상승률 10% 미만
            # diff_start_low_price = (daily_data['start_price'] / daily_data['low_price'] * 10000) - 10000
            # if False is (diff_start_low_price < int(daily_data['cur_inc_rate'] * 0.1)):
            #     continue
            #
            # yesterday_cur_price = round(daily_data['cur_price'] / (daily_data['cur_inc_rate'] / 10000 + 1), 0)
            # # 6. 시가가 어제의 종가보다 높음
            # if yesterday_cur_price < daily_data['start_price']:
            #     continue

            find_daily_datas.append(daily_data)

        if len(find_daily_datas) == 0:
            return False, {}

        # 선별한 종목을 기준을 다음날 데이터와 비교 합니다.
        next_index = i + 1
        if len(self.search_trading_dates) <= next_index:
            return False, {}

        next_search_trading_date = self.search_trading_dates[next_index]

        price_incs = []
        start_price_incs = []
        high_price_incs = []
        low_price_incs = []

        for find_daily_data in find_daily_datas:
            next_daily_data_key = {"date": next_search_trading_date, "code": find_daily_data["code"]}
            next_daily_data = (my_mongo.find_one_to_database(self.stock_db, self.daily_data_collection_name,
                                                            next_daily_data_key))
            price_inc = round(next_daily_data["cur_inc_rate"] / 100, 2)
            start_price_inc = round((next_daily_data["start_price"] / find_daily_data["cur_price"] * 100) - 100, 2)
            high_price_inc = round((next_daily_data["high_price"] / find_daily_data["cur_price"] * 100) - 100, 2)
            low_price_inc = round((next_daily_data["low_price"] / find_daily_data["cur_price"] * 100) - 100, 2)

            self.logger.info(
                f'find 종목 search_trading_date:{search_trading_date}, name :{mkutil.transfer_code_to_name(self.kiwoom, find_daily_data["code"])} '
                f'상승률:{price_inc}, 시가 상승률:{start_price_inc}, 고가 상승률:{high_price_inc}, 저가 상승률:{low_price_inc}')

            price_incs.append(price_inc)
            start_price_incs.append(start_price_inc)
            high_price_incs.append(high_price_inc)
            low_price_incs.append(low_price_inc)

        return (True,
                {
                    'price_incs_mean': round(statistics.mean(price_incs), 2),
                    'start_price_incs_mean': round(statistics.mean(start_price_incs), 2),
                    'high_price_incs_mean': round(statistics.mean(high_price_incs), 2),
                    'low_price_incs_mean': round(statistics.mean(low_price_incs), 2),
                })


if __name__ == "__main__":
    logic_checker = ShortTermLogicChecker()
    logic_checker.run()
