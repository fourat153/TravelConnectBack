def div_ceil(nominator: int, denominator: int) -> int:
    if denominator <= 0:
        raise ValueError("denominator must be greater than zero")
    return (nominator + denominator - 1) // denominator
