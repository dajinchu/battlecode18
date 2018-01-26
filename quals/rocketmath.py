import math
import time

MARS_WIDTH = 40
MARS_HEIGHT = 30
a = 50
b = (2 * math.pi) / 100
c = 125

def orbitPatternFunction(x):
    return a * math.sin(b * x) + c + x

def linearSearchForValue(value, beginning):
    bestValue = 0
    i = beginning
    while orbitPatternFunction(i) < value:
        i += 1
    below = orbitPatternFunction(i - 1)
    above = orbitPatternFunction(i)
    if abs(below - value) < abs(above - value):
        return i-1
    else: return i

def getCurrentInterval(r):
    min0 = getMin(0)
    exactInterval = (r - min0) / op.period
    return math.ceil(exactInterval)

def getMin(i):
    return ((2 * math.pi * i) - math.acos(-1/(a*b)))/b

def shouldILaunch(round):
    MIN1 = getMin(0)
    MIN2 = getMin(1)
    MAX1 = -MIN1
    FIRST_VAL = orbitPatternFunction(MIN2)
    DONT_LEAVE_AFTER_HERE = linearSearchForValue(FIRST_VAL, int(MIN1))
    if DONT_LEAVE_AFTER_HERE > (orbitPatternFunction(round) % 100) > MAX1:
        SHOULD_LAUNCH = False
    else: SHOULD_LAUNCH = True
    return SHOULD_LAUNCH

total_time = 0
for i in range(1000):
    start = time.time()
    A = shouldILaunch(i)
    end = time.time()
    print("round ",i," launch: ",A)
    total_time += end-start
print(total_time/1000)
