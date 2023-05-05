import asyncio
import sys
from collections import defaultdict
from decimal import Decimal
from itertools import permutations

import httpx

from p2p import get_p2p_orderbook

SYMBOLS = ["USDT", "BTC", "BUSD", "BNB", "ETH", "RUB"]
PAYMENTS = ["TinkoffNew", "RosBankNew", "QIWI", "YandexMoneyNew"]
INITIAL_AMOUNT = Decimal(4000)


async def get_orderbook(symbol: str, limit: int = 50):
    async with httpx.AsyncClient() as client:
        return await client.get(
            "https://api.binance.com/api/v3/depth",
            params={"symbol": symbol, "limit": limit},
        )


async def get_convert_rate() -> dict[tuple[str, str], int]:
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
    result = {(s, s): Decimal(1) for s in SYMBOLS}
    for i, rate in enumerate(r):
        c1, c2 = symbols[i].split("/")
        rate = rate.json()
        rate = Decimal(rate["bids"][0][0])
        result[(c1, c2)] = rate
        result[(c2, c1)] = Decimal(1) / rate
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
    result = defaultdict(dict)
    for i, orderbook in enumerate(r):
        direction = directions[i // (len(PAYMENTS) * len(SYMBOLS))]
        symbol = SYMBOLS[(i // len(PAYMENTS)) % len(SYMBOLS)]
        payment = PAYMENTS[i % len(PAYMENTS)]
        orderbook = orderbook.json()["data"][0]
        result[direction][(symbol, payment)] = Decimal(orderbook["adv"]["price"])
    return result


async def main(d: int = 1):
    convert_rate, p2p_rate = await asyncio.gather(get_convert_rate(), get_p2p_rate())
    cnt = d + 1
    results = []

    for depth in range(2, cnt + 1):
        for syms in permutations(SYMBOLS, r=depth):
            for payment_from in PAYMENTS:
                for payment_to in PAYMENTS:
                    result = INITIAL_AMOUNT / p2p_rate["BUY"][(syms[0], payment_from)]
                    for i in range(1, depth):
                        result *= convert_rate[(syms[i - 1], syms[i])]
                    result *= p2p_rate["BUY"][(syms[-1], payment_to)]

                    results.append(
                        (
                            syms,
                            payment_from,
                            payment_to,
                            result,
                            result / INITIAL_AMOUNT * 100 - 100,
                        )
                    )

    results = sorted(results, key=lambda x: x[4])

    for res in results:
        print(f"{'->'.join(res[0])}: {res[1]}->{res[2]} = {res[3]:.2f} ({res[4]:.2f}%)")


if __name__ == "__main__":
    try:
        depth = int(sys.argv[1])
    except IndexError:
        depth = 1
    asyncio.run(main(depth))
