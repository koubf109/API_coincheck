# import collections
import requests
import numpy as np
import time
import pandas as pd

from numpy.core.fromnumeric import var
from pandas.core.algorithms import diff

holdtimer = 0
BTC_buyprice = 0#BTC購入時の値段を保存しておく変数
BTC_sellprice = 0#BTC売却時の値段を保存しておく変数
flag = 0
signal = 0
initial_BTC = 0#最初のレート
trade_counter = 0#取引回数記録
# spread = 20
D_DIV = 14400#unixtimeで換算．最大値の計算範囲の設定
holdtimer = 0
# time_range = 200 #読み取り範囲
# timer = 0
c = 0
# recordrange = 50#まわす回数
START_BTC = 0
START_YEN = 10000
START_LOGGED_AMOUNT = 400



################各種関数##################



def get_variance(n):#nを受けて9~8h時間前(n-540~n-480前)の分散返してくれる
    BTCdf.set_index('time')
    df3 = BTCdf.loc[n-300:n-240]
    variance = df3['price_sell'].diff().var()
    variance = np.sqrt(variance)
    return variance

def get_moving_avr(n):#nを受けて過去30分３回の移動平均がすべて正かをtruefalseで返してくれる
    BTCdf.set_index('time')
    window = 30#移動平均を観測する窓の大きさ
    r = 3#過去何回分を見るか
    moving_avr_list = []
    # print(BTCdf['price_buy'])
    for _num_ in range (r):
        moving_avr_list.append(BTCdf.loc[n-window*(_num_)-1:n-window*(_num_-1)-1]['price_buy'].diff().mean())
    return all((x >= 0.0 for x in moving_avr_list))

def tradesign(n):
    df1 = BTCdf[(BTCdf["time"] > BTCdf["time"][n-1]-D_DIV)& (BTCdf["time"] <= BTCdf["time"][n-1])]#過去d_div時間の配列
    # print(BTCdf["time"][n-1]-D_DIV)
    # print(BTCdf["time"][n-1])
    
    maxid = df1["price_buy"].idxmax() #その最大値のid
    
    # df2 = BTCdf[(BTCdf["time"] > BTCdf["time"][n-1]-3600)& (BTCdf["time"] < BTCdf["time"][n-1])]#過去3600sの配列
    # minid = df2["price_buy"].idxmin() #その最小値のid

    variance_n = get_variance(n-1)#nを受けて9~8h時間前(n-540~n-480前)の分散返してくれる
    global holdtimer
    holdtimer = holdtimer-1

    if holdtimer > 1:
        return_v = 0
    elif variance_n > avr_variance*1.2:# 分散が大きい時の処理
        # print("large variance")
        if BTCdf["price_buy"][n-1]<df1["price_buy"][maxid]*0.95 and BTCdf["account_yen"][n-1]>0:
            holdtimer = 0
            return_v = 2
        # 過去一定時間の最高値より一定額低かったら購入
        elif BTCdf["price_sell"][n-1]>BTC_buyprice*1.05 and BTCdf["account_btc"][n-1]>0:
        # 買った時の値段より一定額高かったら売却
            holdtimer = 0
            return_v = 1
        else:
            holdtimer = holdtimer + 1
            return_v = 0
        #買うとき2，売るとき1，hold0
    elif  variance_n < avr_variance*0.9:# 分散が小さい時の処理
        # print("small variance")
        if get_moving_avr(n-1) and BTCdf["account_yen"][n-1]>0 and holdtimer <1:#3回連続３０分上がり調子
            holdtimer = 0
            return_v = 2
        elif BTCdf["price_sell"][n-1]>BTC_buyprice*1.02 and BTCdf["account_btc"][n-1]>0 and holdtimer<1:
        # 買った時の値段より一定額高かったら売却
            holdtimer = 0
            return_v = 1
        elif BTCdf["price_sell"][n-1]<BTC_buyprice/1.0065 and BTCdf["account_btc"][n-1]>0 and holdtimer<1:
        #損切用
            holdtimer = 0
            return_v = 1
        else:
            holdtimer = holdtimer + 1
            return_v = 0
        #買うとき2，売るとき1，hold0
    else:#分散が普通のとき
        if get_moving_avr(n-1) and BTCdf["account_yen"][n-1]>0 and holdtimer <1:#3回連続３０分上がり調子
            holdtimer = 0
            return_v = 2
        elif BTCdf["price_sell"][n-1]>BTC_buyprice*1.01 and BTCdf["account_btc"][n-1]>0:
        # 買った時の値段より一定額高かったら売却
            holdtimer = 0
            return_v = 1
        elif BTCdf["price_sell"][n-1]<BTC_buyprice/1.0065 and BTCdf["account_btc"][n-1]>0:
        #損切用
            holdtimer = 0
            return_v = 1
        else:
            holdtimer = holdtimer + 1
            return_v = 0
        #買うとき2，売るとき1，hold0

    print(variance_n)    
    return return_v


def hold_btc(n):
    BTCdf.loc[n,"account_btc"] = BTCdf.loc[n-1,"account_btc"]
    BTCdf.loc[n,"account_yen"] = BTCdf.loc[n-1,"account_yen"]
    BTCdf.loc[n,"debug"] = "hold" #debug用

