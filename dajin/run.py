import battlecode as bc
import random
import sys
import traceback
import queue

print("pystarting")

# A GameController is the main type that you talk to the game with.
# Its constructor will connect to a running game.
gc = bc.GameController()

print("pystarted")

# It's a good idea to try to keep your bots deterministic, to make debugging easier.
# determinism isn't required, but it means that the same things will happen in every thing you run,
# aside from turns taking slightly different amounts of time due to noise.
random.seed(6137)

# let's start off with some research!
# we can queue as much as we want.
gc.queue_research(bc.UnitType.Rocket)
gc.queue_research(bc.UnitType.Worker)
gc.queue_research(bc.UnitType.Knight)

# STRATEGY CONSTANTS
FACTORIES_WANTED = 3
SEEK_KARB_ROUND = 80 # workers pathfind to initial karb until this round

# CODING CONSTANTS
MY_TEAM = gc.team()
ENEMY_TEAM = bc.Team.Red if MY_TEAM == bc.Team.Blue else bc.Team.Blue

ALL_DIRS = list(bc.Direction)

MOVE_DIRS = list(bc.Direction)
MOVE_DIRS.remove(bc.Direction.Center)

EARTH = gc.starting_map(bc.Planet.Earth)
MARS = gc.starting_map(bc.Planet.Mars)
HEIGHT = EARTH.height
WIDTH = EARTH.width

def moveableDirections(unit_id):
    ret = []
    for d in MOVE_DIRS:
        if gc.can_move(unit_id, d):
            ret.append(d)
    return ret

def randMoveDir(unit_id):
    dirs = moveableDirections(unit_id)
    if dirs:
        return random.choice(dirs)
    else:
        return bc.Direction.Center

def wander(unit_id): # pick a random movable direction:
    d = randMoveDir(unit_id) 
    tryMove(unit_id,d)

def tryMove(unit_id, d):
    if gc.is_move_ready(unit_id) and gc.can_move(unit_id, d):
        gc.move_robot(unit_id, d)

# For Worker, try to build on nearby factory blueprints. 
# return true if we built and build is still in progress
def tryBuildFactory(unit):
    adjacent = gc.sense_nearby_units_by_type(unit.location.map_location(), 2, bc.UnitType.Factory)
    for factory in adjacent:
        # Build the factory if it isn't already finished
        if not factory.structure_is_built() and gc.can_build(unit.id, factory.id):
            gc.build(unit.id, factory.id)
            # return true only if factory is not yet fully built
            return not factory.structure_is_built()
    return False


# For Worker, try to mine nearby karbonite 
# return true if we mined and there is still more karbonite nearby 
def tryMineKarbonite(unit):
    karbs = []
    for loc in gc.all_locations_within(unit.location.map_location(), 2):
        if gc.karbonite_at(loc) > 0:
            karbs.append(loc)
    if karbs: 
        gc.harvest(unit.id, unit.location.map_location().direction_to(karbs[0]))
        if len(karbs)>1 or gc.karbonite_at(karbs[0]) > 0:   
            return True
    return False


# @param goals is a list of nodes denoting goal locations (to be set to 0)
def dijkstraMap(goals):
    # instantiate initial grid with "infinite" values
    grid = [[100 for i in range(WIDTH)] for k in range(HEIGHT)]
    frontier = queue.Queue()
    for g in goals:
        grid[g[0]][g[1]]=g[2]
        frontier.put(g)

    while frontier.qsize() > 0:
        # pop the first
        curr = frontier.get()
        # check cardinal directions for locations with higher v
        # add the locations to frontier if they have higher
        addLocIfGreater(curr[0]+1,curr[1],curr[2],grid,frontier)
        addLocIfGreater(curr[0]-1,curr[1],curr[2],grid,frontier)
        addLocIfGreater(curr[0],curr[1]+1,curr[2],grid,frontier)
        addLocIfGreater(curr[0],curr[1]-1,curr[2],grid,frontier)
    return grid

# add node to frontier if its grid value is > 1 greater than v
def addLocIfGreater(x,y,v,g,f):
    if 0<=x<WIDTH and 0<=y<HEIGHT and g[x][y] > v+1 and EARTH.is_passable_terrain_at(bc.MapLocation(bc.Planet.Earth,x,y)):
        #print("adding" +str(x)+","+str(y)+","+str(v+1)+"prevV = "+str(g[x][y]))
        g[x][y]=v+1
        f.put([x,y,v+1])

