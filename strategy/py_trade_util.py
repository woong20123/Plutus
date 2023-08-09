import datetime


def isTradingTime() -> bool:
    cur_now = datetime.datetime.now()
    if cur_now.hour not in [9, 10, 11, 12, 13, 14]:
        return True
    elif cur_now.hour == 15 and cur_now.minute < 30:
        return True
    else:
        return False


def isCloseTrade() -> bool:
    cur_now = datetime.datetime.now()
    return False if cur_now.hour < 15 else False if cur_now.hour == 15 and cur_now.minute < 30 else True
