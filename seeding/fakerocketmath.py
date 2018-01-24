import random

def shouldILaunch(round):
    return True

def computeDestination(mars_width, mars_height, mars_walls):
    loc = random.randint(0,mars_width*mars_height-1)
    print(loc)
    while loc in mars_walls:
        print(loc)
        loc = random.randint(0,mars_width*mars_height-1)

    return loc