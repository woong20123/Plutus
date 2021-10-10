
class DailyLeaderStockLogic() :
    def __init__(self):
        super().__init__()

    # 이평선을 구합니다. 
    def make_movin_average_line(self, arr, start_index, term) : 
        if term == 0 :
            return 0
        total = 0
        for i in range(0, term) :
            total += arr[start_index + i]
        return total / term

    def get_rate_of_rise(self, arr, date) : 
        get_stock_info = None
        yesterday_price = 0
        yesterday_index = 0
        for stock_info in arr[:-2] :
            yesterday_index += 1
            if( stock_info['date'] == date) :
                get_stock_info = stock_info
                yesterday_price = arr[yesterday_index]['cur_price']
                break;

        if get_stock_info == None :
            return 0

        diff_price = get_stock_info['cur_price'] - yesterday_price;
        return (diff_price / yesterday_price) * 100


    # 거래량이 주어진 값보다 높은지 체크합니다.
    def check_volume(self, volume, check_volume) : 
        return volume >= check_volume

    def check_transaction_amount(self, tamount, check_volume) : 
        return tamount >= check_volume

    def check_logic(self, stock_data, stock_info_index) :
        cur_stockinfo = stock_data['stock_info'][stock_info_index]
        date = int(cur_stockinfo['date'])
        cur_price = int(cur_stockinfo['cur_price'])
        cur_high_price = int(cur_stockinfo['high_price'])
        cur_low_price = int(cur_stockinfo['low_price'])
        cur_volume = int(cur_stockinfo['cur_volume'])
        yesterday_price = int(stock_data['stock_info'][stock_info_index+1]['cur_price'])
        yesterday_high_price = int(stock_data['stock_info'][stock_info_index+1]['high_price'])
        yesterday_low_price = int(stock_data['stock_info'][stock_info_index+1]['low_price'])
        before_2day_start_price = int(stock_data['stock_info'][stock_info_index+2]['start_price'])
        result_fail = (False, date)
        result_success = (True, date)
        
        # 거래량 체크 2000만
        check_volume = 2500 * 10000
        if False == self.check_volume(cur_volume, check_volume) :
            return result_fail, 0

        # 거래대금 체크
        # tamount = 거래량 * 현재가 / 100만원
        tamount = cur_volume * cur_price / (100 * 10000)

        # 1500억원
        check_tamout = 150000
        if False == self.check_transaction_amount(tamount, check_tamout) :
            return result_fail, 0
        return result_success, 0
