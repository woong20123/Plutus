from pykiwoom.kiwoom import *

def transfer_code_to_name(kiwoom, code):
    return kiwoom.GetMasterCodeName(code)


# 연결 상태 정보를 확인 합니다.
def check_connect_state(kiwoom):
    connect_state = ["미연결", "연결"]
    return connect_state[kiwoom.GetConnectState()]