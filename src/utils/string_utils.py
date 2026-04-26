def pluralize(n: int, forms: list[str]) -> str:
    """
    Returns the correct Russian plural form for a number.
    
    :param n: The number to check.
    :param forms: A list of three forms: [один, два, пять].
    :return: The correct form from the list.
    """
    n = abs(n) % 100
    n1 = n % 10
    if 10 < n < 20:
        return forms[2]
    if 1 < n1 < 5:
        return forms[1]
    if n1 == 1:
        return forms[0]
    return forms[2]


