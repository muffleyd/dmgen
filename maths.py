import math


def divisors(number):
    return [i for i in range(2, 1 + number // 2) if number // i == number / i]


def primerange(limit, primes=None):
    if not primes:
        primes = [False, True] * (limit // 2)
        if limit % 2:
            primes.append(False)
        primes[1] = False
        primes[2] = True
    for i in range(3, int(math.ceil(limit ** .5))):
        if primes[i]:
            for j in range(i * 2, limit, i):
                primes[j] = False
    return primes


def primeslist(limit):
    return [i for i, j in enumerate(primerange(limit)) if j]


def factorial(n):
    for x in range(n - 1, 0, -1):
        n *= x
    return n


def factors(num):
    facts = []
    for x in range(2, int(num ** .5) + 1):
        if not num % x:
            facts.append(x)
    last = num // facts[-1]
    if last != facts[-1]:
        facts.append(last)
    for x in facts[:-1:-1]:
        facts.append(num // x)
    return facts


_fibonacci_known = [None, 1, 1]


def fibonacci(k):
    if round(k) == k and k > 0:
        return _fibonacci(int(k))
    if not k > 0:
        raise ValueError("Must be a positive integer")
    raise TypeError("Must be an integer")


def _fibonacci(k):
    if len(_fibonacci_known) > k:
        return _fibonacci_known[k]
    z = _fibonacci(k - 2) + _fibonacci(k - 1)
    _fibonacci_known.append(z)
    return z


def isprime(i):
    for j in range(2, int(i ** .5) + 1):
        if not i % j:
            return False
    return True


def isprime2(i):
    """returns False if it is a prime, otherwise the number it is divisible by
    """
    for j in range(2, int(i ** .5) + 1):
        if not i % j:
            return j
    return False
