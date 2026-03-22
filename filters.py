def apply_filters(listings: list, filters: dict) -> list:
    result = listings[:]

    deal = filters.get("deal")
    if deal in ("rent", "buy"):
        result = [x for x in result if x["deal"] == deal]

    tenant = filters.get("tenant")
    if tenant == "with":
        result = [x for x in result if x["tenant"] is True]
    elif tenant == "without":
        result = [x for x in result if x["tenant"] is False]

    price_max = filters.get("price_max")
    if price_max is not None:
        result = [x for x in result if x["price"] <= price_max]

    return result
