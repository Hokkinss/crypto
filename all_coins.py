import requests
import time

# Глобально храним пары с MEXC
mexc_symbols = {}

def get_bitget_futures():
    url = "https://api.bitget.com/api/v2/mix/market/tickers"
    params = {"productType": "USDT-FUTURES"}
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if data.get("code") == "00000":
            # возвращаем словарь вида {"BTC": {...}, "ETH": {...}, ...}
            return {
                item["symbol"].replace("USDT", "").strip("_"): item
                for item in data["data"]
                if item["symbol"].endswith("USDT")
            }
    except Exception as e:
        print("Ошибка Bitget:", e)
    return {}

def init_mexc_symbols():
    global mexc_symbols
    url = "https://contract.mexc.com/api/v1/contract/detail"
    try:
        response = requests.get(url)
        data = response.json()
        if data.get("success"):
            for item in data.get("data", []):
                if item.get("quoteCoin") == "USDT":
                    base = item.get("baseCoin")
                    symbol = item.get("symbol")
                    mexc_symbols[base] = symbol
            print(f"Загружено {len(mexc_symbols)} пар с MEXC")
    except Exception as e:
        print("Ошибка при инициализации MEXC символов:", e)

def get_mexc_price(symbol):
    url = f"https://contract.mexc.com/api/v1/contract/ticker?symbol={symbol}"
    try:
        r = requests.get(url)
        d = r.json()
        if d.get("success"):
            return d["data"].get("lastPrice", "N/A")
    except:
        pass
    return "N/A"

def get_mexc_funding(symbol):
    url = f"https://contract.mexc.com/api/v1/contract/funding_rate/{symbol}"
    try:
        r = requests.get(url)
        d = r.json()
        if d.get("success"):
            return d["data"].get("fundingRate", "N/A")
    except:
        pass
    return "N/A"

def show_data_fast():
    init_mexc_symbols()  # загружаем символы один раз

    while True:
        print("\n=== Обновление ===\n")
        bitget_data = get_bitget_futures()

        for coin, b_data in bitget_data.items():
            b_price = b_data.get("lastPr", "N/A")
            b_funding = b_data.get("fundingRate", "N/A")
            print(f"{coin} (Bitget): Цена = {b_price}, Funding = {b_funding}")

            mexc_symbol = mexc_symbols.get(coin)
            if mexc_symbol:
                m_price = get_mexc_price(mexc_symbol)
                m_funding = get_mexc_funding(mexc_symbol)
                print(f"{coin} (MEXC):   Цена = {m_price}, Funding = {m_funding}")
            else:
                print(f"{coin} (MEXC):   Пара не найдена")

            print("-" * 40)

        time.sleep(10)

# запуск
show_data_fast()
