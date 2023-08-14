import datetime

from enum import Enum

SECONDS_PER_MINUTE = 60
MINUTES_PER_HOUR = 60
HOURS_PER_DAY = 24


class Common(Enum):
    # 10시 30분
    TRACKING_CODE_LIST = ["000100",
                            "001740",
                            "066910",
                            "069460",
                            "084650",
                            "149980",
                            "214450",
                            "226330",
                            "326030", ]
    TRACKING_DATE = 230816


def version():
    return "20230814.01"


def make_now_yymmdd():
    return datetime.datetime.today().strftime('%Y-%m-%d')


def make_now_hhmmss():
    return datetime.datetime.today().strftime("%H%M%S")


def isTradingTime() -> bool:
    cur_now = datetime.datetime.now()
    if cur_now.hour in [9, 10, 11, 12, 13, 14]:
        return True
    elif cur_now.hour == 15 and cur_now.minute < 30:
        return True
    else:
        return False


def isCloseTrade() -> bool:
    cur_now = datetime.datetime.now()
    return False if cur_now.hour < 15 else False if cur_now.hour == 15 and cur_now.minute < 30 else True


def to_time(num_time):
    time_sec = num_time % 100
    time_min = int(num_time / 100) % 100
    time_hour = int(num_time / 10000)
    return {"hour": time_hour, "min": time_min, "sec": time_sec}


def num_time_to_str(num_time):
    num_time_to_time = to_time(num_time)
    return '{0:02d}:{1:02d}:{2:02d}'.format(num_time_to_time["hour"], num_time_to_time["min"], num_time_to_time["sec"])


def num_time_add(num_time, add):
    num_time_to_time = to_time(num_time)
    add_to_time = to_time(add)

    result_seconds = num_time_to_time["sec"] + add_to_time["sec"]
    result_minutes = num_time_to_time["min"] + add_to_time["min"]
    result_hours = num_time_to_time["hour"] + add_to_time["hour"]

    if result_seconds >= SECONDS_PER_MINUTE:
        result_seconds = result_seconds % SECONDS_PER_MINUTE
        result_minutes += 1

    if result_minutes >= MINUTES_PER_HOUR:
        result_minutes = result_minutes % MINUTES_PER_HOUR
        result_hours += 1

    result_time = result_hours * 10000 + result_minutes * 100 + result_seconds
    return result_time


def num_time_sub(num_time, sub):
    if num_time < sub:
        raise Exception(f'num_time_sub function => num_time{num_time_sub} < sub{sub}')

    num_time_to_time = to_time(num_time)
    sub_to_time = to_time(sub)

    result_seconds = num_time_to_time["sec"] - sub_to_time["sec"]
    result_minutes = num_time_to_time["min"] - sub_to_time["min"]
    result_hours = num_time_to_time["hour"] - sub_to_time["hour"]

    while result_seconds < 0:
        result_seconds += SECONDS_PER_MINUTE
        result_minutes -= 1

    while result_minutes < 0:
        result_minutes += MINUTES_PER_HOUR
        result_hours -= 1

    result_time = result_hours * 10000 + result_minutes * 100 + result_seconds
    return result_time


def num_time_to_second(num_time):
    time_sec = num_time % 100
    time_min = int(num_time / 100) % 100
    time_hour = int(num_time / 10000)
    result_second = (time_hour * MINUTES_PER_HOUR * SECONDS_PER_MINUTE) + (time_min * SECONDS_PER_MINUTE) + time_sec
    return result_second


def num_time_to_minute(num_time):
    time_min = int(num_time / 100) % 100
    time_hour = int(num_time / 10000)
    result_minute = (time_hour * MINUTES_PER_HOUR) + time_min
    return result_minute
