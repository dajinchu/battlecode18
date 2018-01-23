import collections as fast
import time
import random
import array
WIDTH = 50
HEIGHT = 50

# @param goals is a list of MapLocations denoting goal locations (to be set to 0)
# @param walls is a Set denoting the places that can't be walked through
def dijkstraMap(goals,walls):
    flen = 0
    # instantiate initial grid with "infinite" values
    grid = [[100 for i in range(HEIGHT)] for k in range(WIDTH)]
    frontier = fast.deque()
    for g in goals:
        frontier.append(g)
        grid[g[0]][g[1]] = g[2]
        flen +=1

    while frontier:
        # pop the first
        curr = frontier.popleft()

        x0 = curr[0]
        y0 = curr[1]
        vmin = curr[2]+1

        # check cardinal directions for locations with higher v
        # add the locations to frontier if they have higher
        if x0 != 0:
            x = x0-1
            y = y0
            if not (y*WIDTH+x in walls) and grid[x][y] > vmin:
                grid[x][y]=vmin
                frontier.append([x,y,vmin])
            if y0 != 0:
                y = y0 - 1
                if not (y * WIDTH + x in walls) and grid[x][y] > vmin:
                    grid[x][y] = vmin
                    frontier.append([x, y, vmin])
            if y0 != HEIGHT-1:
                y = y0 + 1
                if not (y * WIDTH + x in walls) and grid[x][y] > vmin:
                    grid[x][y] = vmin
                    frontier.append([x, y, vmin])
        if x0 != WIDTH-1:
            x = x0 + 1
            y = y0
            if not (y * WIDTH + x in walls) and grid[x][y] > vmin:
                grid[x][y] = vmin
                frontier.append([x, y, vmin])
            if y0 != 0:
                y = y0 - 1
                if not (y * WIDTH + x in walls) and grid[x][y] > vmin:
                    grid[x][y] = vmin
                    frontier.append([x, y, vmin])
            if y0 != HEIGHT - 1:
                y = y0 + 1
                if not (y * WIDTH + x in walls) and grid[x][y] > vmin:
                    grid[x][y] = vmin
                    frontier.append([x, y, vmin])
        if y0 != HEIGHT - 1:
            x = x0
            y = y0+1
            if not (y * WIDTH + x in walls) and grid[x][y] > vmin:
                grid[x][y] = vmin
                frontier.append([x, y, vmin])
        if y0 != 0:
            x = x0
            y = y0-1
            if not (y * WIDTH + x in walls) and grid[x][y] > vmin:
                grid[x][y] = vmin
                frontier.append([x, y, vmin])
    return grid


total_time = 0
goals = [[random.randrange(WIDTH),random.randrange(WIDTH),-random.randrange(5)] for i in range(100)]
walls = {i for i in range(WIDTH*HEIGHT) if random.randint(0,0)==1}
for i in range(1000):
    start = time.time()
    A = dijkstraMap(goals,walls)
    end = time.time()
    total_time += end-start
print(total_time/1000)

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
