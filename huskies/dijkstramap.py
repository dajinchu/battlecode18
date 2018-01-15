import collections as fast
import time
import random
WIDTH = 50
HEIGHT = 50

class Node:
    def __init__(self,x,y,v):
        self.x = x
        self.y = y
        self.v = v


# @param goals is a list of MapLocations denoting goal locations (to be set to 0)
def dijkstraMap(goals):
    flen = 0
    # instantiate initial grid with "infinite" values
    grid = [[100 for i in range(WIDTH)] for k in range(HEIGHT)]
    frontier = fast.deque()
    for g in goals:
        frontier.append(g)
        flen +=1

    while flen:
        # pop the first
        curr = frontier.popleft()
        flen -= 1
        # TODO CHECK IF ITS A WALL
        
        # set the value in the grid
        grid[curr[0]][curr[1]]=curr[2]
        # check cardinal directions for locations with higher v
        # add the locations to frontier if they have higher
        v = curr[2]
        x = curr[0]+1
        y = curr[1]
        if 0<=x<WIDTH and 0<=y<HEIGHT and grid[x][y] > v+1:
            grid[x][y]=v+1
            frontier.append([x,y,v+1])
            flen += 1
        x = curr[0]-1
        y = curr[1]
        if 0<=x<WIDTH and 0<=y<HEIGHT and grid[x][y] > v+1:
            grid[x][y]=v+1
            frontier.append([x,y,v+1])
            flen += 1
        x = curr[0]
        y = curr[1]+1
        if 0<=x<WIDTH and 0<=y<HEIGHT and grid[x][y] > v+1:
            grid[x][y]=v+1
            frontier.append([x,y,v+1])
            flen += 1
        x = curr[0]
        y = curr[1]-1
        if 0<=x<WIDTH and 0<=y<HEIGHT and grid[x][y] > v+1:
            grid[x][y]=v+1
            frontier.append([x,y,v+1])
            flen += 1
    return grid



total_time = 0
goals = [[random.randrange(WIDTH),random.randrange(WIDTH),-random.randrange(5)] for i in range(100)]
for i in range(500):
    start = time.time()
    A = dijkstraMap(goals)
    end = time.time()
    total_time += end-start
print(total_time/500)

'''A = dijkstraMap([[25,25,0],[25,30,-1]])

inrange = []
for x,row in enumerate(A):
    for y,cell in enumerate(row):
        if cell == 7:
            inrange.append([x,y,0])
B = dijkstraMap(inrange)
print('\n'.join([''.join(['{:3}'.format(item) for item in row])for row in A]))
print('\n')
print('\n'.join([''.join(['{:3}'.format(item) for item in row])for row in B]))
'''
