import math
import time

a = 0
b = 0
c = 0
roundMap = [];
shouldLaunch = [];

def orbitPatternFunction(x):
    return a * math.sin(b * x) + c + x

def setUp(a1, b1, c1):
    a = a1
    b = b1
    c = c1
    i = 0;
    while i < 1000:
        roundMap[i] = orbitPatternFunction(i)

    i = 0
    while i < 1000:
        bool = true
        curRound = roundMap[i]
        j = i
        while j < 999 and roundMap[j] < roundMap[j+1]
            futureRound = roundMap[j]
            if(futureRound < curRound)
                bool = false

        shouldLaunch[i] = true


def shouldILaunch(x):
    return shouldLaunch[x]

def computeDestination(mars_width, mars_height, mars_walls):
    loc = random.randint(0,mars_width*mars_height-1)
    print(loc)
    while loc in mars_walls:
        print(loc)
        loc = random.randint(0,mars_width*mars_height-1)

    return loc


