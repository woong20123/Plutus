import logging
import sys
from PyQt5.QtWidgets import *
from PyQt5.QAxContainer import *
import datetime
import my_telegram as telegram
import time
import py_trade_util
import my_mongo


def make_logger():
    log_name = 'real_lion'
    log_instance = logging.getLogger(name=log_name)
    log_instance.setLevel(logging.INFO)
    formatter = logging.Formatter('|%(asctime)s||%(name)s||%(levelname)s|%(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S'
                                  )
    file_handler = logging.FileHandler('log/'+ log_name + '.log', mode='w+')  ## 파일 핸들러 생성
    file_handler.setFormatter(formatter)  ## 텍스트 포맷 설정
    log_instance.addHandler(file_handler)  ## 핸들러 등록
    log_instance.addHandler(logging.StreamHandler(sys.stdout))
    return log_instance


def make_code_list_str(code_list):
    result = ""
    for s in code_list:
        result += s + ";"
    return result.strip()[:-1]


def update_data_to_msg(update_data):
    return (f'이름 : {update_data["name"]}\n'
            f'현재가 : {update_data["current_price"]}원\n'
            f'10선 : {update_data["ave10_price"]}원\n'
            f'20선 : {update_data["ave20_price"]}원\n'
            f'60선 : {update_data["ave60_price"]}원\n')
def update_data_and_process(code_data, code, update_data, bot):
    code_data = code_data[code]
    code_data["update_datas"].append(update_data)

    if code_data["is_buy"] < 3:
        # 어제 고가 보다 가격이 높아 지면 체크
        if update_data["yesterday_high_price"] < update_data["current_price"]:
            code_data["is_buy"] += 1
            telegram.send_bot_message(bot, f'매수 포착 {update_data_to_msg(update_data)}')
    # 첫번째는 20일선이 깨지는지 먼저 체크 합니다.
    elif code_data["is_sell"] < 2:
        if update_data["current_price"] < update_data["ave20_price"]:
            code_data["is_sell"] += 1
            telegram.send_bot_message(bot, f'매도 포착 {update_data_to_msg(update_data)}')
    # 두번째는 60일선이 깨지는지 먼저 체크 합니다.
    elif code_data["is_sell"] < 3:
        if update_data["current_price"] < update_data["ave60_price"]:
            code_data["is_sell"] += 1
            telegram.send_bot_message(bot, f'매도 포착 {update_data_to_msg(update_data)}')

class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Real")
        self.setGeometry(300, 300, 300, 400)

        # telegram bot 생성
        self.bot = telegram.getBot()
        # logger 생성
        self.logger = make_logger()

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

    def make_code_data(self):
        self.tracking_code_list = ["304100", "028050", "060370", "067900", "326030", "049520", "110990", "950140"]
        self.code_data = {}
        self.logger.info(f'[감시 목록]')
        for code in self.tracking_code_list :
            name = self.GetMasterCordName(code)
            self.code_data[code] = {"update_datas": [], "is_buy": 0, "is_sell": 0, "name" : name}
            self.logger.info(f' - {name}')
    def _handler_real_data(self, code, real_type, data):
        if real_type == "주식체결":
            rtime = self.GetCommRealData(code,          20)    # 체결 시간
            rprice = self.GetCommRealData(code,         10)    # 현재가
            rsell_quote = self.GetCommRealData(code,    27)    # 매도호가
            rbuy_quote = self.GetCommRealData(code,     28)    # 매수호가
            rvolume = self.GetCommRealData(code,        13)    # 누적 거래량
            rstart_price = self.GetCommRealData(code,   16)    # 시가
            rhigh_price = self.GetCommRealData(code,    17)    # 고가
            rlow_price = self.GetCommRealData(code,     18)    # 저가
            rvolume_ratio = self.GetCommRealData(code,  851)   # 전일비 거래량 비율

            # 데이터 가공
            date = datetime.datetime.now().strftime("%Y-%m-%d ")
            time = datetime.datetime.strptime(date + rtime, "%Y-%m-%d %H%M%S")


    def btn_clicked(self):
        code_list_str = make_code_list_str(self.tracking_code_list)
        self.SetRealReg("1000", code_list_str, "20;10;27;28;13;16;17;18;851", "0")
        self.logger.info(f'{code_list_str} 구독 신청 완료.')

    def btn2_clicked(self):
        self.DisConnectRealData("1000")
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