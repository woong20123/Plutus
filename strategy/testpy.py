
yesterday_prices = [1,2,3,4,5,6,7,8,9,10,11,12]
#today_prices = [1,2,3,4,5,6,7,8,9,10,11,12]
today_prices = [1,2,3,4]

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