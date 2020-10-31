import sys

from PyQt5.QAxContainer import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Plutus')
        self.setGeometry(300, 300, 300, 400)

        # 키움 OpenAPI 라이브러리 추가 
        self.kiwoom = QAxWidget('KHOPENAPI.KHOpenAPICtrl.1')
        self.kiwoom.dynamicCall('CommConnect()')

        self.text_edit = QTextEdit(self)
        self.text_edit.setGeometry(10, 260, 280, 100)
        self.text_edit.setEnabled(False)

        # 코드 검색용 UI 인터페이스
        label = QLabel('종목코드 : ', self)
        label.move(20, 20)

        self.code_edit = QLineEdit(self)
        self.code_edit.move(80, 20)
        self.code_edit.setText('039490')

        # 조회용 버튼 클릭
        findbtn = QPushButton('조회', self)
        findbtn.move(190, 20)
        findbtn.clicked.connect(self.findbtn_clicked)

        # 종목 코드 얻는 버튼 
        getCodebtn = QPushButton('종목코드 얻기', self)
        getCodebtn.move(190, 60)
        getCodebtn.clicked.connect(self.getCodebtn_clicked)

        self.listWidget = QListWidget(self)
        self.listWidget.setGeometry(10, 60, 170, 130)

        # 콜백이벤트 등록
        self.kiwoom.OnEventConnect.connect(self.on_connect)
        self.kiwoom.OnReceiveTrData.connect(self.on_receiveTr)

    # 검색용 버튼 클릭 이벤트 함수
    def findbtn_clicked(self):
        code = self.code_edit.text()
        self.text_edit.append('종목코드: ' + code)

        # SetInputValue
        self.kiwoom.dynamicCall('SetInputValue(QString, QString)', '종목코드', code)

        # CommRqData
        self.kiwoom.dynamicCall('CommRqData(QString, QString, int, QString)', 'opt10001_req', 'opt10001', 0, '0101')

    # 마켓 정보 가져오기
    def getCodebtn_clicked(self):
        codeList = self.get_MarketList('kospi')
        self.listWidget.addItems(codeList)
        self.text_edit.append('kospi MarkerCode Count = ' +  str(len(codeList)))

    def get_MarketList(self, marketType):
        callRet = ''
        code_name_list =[]
        if marketType == 'kospi':
            callRet = self.kiwoom.dynamicCall('GetCodeListByMarket(QString)', ['0'])
        elif marketType == 'kosdaq':
            callRet = self.kiwoom.dynamicCall('GetCodeListByMarket(QString)', ['10'])
        else :
            return code_name_list

        code_list = callRet.split(';')

        for x in code_list :
            name = self.kiwoom.dynamicCall('GetMasterCodeName(QString)', [x])
            code_name_list.append(x + ' : ' + name)
        return code_name_list


    # 접속 이벤트 콜백 함수
    def on_connect(self, err_code):
        if err_code == 0:
            self.text_edit.append('Login On')
        else: 
            self.text_edit.append('Login Fail err =' +  err_code)

    # Tr 이벤트 콜백 함수
    def on_receiveTr(self, screen_no, rqname, trcode, recordname, prev_next, data_len, err_code, msg1, msg2):
        if rqname == 'opt10001_req':
            name = self.kiwoom.dynamicCall('CommGetData(QString, QString, QString, int, QString)', trcode, '', rqname, 0, '종목명')
            volume = self.kiwoom.dynamicCall('CommGetData(QString, QString, QString, int, QString)', trcode, '', rqname, 0, '거래량')
            self.text_edit.append('종목명: ' + name.strip())
            self.text_edit.append('거래량: ' + volume.strip())

if __name__ == '__main__' :
    app = QApplication(sys.argv)
    mywindow = MyWindow()
    mywindow.show()
    app.exec_()
