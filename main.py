import asyncio
from collections import defaultdict
from decimal import Decimal

import httpx

from p2p import get_p2p_orderbook

SYMBOLS = ["USDT", "BTC", "BUSD", "BNB", "ETH", "RUB"]
PAYMENTS = ["TinkoffNew", "RosBankNew"] #, "QIWI", "YandexMoneyNew"]
INITIAL_AMOUNT = Decimal(2000)


async def get_orderbook(symbol: str, limit: int = 50):
    async with httpx.AsyncClient() as client:
        return await client.get(
            "https://api.binance.com/api/v3/depth",
            params={"symbol": symbol, "limit": limit},
        )


async def get_convert_rate() -> dict:
    symbols = [
        "BTC/USDT",
        "BUSD/USDT",
        "BNB/USDT",
        "ETH/USDT",
        "USDT/RUB",
        "BTC/BUSD",
        "BNB/BTC",
        "ETH/BTC",
        "BTC/RUB",
        "BNB/BUSD",
        "ETH/BUSD",
        "BUSD/RUB",
        "BNB/ETH",
        "BNB/RUB",
        "ETH/RUB",
    ]
    tasks = [get_orderbook(s.replace("/", ""), 1) for s in symbols]
    r = await asyncio.gather(*tasks)
    result = defaultdict(dict)
    for i, rate in enumerate(r):
        c1, c2 = symbols[i].split("/")
        rate = rate.json()
        rate = (Decimal(rate["bids"][0][0]) + Decimal(rate["asks"][0][0])) / 2
        result[c1][c2] = rate
        result[c2][c1] = Decimal(1) / rate
    for s in SYMBOLS:
        result[s][s] = Decimal(1)
    return result


async def get_p2p_rate() -> dict:
    directions = ["BUY", "SELL"]

    tasks = [
        get_p2p_orderbook(d, s, p, trans_amount=int(INITIAL_AMOUNT))
        for d in directions
        for s in SYMBOLS
        for p in PAYMENTS
    ]
    r = await asyncio.gather(*tasks)
    result = defaultdict(lambda: defaultdict(dict))
    for i, orderbook in enumerate(r):
        direction = directions[i // (len(PAYMENTS) * len(SYMBOLS))]
        symbol = SYMBOLS[(i // len(PAYMENTS)) % len(SYMBOLS)]
        payment = PAYMENTS[i % len(PAYMENTS)]
        orderbook = orderbook.json()["data"][0]
        result[direction][symbol][payment] = Decimal(orderbook["adv"]["price"])
    return result


async def main():
    convert_rate, p2p_rate = await asyncio.gather(get_convert_rate(), get_p2p_rate())

    for symbol_from in SYMBOLS:
        for symbol_to in SYMBOLS:
            for payment_from in PAYMENTS:
                for payment_to in PAYMENTS:
                    # usdt -> btc
                    bought = INITIAL_AMOUNT / p2p_rate["BUY"][symbol_from][payment_from]
                    converted = bought * convert_rate[symbol_from][symbol_to]
                    sold = converted * p2p_rate["BUY"][symbol_to][payment_to]
                    if sold / INITIAL_AMOUNT > Decimal(1.01):
                        print(
                            f"{symbol_from}->{symbol_to}: {payment_from}->{payment_to} = {sold:.2f} ({sold / INITIAL_AMOUNT * 100 - 100:.2f}%)"
                        )


if __name__ == "__main__":
    asyncio.run(main())
