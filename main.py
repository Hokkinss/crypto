import requests
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Глобально храним пары с MEXC
mexc_symbols = {}

# 0 = без сортировки, 1 = по разнице цен, 2 = по разнице фандинга
sort_mode = 1

def input_thread():
    global sort_mode
    while True:
        try:
            user_input = input("Введите режим сортировки (0 = без сортировки, 1 = по цене, 2 = по фандингу): ")
            if user_input.strip() in {"0", "1", "2"}:
                sort_mode = int(user_input.strip())
                print(f"✅ Режим сортировки изменен на {sort_mode}")
            else:
                print("❌ Неверный ввод. Введите 0, 1 или 2.")
        except Exception as e:
            print("Ошибка ввода:", e)

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
        results = []

        with ThreadPoolExecutor(max_workers=100) as executor:
            future_to_coin = {}

            for coin, b_data in bitget_data.items():
                mexc_symbol = mexc_symbols.get(coin)
                if mexc_symbol:
                    future = executor.submit(fetch_mexc_data, mexc_symbol)
                    future_to_coin[future] = (coin, b_data, mexc_symbol)
                else:
                    b_price = b_data.get("lastPr", "N/A")
                    b_funding = b_data.get("fundingRate", "N/A")
                    results.append({
                        "coin": coin,
                        "bitget_price": b_price,
                        "bitget_funding": b_funding,
                        "mexc_price": None,
                        "mexc_funding": None,
                        "price_diff": None,
                        "funding_diff": None,
                        "status": "no_pair"
                    })

            for future in as_completed(future_to_coin):
                coin, b_data, mexc_symbol = future_to_coin[future]
                m_price_str, m_funding_str = future.result()

                try:
                    b_price = float(b_data.get("lastPr", 0))
                    m_price = float(m_price_str)
                    price_diff = abs(b_price - m_price)
                except:
                    b_price = b_data.get("lastPr", "N/A")
                    m_price = m_price_str
                    price_diff = None

                try:
                    b_funding = float(b_data.get("fundingRate", 0))
                    m_funding = float(m_funding_str)
                    funding_diff = abs(b_funding - m_funding)
                except:
                    b_funding = b_data.get("fundingRate", "N/A")
                    m_funding = m_funding_str
                    funding_diff = None

                results.append({
                    "coin": coin,
                    "bitget_price": b_price,
                    "bitget_funding": b_funding,
                    "mexc_price": m_price,
                    "mexc_funding": m_funding,
                    "price_diff": price_diff,
                    "funding_diff": funding_diff,
                    "status": "ok"
                })

        # 🔽 Сортировка по выбранному режиму
        if sort_mode == 1:
            results.sort(key=lambda x: (x["price_diff"] is not None, x["price_diff"]), reverse=True)
        elif sort_mode == 2:
            results.sort(key=lambda x: (x["funding_diff"] is not None, x["funding_diff"]), reverse=True)

        # 🖨️ Вывод результатов
        for res in results:
            coin = res["coin"]
            if res["status"] == "no_pair":
                print(f"{coin} (Bitget): Цена = {res['bitget_price']}, Funding = {res['bitget_funding']}")
                print(f"{coin} (MEXC):   Пара не найдена")
            else:
                print(f"{coin} (Bitget): Цена = {res['bitget_price']}, Funding = {res['bitget_funding']}")
                print(f"{coin} (MEXC):   Цена = {res['mexc_price']}, Funding = {res['mexc_funding']}")
                if sort_mode == 1:
                    print(f"📊 Разница в цене: {res['price_diff']}")
                elif sort_mode == 2:
                    print(f"📉 Разница в фандинге: {res['funding_diff']}")
            print("-" * 40)

        time.sleep(10)

if __name__ == "__main__":
    threading.Thread(target=input_thread, daemon=True).start()
    show_data_fast()
