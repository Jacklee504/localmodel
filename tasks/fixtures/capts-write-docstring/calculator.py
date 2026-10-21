"""A small calculator module that needs documenting."""


def add(left, right):
    return left + right


def divide(numerator, denominator):
    if denominator == 0:
        raise ValueError("denominator must not be zero")
    return numerator / denominator


def mean(values):
    return sum(values) / len(values)
