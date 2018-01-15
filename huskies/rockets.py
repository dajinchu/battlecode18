
import math


''' the orbit path function
def orbitPatterFunction():
    a = orbitPattern.amplitude
    b = (2 * math.pi) * orbitPattern.period
    c = orbitPattern.center'''
def orbitPatternFunction(x):
    a = 75
    b = .05
    c = 125
    return a * math.sin(b * x) + c + x

def linearSearchForValue(value, beginning, end):
    diff = 1000000000
    bestValue = 0
    i = 0
    while orbitPatternFunction(i) < value:
        i += 1
    below = orbitPatternFunction(i - 1)
    above = orbitPatternFunction(i)
    if abs(below - value) < abs(above - value):
        return below
    else: return above


def getBestPoint():
    a = 75
    b = .05
    c = 125
    min1 = ((2 * math.pi * 0) - math.acos(-1/(a*b)))/b
    min2 = ((2 * math.pi * 1) - math.acos(-1/(a*b)))/b
    max1 = -min1

    firstval = orbitPatternFunction(min2)

    return linearSearchForValue(firstval, int(min1), int(max1))

print(getBestPoint())