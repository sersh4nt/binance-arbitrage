from typing import Literal
from urllib.parse import urljoin

import httpx

BASE_URL = "https://p2p.binance.com/"
ENDPOINT = "/bapi/c2c/v2/friendly/c2c/adv/search"
path = urljoin(BASE_URL, ENDPOINT)

Direction = Literal["BUY", "SELL"]

PayType = Literal[
    "TinkoffNew", "RaiffeisenBank", "RosBankNew", "QIWI", "YandexMoneyNew"
]


def generate_payload(asset, pay_type, rows, direction, trans_amount) -> dict:
    return {
        "asset": asset,
        "countries": [],
        "fiat": "RUB",
        "page": 1,
        "payTypes": [pay_type],
        "proMerchantAds": False,
        "publisherType": None,
        "rows": rows,
        "tradeType": direction,
        "transAmount": trans_amount,
    }


async def get_p2p_orderbook(
    direction: Direction,
    asset: str,
    pay_type: PayType,
    trans_amount: int = 50000,
    rows: int = 10,
):
    data = generate_payload(asset, pay_type, rows, direction, trans_amount)
    async with httpx.AsyncClient() as client:
        return await client.post(path, json=data)
