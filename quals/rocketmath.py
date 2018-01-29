import math
import time
import random

a = 0
b = 0
c = 0
roundMap = [None] * 1000
shouldLaunch = [None] * 1000

def orbitPatternFunction(x):
    return a * math.sin(b * x) + c + x

def setup(a1, b1, c1):
    global a,b,c
    a = a1
    b = b1
    c = c1
    for i in range(1000):
        roundMap[i] = orbitPatternFunction(i)

    for i in range(1000):
        bof = True
        curRound = roundMap[i]
        j = i
        while j < 999 and roundMap[j] < roundMap[j+1]:
            futureRound = roundMap[j]
            if(futureRound < curRound):
                bof = False
            j += 1

        shouldLaunch[i] = bof

    print (shouldLaunch)


def shouldILaunch(x):
    return shouldLaunch[x]

def computeDestination(mars_width, mars_height, mars_walls):
    loc = random.randint(0,mars_width*mars_height-1)
    print(loc)
    while loc in mars_walls:
        print(loc)
        loc = random.randint(0,mars_width*mars_height-1)

    return loc

