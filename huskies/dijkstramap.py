import queue
import time
WIDTH = 50
HEIGHT = 50

class Node:
    def __init__(self,x,y,v):
        self.x = x
        self.y = y
        self.v = v


# @param goals is a list of MapLocations denoting goal locations (to be set to 0)
def dijkstraMap(goals):
    # instantiate initial grid with "infinite" values
    grid = [[100 for i in range(WIDTH)] for k in range(HEIGHT)]
    frontier = queue.Queue()
    for g in goals:
        frontier.put(g)

    while frontier.qsize() > 0:
        # pop the first
        curr = frontier.get()
        # TODO CHECK IF ITS A WALL
        
        # set the value in the grid
        grid[curr[0]][curr[1]]=curr[2]
        # check cardinal directions for locations with higher v
        # add the locations to frontier if they have higher
        addLocIfGreater(curr[0]+1,curr[1],curr[2],grid,frontier)
        addLocIfGreater(curr[0]-1,curr[1],curr[2],grid,frontier)
        addLocIfGreater(curr[0],curr[1]+1,curr[2],grid,frontier)
        addLocIfGreater(curr[0],curr[1]-1,curr[2],grid,frontier)
    return grid

# add node to frontier if its grid value is > 1 greater than v
def addLocIfGreater(x,y,v,g,f):
    if 0<=x<WIDTH and 0<=y<HEIGHT and g[x][y] > v+1:
        #print("adding" +str(x)+","+str(y)+","+str(v+1)+"prevV = "+str(g[x][y]))
        g[x][y]=v+1
        f.put([x,y,v+1])

total_time = 0
for i in range(50):
    start = time.time()
    A = dijkstraMap([[10,10,0],[30,20,0],[20,20,0]])
    end = time.time()
    total_time += end-start
print(total_time/50)
#print('\n'.join([''.join(['{:3}'.format(item) for item in row])for row in A]))
