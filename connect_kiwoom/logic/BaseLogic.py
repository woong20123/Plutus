
class BaseLogic() :
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


    # 최근 거래량이 많았던 적이 있는지 체크합니다.
    def find_highvolume(self, arr, start_index, term) : 
        high_volume = None
        avg_volume = None
        if term == 0 :
            return False, high_volume, avg_volume

        arr_volume_sort = sorted(arr[start_index:start_index+term], key=lambda x : (-x['cur_volume']))

        high_volume = arr_volume_sort[0]

        avg_sum_volume = 0
        for value in arr_volume_sort[2:] :
            avg_sum_volume += value['cur_volume']

        avg_volume = avg_sum_volume/len(arr_volume_sort[2:])

        if avg_volume < 5000 : 
            return False, high_volume, avg_volume

        if high_volume['cur_volume'] > avg_volume * 4 :
            return True, high_volume, avg_volume
        return False, high_volume, avg_volume

    # 2일간 거래량이 줄고 있는지 체크
    def check_volume_down(self, arr, start_index, avg_volume) : 
        today_vol = arr[start_index]['cur_volume']
        one_before_day_vol = arr[start_index+1]['cur_volume']
        two_before_day_vol = arr[start_index+2]['cur_volume']

        is_continue_down = False
        is_avg_volume_than_down = False

        if today_vol < one_before_day_vol and one_before_day_vol < two_before_day_vol :
            is_continue_down = True

        if  avg_volume != None and today_vol < avg_volume and one_before_day_vol < avg_volume and two_before_day_vol < avg_volume :
            is_avg_volume_than_down = True
            
        
        return is_continue_down, is_avg_volume_than_down

# 120일선 체크 로직 
    def check_logic(self, stock_data, stock_info_index) :
        cur_stockinfo = stock_data['stock_info'][stock_info_index]
        date = int(cur_stockinfo['date'])
        cur_price = int(cur_stockinfo['cur_price'])
        cur_high_price = int(cur_stockinfo['high_price'])
        cur_low_price = int(cur_stockinfo['low_price'])
        yesterday_price = int(stock_data['stock_info'][stock_info_index+1]['cur_price'])
        yesterday_high_price = int(stock_data['stock_info'][stock_info_index+1]['high_price'])
        yesterday_low_price = int(stock_data['stock_info'][stock_info_index+1]['low_price'])
        before_2day_start_price = int(stock_data['stock_info'][stock_info_index+2]['start_price'])
        result_fail = (False, date)
        result_success = (True, date)
        
        # 거래량 체크
        ishighvolume, high_volume_stock_info, avg_volume = self.find_highvolume(stock_data['stock_info'], stock_info_index, 15)
        if False == ishighvolume:
            return result_fail, 0

        is_continue_down, is_avg_volume_than_down = self.check_volume_down(stock_data['stock_info'], stock_info_index, avg_volume)
    
        if False == is_avg_volume_than_down and False == is_continue_down :
             return result_fail, 0

        ma_line_10 =  self.make_movin_average_line(stock_data['cur_prices'], stock_info_index, 10)
        ma_line_20 =  self.make_movin_average_line(stock_data['cur_prices'], stock_info_index, 20)
        ma_line_60 =  self.make_movin_average_line(stock_data['cur_prices'], stock_info_index, 60)
        ma_line_120 =  self.make_movin_average_line(stock_data['cur_prices'], stock_info_index, 120)

        if False == (ma_line_20 > ma_line_60 and ma_line_60 > ma_line_120) :
            return result_fail, 0

        # 120일 선 체크
        # if (cur_price * 1.02 > ma_line_120 and ma_line_120 > cur_price * 0.995) and ( yesterday_price > ma_line_120) :
        #     return result_success, 120

        # 60일 선 체크
        # if (cur_price * 1.02 > ma_line_60 and ma_line_60 > cur_price * 0.995) and ( yesterday_price > ma_line_60) :
        #     return result_success, 60

        high_v_rate_rise = self.get_rate_of_rise(stock_data['stock_info'], high_volume_stock_info['date'])
        

        # 20일 선 체크
        diff_10_20 = ma_line_10 - ma_line_20
        diff_20_60 = ma_line_20 - ma_line_60
        # if (cur_price < ma_line_10 and cur_price > ma_line_20) and ( yesterday_price > ma_line_20) and (high_v_rate_rise > 10)  :
        #     if ( ma_line_10 > ma_line_20 * 1.02 ) and ( diff_10_20 > diff_20_60 / 3.5 ):
        if (cur_price < ma_line_10 and cur_price > ma_line_20) and ( yesterday_price > ma_line_20) and (high_v_rate_rise > 10)  :
            if ( ma_line_10 > ma_line_20 * 1.01 ) and ( diff_10_20 > diff_20_60 / 4 ):
                return result_success, 20

        if (cur_price > ma_line_10 and yesterday_price > ma_line_10) and ( True == is_continue_down) and before_2day_start_price > cur_low_price and (cur_price < ma_line_10 * 1.04) :
            if ( cur_high_price > yesterday_high_price * 0.992) and ( cur_high_price < yesterday_high_price * 1.008) and (ma_line_10 > ma_line_20) :
                if ( cur_low_price > yesterday_low_price * 0.992) and ( cur_low_price < yesterday_low_price * 1.008) :
                    return result_success, 10

        return result_fail, 0