def buy_btc(n,btc_rate):
    if BTCdf.loc[n-1,"account_yen"] !=0:
        BTCdf.loc[n,"account_btc"] = BTCdf.loc[n-1,"account_btc"] + BTCdf.loc[n-1,"account_yen"]/(btc_rate)
        BTCdf.loc[n,"account_yen"] = 0
        # BTCdf.loc[n,"btc_rate"] = btc_rate #debug用
        global BTC_buyprice
        BTC_buyprice = btc_rate
        global c
        c = c + 1
        # print("buy")
        BTCdf.loc[n,"debug"] = "buy"
    else:
        BTCdf.loc[n,"account_btc"] = BTCdf.loc[n-1,"account_btc"]
        BTCdf.loc[n,"account_yen"] = BTCdf.loc[n-1,"account_yen"]
        BTCdf.loc[n,"debug"] = "buy but no yen"
#ビットコを買う時の関数．

def sell_btc(n,btc_rate):
    if BTCdf.loc[n-1,"account_btc"] !=0:
        BTCdf.loc[n,"account_yen"] = BTCdf.loc[n-1,"account_yen"] + BTCdf.loc[n-1,"account_btc"]*(btc_rate)
        BTCdf.loc[n,"account_btc"] = 0
        BTCdf.loc[n,"btc_rate"] = btc_rate#debug用
        global BTC_sellprice
        BTC_sellprice = btc_rate
        global c
        BTCdf.loc[n,"debug"] = "sell"
        # print("sell")
    else:
        BTCdf.loc[n,"account_btc"] = BTCdf.loc[n-1,"account_btc"]
        BTCdf.loc[n,"account_yen"] = BTCdf.loc[n-1,"account_yen"]
        BTCdf.loc[n,"debug"] = "sell but no yen"
#ビットコを売る時の関数．

def BTCconv(n,btc_rate):
    if BTCdf.loc[n,"account_yen"] == 0:
        yen = BTCdf.loc[n,"account_yen"] + BTCdf.loc[n,"account_btc"]*(btc_rate)
    else :
        yen = BTCdf.loc[n,"account_yen"]
    return yen
#総資産をyenで評価してくれる関数

##############ここまで各種関数########################



###################初期設定########################



avr_variance = 4500



# dfflag = 0
pre_unix = 0
global dfflag
dfflag = 0

INTERVAL = 60

predata = []
# predata = 0

URL = 'https://coincheck.com/api/exchange/orders/rate'



def getAPIdata():
    params = {'order_type': 'sell', 'pair': 'btc_jpy', 'price': START_YEN}
    sellprice = requests.get(URL, params = params).json()
    # print(coincheck)

    params = {'order_type': 'buy', 'pair': 'btc_jpy', 'price': START_YEN}
    buyprice = requests.get(URL, params = params).json()
    # print(coincheck)


    APIdata = np.array([time.time(),sellprice['rate'],buyprice['rate']],dtype='float')
    return APIdata

# 1分ごとにdfに追加，price_sellとかはnでquery？

###################main文############################3



while True:
    if time.time() > pre_unix + INTERVAL:#時間感覚に応じて適宜変更
        currentdata = getAPIdata()
        
        pre_unix = time.time()
        logged_amount = len(np.reshape(predata,(-1,3)))-1
        
        # print(logged_amount)
        
        if logged_amount > START_LOGGED_AMOUNT:
            if dfflag == 0:#最初だけ口座情報など記録用columns追加，flagで管理
                # print(predata)
                BTCdf = pd.DataFrame(np.reshape(predata,(-1,3)),columns=["time","price_buy","price_sell"])
                BTCdf = BTCdf.assign(btc_ignore=0,account_yen=0,account_btc=0,Total_assets=0,debug=0)
                # print(BTCdf)
                initial_BTC = START_YEN/float((BTCdf.loc[logged_amount,"price_buy"]))#最初の持ち金BTC
                BTCdf.loc[logged_amount,"btc_ignore"] = initial_BTC
                BTCdf.loc[logged_amount,"account_yen"] = START_YEN
                BTCdf.loc[logged_amount,"account_btc"] = 0
                
                dfflag = 1
            elif dfflag == 1:
                signal = tradesign(logged_amount)
                #sell,buyに渡すのは現在の値
                if signal == 1:sell_btc(logged_amount,currentdata[1])
                elif signal == 2:buy_btc(logged_amount,currentdata[2])
                elif signal == 0:hold_btc(logged_amount)
                
                BTCdf.loc[logged_amount,"Total_assets"] = BTCconv(logged_amount,currentdata[1])
                BTCdf.loc[logged_amount,"btc_ignore"] = BTCdf.loc[START_LOGGED_AMOUNT+1,"btc_ignore"]*currentdata[2]#比較用ガチホモデル
                
                BTCdf.loc[logged_amount,"time"] = currentdata[0]
                BTCdf.loc[logged_amount,"price_sell"] = currentdata[1]
                BTCdf.loc[logged_amount,"price_buy"] = currentdata[2]
                if logged_amount%2==0:BTCdf.to_csv("sawada_tradedata.csv",encoding = 'UTF-8')#適当なタイミングで売買記録をcsvに記述
            else:
                break

        
        #売買処理後，predataに今回の相場追記
        predata = np.append(predata,currentdata,axis=0)

        #BTCdfにも反映




