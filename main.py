import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Глобально храним пары с MEXC
mexc_symbols = {}

def get_bitget_futures():
    url = "https://api.bitget.com/api/v2/mix/market/tickers"
    params = {"productType": "USDT-FUTURES"}
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if data.get("code") == "00000":
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

def fetch_mexc_data(symbol):
    # Получение и цены, и фандинга
    price_url = f"https://contract.mexc.com/api/v1/contract/ticker?symbol={symbol}"
    fund_url = f"https://contract.mexc.com/api/v1/contract/funding_rate/{symbol}"

    price = "N/A"
    funding = "N/A"

    try:
        r = requests.get(price_url)
        d = r.json()
        if d.get("success"):
            price = d["data"].get("lastPrice", "N/A")
    except:
        pass

    try:
        r = requests.get(fund_url)
        d = r.json()
        if d.get("success"):
            funding = d["data"].get("fundingRate", "N/A")
    except:
        pass

    return price, funding

def show_data_fast():
    init_mexc_symbols()  # загружаем символы один раз

    while True:
        print("\n=== Обновление ===\n")
        bitget_data = get_bitget_futures()

        with ThreadPoolExecutor(max_workers=100) as executor:
            future_to_coin = {}

            for coin, b_data in bitget_data.items():
                mexc_symbol = mexc_symbols.get(coin)
                if mexc_symbol:
                    future = executor.submit(fetch_mexc_data, mexc_symbol)
                    future_to_coin[future] = (coin, b_data, mexc_symbol)
                else:
                    # Если символа нет — покажем сразу
                    b_price = b_data.get("lastPr", "N/A")
                    b_funding = b_data.get("fundingRate", "N/A")
                    print(f"{coin} (Bitget): Цена = {b_price}, Funding = {b_funding}")
                    print(f"{coin} (MEXC):   Пара не найдена")
                    print("-" * 40)

            for future in as_completed(future_to_coin):
                coin, b_data, mexc_symbol = future_to_coin[future]
                m_price, m_funding = future.result()

                b_price = b_data.get("lastPr", "N/A")
                b_funding = b_data.get("fundingRate", "N/A")
                print(f"{coin} (Bitget): Цена = {b_price}, Funding = {b_funding}")
                print(f"{coin} (MEXC):   Цена = {m_price}, Funding = {m_funding}")
                print("-" * 40)

        time.sleep(10)

# запуск
show_data_fast()
