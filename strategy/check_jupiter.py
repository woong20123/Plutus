import sys
import logging
import py_trade_util as ptutil
import my_kiwoon_util as mkutil
from pykiwoom.kiwoom import *


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