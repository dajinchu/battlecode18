
import math


''' the orbit path function
def orbitPatterFunction():
    a = orbitPattern.amplitude
    b = (2 * math.pi) * orbitPattern.period
    c = orbitPattern.center'''

a = 75
b = .05
c = 125

def orbitPatternFunction(x):
    return a * math.sin(b * x) + c + x

def linearSearchForValue(value, beginning):
    bestValue = 0
    i = beginning
    while orbitPatternFunction(i) < value:
        i += 1
        print(i)
    below = orbitPatternFunction(i - 1)
    above = orbitPatternFunction(i)
    if abs(below - value) < abs(above - value):
        return i-1
    else: return i


def getBestPoint():
    min1 = ((2 * math.pi * 0) - math.acos(-1/(a*b)))/b
    min2 = ((2 * math.pi * 1) - math.acos(-1/(a*b)))/b
    min3 = min2 + ((2 * math.pi) / b)
    max1 = -min1

    firstval = orbitPatternFunction(min2)
    secondval = orbitPatternFunction(min3)
    return linearSearchForValue(secondval, int(min2))

print(getBestPoint())