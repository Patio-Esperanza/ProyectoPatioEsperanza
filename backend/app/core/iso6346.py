_VALORES_LETRA = {
    "A": 10, "B": 12, "C": 13, "D": 14, "E": 15, "F": 16, "G": 17, "H": 18,
    "I": 19, "J": 20, "K": 21, "L": 23, "M": 24, "N": 25, "O": 26, "P": 27,
    "Q": 28, "R": 29, "S": 30, "T": 31, "U": 32, "V": 34, "W": 35, "X": 36,
    "Y": 37, "Z": 38,
}


def validar_iso6346(numero: str) -> bool:
    numero = numero.strip().upper()
    if len(numero) != 11:
        return False
    if not numero[:4].isalpha() or numero[3] not in "UJZ":
        return False
    if not numero[4:10].isdigit():
        return False
    if not numero[10].isdigit():
        return False

    total = 0
    for i, ch in enumerate(numero[:10]):
        valor = _VALORES_LETRA[ch] if ch.isalpha() else int(ch)
        total += valor * (2**i)

    digito_verificador = total % 11
    if digito_verificador == 10:
        digito_verificador = 0
    return digito_verificador == int(numero[10])
