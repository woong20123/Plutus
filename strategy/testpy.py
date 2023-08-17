import json
import py_trade_util as ptutil

yesterday_prices = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,]
today_prices = [1,1,1,2,2,4,5,6,5,4,4,5,6]

def get_score_serialize_price(prices, search_count) :
    find_count = search_count + 1 if search_count + 1 <= len(prices) else len(prices)
    last_price = 0
    score = 0
    for i, price in enumerate(prices[-find_count:]):
        if 0 < i:
            if last_price < price:
                score += 1
                print(f'score add {i} {last_price} -> {price}')
            if last_price > price:
                score -= 1
                print(f'score del {i} {last_price} -> {price}')
        last_price = price
    return score


yesterday_cur_price = round(10000 / (500/10000 + 1), 0)
print(f'yesterday_cur_price = {yesterday_cur_price}')

