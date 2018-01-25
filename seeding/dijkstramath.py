import collections as fast

def setSize(w,h):
    global WIDTH, HEIGHT
    WIDTH = w
    HEIGHT = h

def flattenXY(x,y):
    return y*WIDTH+x

def flattenMapLoc(maploc):
    return maploc.y*WIDTH + maploc.x

def unflattenXY(flatVal):
    return flatVal%WIDTH, int(flatVal/WIDTH)

def adjacentInBounds(i):
    x0 = i % WIDTH
    y0 = int(i / WIDTH)
    adj = set()
    if x0 != 0:
        adj.add(i - 1)
        if y0 != 0:
            adj.add(i - 1 - WIDTH)
        if y0 != HEIGHT - 1:
            adj.add(i - 1 + WIDTH)
    if x0 != WIDTH - 1:
        adj.add(i + 1)
        if y0 != 0:
            adj.add(i + 1 - WIDTH)
        if y0 != HEIGHT - 1:
            adj.add(i + 1 + WIDTH)
    if y0 != HEIGHT - 1:
        adj.add(i + WIDTH)
    if y0 != 0:
        adj.add(i - WIDTH)
    return adj

# builds an adjacency graph
def adjacencyGraph(walls):
    # for every grid location in HEIGHT*WIDTH, we store an array of unsigned shorts representing open adjacents
    graph = []
    for i in range(HEIGHT * WIDTH):
        if i in walls:
            graph.append([])
        else:
            adj = adjacentInBounds(i)
            adj.difference_update(walls)
            graph.append(adj)
    return graph


# @param goals is a list of flattened coordinates and values denoting goal locations (to be set to value)
# @param walls is a adjacency graph for walls
def dijkstraMap(goals, wallGraph):
    # instantiate initial grid with "infinite" values
    grid = [100 for k in range(HEIGHT * WIDTH)]
    frontier = fast.deque()
    for g in goals:
        frontier.append(g)
        grid[g[0]] = g[1]

    while frontier:
        # pop the first
        curr = frontier.popleft()

        idx = curr[0]
        vmin = curr[1] + 1

        # check cardinal directions for locations with higher v
        # add the locations to frontier if they have higher
        for adj in wallGraph[idx]:
            if grid[adj] > vmin:
                grid[adj] = vmin
                frontier.append([adj,vmin])
    return grid


def logMap(map):
    print(''.join([('{:3}\n' if idx % WIDTH == WIDTH - 1 else '{:3}').format(cell) for idx, cell in enumerate(map)]))