# Move unit down a dijkstraMap
def walkDownMap(unit, grid):
    l = unit.location.map_location()
    x = l.x
    y = l.y
    smallestLoc = [x,y]
    smallest = grid[x][y]
    adjacents = [[x+1,y+1],[x+1,y],[x+1,y-1],[x,y-1],[x-1,y-1],[x-1,y],[x-1,y+1],[x,y+1]]
    for loc in adjacents:
        if grid[loc[0]][loc[1]] <= smallest:
            smallest = grid[loc[0]][loc[1]]
            smallestLoc = loc
    tryMove(unit.id,l.direction_to(bc.MapLocation(l.planet,smallestLoc[0],smallestLoc[1])))


# Build a Dijkstra Map for earth's karbonite
initial_karbonite_nodes = []
for x in range(WIDTH):
    for y in range(HEIGHT):
        if EARTH.initial_karbonite_at(bc.MapLocation(bc.Planet.Earth,x,y))>0:
            initial_karbonite_nodes.append([x,y,-EARTH.initial_karbonite_at(bc.MapLocation(bc.Planet.Earth,x,y))/4])
EARTH_KARBONITE_MAP = dijkstraMap(initial_karbonite_nodes)


while True:
    ROUND = gc.round()
    # We only support Python 3, which means brackets around print()
    print('pyround:', gc.round())

    # frequent try/catches are a good idea
    try:
        # count our units
        numFactories = 0
        for unit in gc.my_units():
            if unit.unit_type == bc.UnitType.Factory:
                numFactories += 1
        
        # walk through our units:
        for unit in gc.my_units():

            print("ID:"+str(unit.id))
            # first, factory logic
            if unit.unit_type == bc.UnitType.Factory:
                garrison = unit.structure_garrison()
                if len(garrison) > 0:
                    d = randMoveDir(unit.id)
                    if gc.can_unload(unit.id, d):
                        print('unloaded a knight!')
                        gc.unload(unit.id, d)
                        continue
                elif gc.can_produce_robot(unit.id, bc.UnitType.Knight):
                    gc.produce_robot(unit.id, bc.UnitType.Knight)
                    print('produced a knight!')
                    continue

            # Worker logic
            if unit.unit_type == bc.UnitType.Worker:
                if unit.location.is_on_map():
                    d = randMoveDir(unit.id)
                    # 1. look for and work on blueprints
                    if tryBuildFactory(unit):
                        # if we worked on factory, move on to next unit
                        print("worked on factory")
                        continue
                    # 2. Look for and mine Karbonite
                    elif tryMineKarbonite(unit):
                        print("mined")
                        # we mined and there's still more, stay in place and move on
                        continue
                    # 3. Walk towards karbonite
                    elif ROUND < SEEK_KARB_ROUND:
                        print("walked down")
                        walkDownMap(unit, EARTH_KARBONITE_MAP)
                    # 4. Place blueprints if needed
                    elif numFactories < FACTORIES_WANTED and gc.karbonite() > bc.UnitType.Factory.blueprint_cost() and gc.can_blueprint(unit.id, bc.UnitType.Factory, d):
                        print('blueprinted')
                        gc.blueprint(unit.id, bc.UnitType.Factory, d)
                    # 5. Wander
                    else:
                        print("wandered")
                        tryMove(unit.id,d)


            # Knight logic
            if unit.unit_type == bc.UnitType.Knight:
                if unit.location.is_on_map():
                    # Attack in range enemies
                    adjacent = gc.sense_nearby_units_by_team(unit.location.map_location(), 2, ENEMY_TEAM)
                    for other in adjacent:
                        if gc.is_attack_ready(unit.id) and gc.can_attack(unit.id, other.id):
                            print('attacked a thing!')
                            gc.attack(unit.id, other.id)
                            break
                    # Move towards enemies
                    nearby = gc.sense_nearby_units_by_team(unit.location.map_location(), 50, ENEMY_TEAM)
                    for other in nearby:
                        tryMove(unit.id,unit.location.map_location().direction_to(other.location.map_location()))
                    wander(unit.id)
            
            # Ranger logic
            #if unit.unit_type == bc.UnitType.Ranger:
            #    if unit.location.is_on_map():
            # okay, there weren't any dudes around
            # wander(unit.id)
    except Exception as e:
        print('Error:', e)
        # use this to show where the error was
        traceback.print_exc()

    # send the actions we've performed, and wait for our next turn.
    gc.next_turn()

    # these lines are not strictly necessary, but it helps make the logs make more sense.
    # it forces everything we've written this turn to be written to the manager.
    sys.stdout.flush()
    sys.stderr.flush()
