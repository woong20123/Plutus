
yesterday_prices = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,]
today_prices = [1,1,1,2,2,4,5,6,5,4,4,5,6]

range = 5
yesterday_range = range - len(today_prices) if 0 < range - len(today_prices) else 0
today_range = range - yesterday_range
print(f'yrage : {yesterday_range} trange : {today_range}')

print('yesterday')
if 0 < yesterday_range:
    for price in yesterday_prices[:yesterday_range]:
        print(price)
print('today')
for price in today_prices[-today_range:]:
    print(price)

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


print(f'get_score_serialize_price = {get_score_serialize_price(today_prices, 15)}')
