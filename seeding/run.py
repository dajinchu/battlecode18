import battlecode as bc
import random
import sys
import traceback
import collections as fast
import time
import math
import fakerocketmath as rocketmath

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
# gc.queue_research(bc.UnitType.Rocket)
gc.queue_research(bc.UnitType.Healer)
gc.queue_research(bc.UnitType.Rocket)
gc.queue_research(bc.UnitType.Ranger)
gc.queue_research(bc.UnitType.Healer)
gc.queue_research(bc.UnitType.Ranger)

# disable timing logs for production code
TIMING_DISABLED = True

# SPEC CONSTANTS
REPLICATE_COST = 30
ROCKET_COST = 75

# CODING CONSTANTS
MY_TEAM = gc.team()
ENEMY_TEAM = bc.Team.Red if MY_TEAM == bc.Team.Blue else bc.Team.Blue

ALL_DIRS = list(bc.Direction)

MOVE_DIRS = list(bc.Direction)
MOVE_DIRS.remove(bc.Direction.Center)

# Order to attack units. First in list is higher priority
UNIT_PRIORITY = [bc.UnitType.Factory,bc.UnitType.Rocket,bc.UnitType.Mage,bc.UnitType.Healer,bc.UnitType.Ranger,bc.UnitType.Knight,bc.UnitType.Worker]

EARTHMAP = gc.starting_map(bc.Planet.Earth)
MARSMAP = gc.starting_map(bc.Planet.Mars)
THIS_PLANETMAP = gc.starting_map(gc.planet())
HEIGHT = THIS_PLANETMAP.height
WIDTH = THIS_PLANETMAP.width
MARS_WIDTH = MARSMAP.width
MARS_HEIGHT = MARSMAP.height
EARTH_WIDTH = EARTHMAP.width
EARTH_HEIGHT = EARTHMAP.height

# Keeping track of enemy initial spawns and factory locations, deleting if we seem them no longer there
ENEMY_LOCATION_MEMORY = {unit.location.map_location().y*WIDTH+unit.location.map_location().x
                         for unit in THIS_PLANETMAP.initial_units if unit.team != MY_TEAM}

# Instead of instantiating new MapLocations constantly, we make them ALL at the start and recycle them
# I AM NOT SURE IF THIS ACTUALLY SAVES TIME, (doesn't appear to hurt though)
EARTH_MAPLOCATIONS = [bc.MapLocation(bc.Planet.Earth, i % EARTH_WIDTH, int(i / EARTH_WIDTH)) for i in
                      range(EARTH_WIDTH * EARTH_HEIGHT)]
MARS_MAPLOCATIONS = [bc.MapLocation(bc.Planet.Mars, i % MARS_WIDTH, int(i / MARS_WIDTH)) for i in
                     range(MARS_WIDTH * MARS_HEIGHT)]


def MapLocation(planetEnum, x, y):
    if planetEnum == bc.Planet.Earth:
        return EARTH_MAPLOCATIONS[y * EARTH_WIDTH + x]
    else:
        return MARS_MAPLOCATIONS[y * MARS_WIDTH + x]


def getWalls(planetmap):
    impass = set()
    for x in range(planetmap.width):
        for y in range(planetmap.height):
            if not planetmap.is_passable_terrain_at(MapLocation(planetmap.planet, x, y)):
                impass.add(y * planetmap.width + x)
    return impass


WATER = getWalls(EARTHMAP)
ROCKY = getWalls(MARSMAP)
THIS_PLANET_WALLS = WATER if gc.planet() == bc.Planet.Earth else ROCKY


def occupiableDirections(loc):
    ret = []
    for d in MOVE_DIRS:
        l = loc.add(d)
        if 0 <= l.x < WIDTH and 0 <= l.y < HEIGHT and gc.is_occupiable(l):
            ret.append(d)
    return ret


def randMoveDir(unit):
    dirs = occupiableDirections(unit.location.map_location())
    if dirs:
        return random.choice(dirs)
    else:
        return bc.Direction.Center


def wander(unit):  # pick a random movable direction:
    d = randMoveDir(unit)
    tryMove(unit, d)


def tryMove(unit, d):
    if gc.is_move_ready(unit.id) and gc.can_move(unit.id, d):
        gc.move_robot(unit.id, d)


def senseEnemies(loc, radius2):
    return gc.sense_nearby_units_by_team(loc, radius2, ENEMY_TEAM)


def senseAdjacentEnemies(loc):
    return senseEnemies(loc, 2)


def senseAllEnemies(planet):
    return senseEnemies(MapLocation(planet, 0, 0), 1000)


def senseAllByType(planet, unitType):
    return gc.sense_nearby_units_by_type(MapLocation(planet, 0, 0), 1000, unitType)

def senseAllies(loc,radius2):
    return gc.sense_nearby_units_by_team(loc, radius2, MY_TEAM)

def senseAdjacentAllies(loc):
    return senseAllies(loc, 2)


# For worker try place  blueprint
# spaces out the blueprints intelligently
def tryBlueprint(unit, blueprintType):
    if gc.karbonite() > blueprintType.blueprint_cost():
        dirs = MOVE_DIRS
        for d in dirs:
            loc = unit.location.map_location().add(d)
            # check that the place we're thinking about blueprinting is not adjacent to existing factories
            adjacent = gc.sense_nearby_units_by_type(loc, 2, blueprintType)
            if not adjacent and gc.can_blueprint(unit.id, blueprintType, d):
                gc.blueprint(unit.id, blueprintType, d)
                return True
    return False


# For Worker, try to build on nearby blueprints.
# return true if we built and build is still in progress
def tryBuildStructure(unit):
    # First try to build directly adjacent factories
    adjfactories = gc.sense_nearby_units_by_type(unit.location.map_location(), 2, bc.UnitType.Factory)
    adjrockets = gc.sense_nearby_units_by_type(unit.location.map_location(), 2, bc.UnitType.Rocket)
    structureToBuild = None
    highestHealth = -1
    for s in adjfactories:
        # Build the factory if it isn't already finished
        if not s.structure_is_built() and s.health > highestHealth:
            structureToBuild = s
            highestHealth = s.health
    for s in adjrockets:
        # Build the factory if it isn't already finished
        if not s.structure_is_built() and s.health > highestHealth:
            structureToBuild = s
            highestHealth = s.health
    if structureToBuild and gc.can_build(unit.id, structureToBuild.id):
        gc.build(unit.id, structureToBuild.id)
        # return true only if factory build is still in progress
        return not structureToBuild.structure_is_built()
    else:
        return False


# For Worker, try to mine nearby karbonite
# return true if we mined and there is still more karbonite nearby
def tryMineKarbonite(unit):
    karbs = []
    for loc in gc.all_locations_within(unit.location.map_location(), 2):
        if gc.karbonite_at(loc) > 0:
            karbs.append(loc)
    if karbs:
        dirTo = unit.location.map_location().direction_to(karbs[0])
        if gc.can_harvest(unit.id, dirTo):
            gc.harvest(unit.id, dirTo)
            if len(karbs) > 1 or gc.karbonite_at(karbs[0]) > 0:
                return True
    return False


# @param goals is a list of MapLocations denoting goal locations (to be set to 0)
# @param walls is a Set denoting the places that can't be walked through
def dijkstraMap(goals,walls):
    # instantiate initial grid with "infinite" values
    grid = [[100 for i in range(HEIGHT)] for k in range(WIDTH)]
    frontier = fast.deque()
    for g in goals:
        frontier.append(g)
        grid[g[0]][g[1]] = g[2]

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
        if x0 != WIDTH-1:
            x = x0 + 1
            y = y0
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


# Move unit down a dijkstraMap
def walkDownMap(unit, grid):
    l = unit.location.map_location()
    x = l.x
    y = l.y
    smallestLoc = [x, y]
    smallest = grid[x][y]
    adjacents = [[x + 1, y + 1], [x + 1, y], [x + 1, y - 1], [x, y - 1], [x - 1, y - 1], [x - 1, y], [x - 1, y + 1],
                 [x, y + 1]]
    for loc in adjacents:
        if 0 <= loc[0] < WIDTH and 0 <= loc[1] < HEIGHT and grid[loc[0]][loc[1]] <= smallest and gc.is_occupiable(
                MapLocation(l.planet, loc[0], loc[1])):
            smallest = grid[loc[0]][loc[1]]
            smallestLoc = loc
    tryMove(unit, l.direction_to(MapLocation(l.planet, smallestLoc[0], smallestLoc[1])))


# Move unit up a dijkstraMap
def walkUpMap(unit, grid):
    l = unit.location.map_location()
    x = l.x
    y = l.y
    biggestLoc = [x, y]
    biggest = grid[x][y]
    adjacents = [[x + 1, y + 1], [x + 1, y], [x + 1, y - 1], [x, y - 1], [x - 1, y - 1], [x - 1, y], [x - 1, y + 1],
                 [x, y + 1]]
    for loc in adjacents:
        if 0 <= loc[0] < WIDTH and 0 <= loc[1] < HEIGHT and grid[loc[0]][loc[1]] >= biggest and gc.is_occupiable(
                MapLocation(l.planet, loc[0], loc[1])):
            biggest = grid[loc[0]][loc[1]]
            biggestLoc = loc
    tryMove(unit, l.direction_to(MapLocation(l.planet, biggestLoc[0], biggestLoc[1])))


# Move unit towards goal value on dijkstraMap
def walkToValue(unit, grid, goalValue):
    loc = unit.location.map_location()
    x = loc.x
    y = loc.y
    if grid[x][y] > goalValue:
        walkDownMap(unit, grid)
    elif grid[x][y] < goalValue:
        walkUpMap(unit, grid)
    # if currvalue is goalvalue, just don't move


# Takes list of maplocations, makes map to all spots adjacent to those locations
# useful for pathing buildings into places where they can work on blueprints
def adjacentToMap(mapLocs):
    goals = []
    for loc in mapLocs:
        adjacent = gc.all_locations_within(loc, 2)
        for adjLoc in adjacent:
            if not adjLoc.x * WIDTH + adjLoc.y in THIS_PLANET_WALLS:  # and not gc.is_occupiable(MapLocation(THIS_PLANETMAP.planet,adjLoc.x,adjLoc.y)):
                goals.append([adjLoc.x, adjLoc.y, 0])
    return dijkstraMap(goals, THIS_PLANET_WALLS)

# Produces an approximate dijkstra map of the enemy attack ranges.
def enemyAttackMap(planetMap):
    eList  = []
    for e in senseAllEnemies(planetMap.planet):
        loc = e.location.map_location()
        if e.unit_type == bc.UnitType.Ranger or e.unit_type == bc.UnitType.Knight or e.unit_type == bc.UnitType.Mage:
            eList.append([loc.x,loc.y,-int(math.sqrt(e.attack_range()))])
    return dijkstraMap(eList,[])

# Produces a map for fleeing, using the map of enemy attack ranges
def fleeMap(enemyAttackMap):
    goalLocs = []
    for x, col in enumerate(enemyAttackMap):
        for y, cell in enumerate(col):
            if cell < 0 and not (y*WIDTH+x in THIS_PLANET_WALLS):
                goalLocs.append([x, y, cell])
    return dijkstraMap(goalLocs,THIS_PLANET_WALLS)

# Build map towards enemy TODO UNUSED
def mapToEnemy(planetMap):
    s = time.time()
    enemies = senseAllEnemies(planetMap.planet)
    enemyLocs = []
    walls = set()
    for f in senseAllByType(planetMap.planet, bc.UnitType.Factory):
        walls.add(f.location.map_location().y * WIDTH + f.location.map_location().x)
    walls.update(THIS_PLANET_WALLS)
    for e in enemies:
        loc = e.location.map_location()
        enemyLocs.append([loc.x, loc.y, 0])
    if not enemies:
        enemyLocs = [[unit.location.map_location().x, unit.location.map_location().y, 0] for unit in
                     THIS_PLANETMAP.initial_units if unit.team != MY_TEAM]
    m = dijkstraMap(enemyLocs, walls)
    # print('\n'.join([''.join(['{:4}'.format(item) for item in row])for row in m]))
    # print("build enemy map took " + str(time.time()-s))
    return m


# Build map for rangers where goals are in range
def rangerMap(planetMap, atkRange):
    enemies = senseAllEnemies(planetMap.planet)
    enemyLocs = []
    walls = set()
    for f in senseAllByType(planetMap.planet, bc.UnitType.Factory):
        walls.add(f.location.map_location().x * WIDTH + f.location.map_location().y)
    walls.update(THIS_PLANET_WALLS)
    if enemies:
        for e in enemies:
            loc = e.location.map_location()
            enemyLocs.append([loc.x, loc.y, 0])
    # If we can't see any enemies head towards where we last saw them. currently only remembers factory locations
    elif ENEMY_LOCATION_MEMORY:
        for loc in ENEMY_LOCATION_MEMORY:
            enemyLocs.append([loc%WIDTH,int(loc/WIDTH),0])
    # find distances to enemy, ignoring walls, because rangers can shoot over
    distMap = dijkstraMap(enemyLocs, [])

    goalLocs = []

    realAtkRange = int(math.sqrt(atkRange))
    # now find where the distance is right for rangers
    for x, col in enumerate(distMap):
        for y, cell in enumerate(col):
            if cell == realAtkRange:
                goalLocs.append([x, y, 0])

    # now pathfind to those sweet spot
    rangerMap = dijkstraMap(goalLocs, walls)

    return rangerMap


TOTAL_EARTH_KARBONITE = 0
KARBONITE_LOCS = []

# Iterate through all spots to find karbonite
# count total karbonite and record their locations and amounts
def initKarbonite():
    global TOTAL_EARTH_KARBONITE
    for x in range(WIDTH):
        for y in range(HEIGHT):
            k = EARTHMAP.initial_karbonite_at(MapLocation(bc.Planet.Earth, x, y))
            if k >= 5:
                KARBONITE_LOCS.append([x, y, int(-k / 4)])
            TOTAL_EARTH_KARBONITE += k


initKarbonite()


# Build a Dijkstra Map for earth's karbonite using vision and initial
def updateKarbonite():
    global TOTAL_EARTH_KARBONITE
    KARBONITE_LOCS[:] = [k for k in KARBONITE_LOCS if
                         not gc.can_sense_location(MapLocation(bc.Planet.Earth, k[0], k[1]))
                         or gc.karbonite_at(MapLocation(bc.Planet.Earth, k[0], k[1]))]
    for k in KARBONITE_LOCS:
        TOTAL_EARTH_KARBONITE += k[2]
    return dijkstraMap(KARBONITE_LOCS, WATER)

def updateEnemyMemory():
    global ENEMY_LOCATION_MEMORY
    deleteLocs = set()
    # delete if we see it is now empty
    for loc in ENEMY_LOCATION_MEMORY:
        maploc = MapLocation(THIS_PLANETMAP.planet,loc%WIDTH,int(loc/WIDTH))
        if gc.can_sense_location(maploc):
            if not gc.has_unit_at_location(maploc) or gc.sense_unit_at_location(maploc).team == MY_TEAM:
                deleteLocs.add(loc)
    ENEMY_LOCATION_MEMORY.difference_update(deleteLocs)
    for e in senseAllByType(THIS_PLANETMAP.planet, bc.UnitType.Factory):
        if e.team != MY_TEAM:
            loc = e.location.map_location()
            ENEMY_LOCATION_MEMORY.add(loc.y*WIDTH + loc.x)

class Benchmark:
    canStart = True

    def __init__(self, name):
        self.name = name

    def start(self):
        if TIMING_DISABLED:
            return
        if self.canStart:
            self.canStart = False
            self.startt = time.time()
        else:
            print("CALLED BENCHMARK.START AGAIN BEFORE CALLING .END()")

    def end(self):
        if TIMING_DISABLED:
            return
        print(self.name, "took ", 1000 * (time.time() - self.startt), "ms")
        self.canStart = True


# Create benchmarks for different parts
turnBench = Benchmark("Full turn")
enemyMapBench = Benchmark("Creating enemy map")
rangerMapBench = Benchmark("Creating ranger map")
healerMapBench = Benchmark("Creating healer map")
factoryMapBench = Benchmark("Creating factory map")
karboniteMapBench = Benchmark("Creating karbonite map")
rangerBench = Benchmark("Handling rangers")
healerBench = Benchmark("Handling healers")
factoryBench = Benchmark("Handling factories")
workerBench = Benchmark("Handling workers")


# Dijkstra maps
ENEMY_RANGE_MAP = []
FLEE_MAP = []
RANGER_MAP = []
HEALER_MAP = []
BLUEPRINT_MAP = []
EARTH_KARBONITE_MAP = []
ROCKET_MAP = []
ID_GO_TO_ROCKET = set()

while True:
    ROUND = gc.round()
    # We only support Python 3, which means brackets around print()
    if TIMING_DISABLED:
        print('pyround:', gc.round(), 'time left:', gc.get_time_left_ms(), 'ms')
    turnBench.start()

    # frequent try/catches are a good idea
    try:
        # sort our units
        factories = []
        factoryBlueprints = []
        rockets = []
        rocketBlueprints = []
        workers = []
        rangers = []
        knights = []
        mages = []
        healers = []
        for unit in gc.my_units():
            type = unit.unit_type
            if type == bc.UnitType.Factory:
                if unit.structure_is_built():
                    factories.append(unit)
                else:
                    factoryBlueprints.append(unit)
            elif type == bc.UnitType.Rocket:
                if unit.structure_is_built():
                    rockets.append(unit)
                else:
                    rocketBlueprints.append(unit)
            elif type == bc.UnitType.Worker:
                workers.append(unit)
            elif type == bc.UnitType.Ranger:
                rangers.append(unit)
            elif type == bc.UnitType.Knight:
                knights.append(unit)
            elif type == bc.UnitType.Mage:
                mages.append(unit)
            elif type == bc.UnitType.Healer:
                healers.append(unit)
        numWorkers = len(workers)
        numFactories = len(factories) + len(factoryBlueprints)
        numRockets = len(rockets) + len(rocketBlueprints)
        numRangers = len(rangers)
        numHealers = len(healers)
        allBlueprints = factoryBlueprints + rocketBlueprints

        # update the ranger atkRange, because it can change with research.
        # SLIGHTLY BETTER TO UPDATE THIS JUST WHEN RESEARCH FINISHES INSTEAD OF POLLING EVERY TURN
        rangerAtkRange = 0  # This is dumb, but you need at least one ranger to find the atk range of the ranger
        if rangers:
            rangerAtkRange = rangers[0].attack_range()

        # update our memory of enemy location
        updateEnemyMemory()

        # update maps ONLY if we have computation time for it. It's okay to use outdated maps
        if gc.get_time_left_ms() > 400:
            # Refresh enemy map
            ENEMY_RANGE_MAP = enemyAttackMap(THIS_PLANETMAP)
            FLEE_MAP = fleeMap(ENEMY_RANGE_MAP)
            #print('\n'.join([''.join(['{:3}'.format(item) for item in row]) for row in ENEMY_RANGE_MAP]))

            enemyMapBench.start()
            #ENEMY_MAP = mapToEnemy(THIS_PLANETMAP)
            enemyMapBench.end()
            RANGER_MAP = []
            if rangers:
                rangerMapBench.start()
                RANGER_MAP = rangerMap(THIS_PLANETMAP, rangerAtkRange)
                rangerMapBench.end()

            # Healer map. Directs healers to get near rangers to heal them
            HEALER_MAP = []
            if healers:
                healerMapBench.start()
                goals = []
                for ally in rangers:
                    if ally.health < ally.max_health and ally.location.is_on_map():
                        loc = ally.location.map_location()
                        goals.append([loc.x, loc.y, int((ally.health - ally.max_health)/10)])
                HEALER_MAP = dijkstraMap(goals, THIS_PLANET_WALLS)
                healerMapBench.end()

            # refresh blueprint map
            BLUEPRINT_MAP = []
            if allBlueprints:
                factoryMapBench.start()
                blueprintLocs = [f.location.map_location() for f in allBlueprints]
                BLUEPRINT_MAP = adjacentToMap(blueprintLocs)
                factoryMapBench.end()

            # refresh rocket map
            ROCKET_MAP = []
            if rockets:
                rocketlocs = [f.location.map_location() for f in rockets if len(f.structure_garrison())<f.structure_max_capacity()]
                ROCKET_MAP = adjacentToMap(rocketlocs)

        # refresh karbonite map
        if ROUND % 10 == 1:
            EARTH_KARBONITE_MAP = updateKarbonite()

        # refresh units_wanted TODO MAGIC NUMBERS
        WORKERS_WANTED = 4 + int(TOTAL_EARTH_KARBONITE/150)
        FACTORIES_WANTED = 3 + int(gc.karbonite()/300)
        ROCKETS_WANTED = 0 if ROUND < 500 else int((numRangers+numHealers)/(8+(700-ROUND)/50))


        # collect hurt rangers for healers to heal
        HURT_ALLIES = []
        if healers:
            for ally in rangers:
                if ally.location.is_on_map():
                    if ally.health < ally.max_health:
                        HURT_ALLIES.append(ally.id)

        # rockets need to processed first so they can load units
        ID_GO_TO_ROCKET = set()
        for unit in rockets:
            garrison = unit.structure_garrison()
            garSize = len(garrison)
            # on earth
            if unit.location.is_on_planet(EARTHMAP.planet):
                # If we are not full, load up
                if garSize < unit.structure_max_capacity():
                    adjacent = senseAdjacentAllies(unit.location.map_location())
                    for unit2 in adjacent:
                        if unit2.unit_type != bc.UnitType.Worker and gc.can_load(unit.id, unit2.id):
                            gc.load(unit.id, unit2.id)
                            garSize+=1
                # if we're still not full tell some dudes to come here
                if garSize < unit.structure_max_capacity():
                    nearby = senseAllies(unit.location.map_location(),5)
                    toldToCome = 0
                    for unit2 in nearby:
                        if unit2.unit_type == bc.UnitType.Ranger or unit2.unit_type == bc.UnitType.Healer:
                            ID_GO_TO_ROCKET.add(unit2.id)
                            toldToCome += 1
                        if toldToCome >= unit.structure_max_capacity() - garSize:
                            break
                # we are full, now check if it's a good time to launch, then launch
                elif rocketmath.shouldILaunch(ROUND):
                    loc = rocketmath.computeDestination(MARS_WIDTH,MARS_HEIGHT,ROCKY)
                    # convert the loc we got back to a MapLocation
                    destination = MapLocation(MARSMAP.planet,loc%MARS_WIDTH,int(loc/MARS_HEIGHT))
                    if gc.can_launch_rocket(unit.id,destination):
                        gc.launch_rocket(unit.id, destination)
            # On mars
            else:
                for unit2 in garrison:
                    d = randMoveDir(unit)
                    if gc.can_unload(unit.id, d):
                        # print('unloaded a knight!')
                        gc.unload(unit.id, d)

        rangerBench.start()
        for unit in rangers:
            # Ranger logic
            if unit.location.is_on_map():
                if gc.is_attack_ready(unit.id):
                    enemies = senseEnemies(unit.location.map_location(), unit.attack_range())
                    if enemies:
                        target = enemies[0]
                        targetPriority = UNIT_PRIORITY.index(enemies[0].unit_type)
                        for e in enemies:
                            priorityLevel = UNIT_PRIORITY.index(e.unit_type)
                            if priorityLevel < targetPriority:
                                target = e
                                targetPriority = priorityLevel
                            elif priorityLevel == targetPriority and e.health < target.health:
                                target = e
                        if gc.can_attack(unit.id, target.id):
                            gc.attack(unit.id, target.id)
                if unit.id in ID_GO_TO_ROCKET:
                    walkDownMap(unit,ROCKET_MAP)
                elif unit.health < 170 and ENEMY_RANGE_MAP[unit.location.map_location().x][unit.location.map_location().y] < 3:
                    walkUpMap(unit,FLEE_MAP)
                else:
                    walkDownMap(unit, RANGER_MAP)
        rangerBench.end()

        healerBench.start()
        for unit in healers:
            # Ranger logic
            if unit.location.is_on_map():
                if gc.is_heal_ready(unit.id):
                    for ally_id in HURT_ALLIES:
                        if gc.can_heal(unit.id, ally_id):
                            gc.heal(unit.id, ally_id)
                            break
                if unit.id in ID_GO_TO_ROCKET:
                    walkDownMap(unit,ROCKET_MAP)
                elif ENEMY_RANGE_MAP[unit.location.map_location().x][unit.location.map_location().y] < 5:
                    walkUpMap(unit, FLEE_MAP)
                else:
                    walkDownMap(unit, HEALER_MAP)
        healerBench.end()

        workerBench.start()
        # Worker logic
        for unit in workers:
            if unit.location.is_on_map():
                d = randMoveDir(unit) #TODO let workers act and move in the same turn
                # 1. Replicate if needed
                if numWorkers < WORKERS_WANTED and gc.karbonite() > REPLICATE_COST and gc.can_replicate(unit.id, d):
                    gc.replicate(unit.id, d)
                    numWorkers += 1
                # 2. look for and work on blueprints
                elif tryBuildStructure(unit):
                    # if we worked on factory, move on to next unit
                    # print("worked on factory")
                    continue
                elif BLUEPRINT_MAP and BLUEPRINT_MAP[unit.location.map_location().x][unit.location.map_location().y] < 4:
                    walkDownMap(unit, BLUEPRINT_MAP)
                    continue
                # Run away!
                elif ENEMY_RANGE_MAP[unit.location.map_location().x][unit.location.map_location().y] < 3:
                    walkUpMap(unit,FLEE_MAP)
                # 0. Place blueprints if needed
                elif numFactories < FACTORIES_WANTED and tryBlueprint(unit, bc.UnitType.Factory):
                    # print('blueprinted')
                    numFactories += 1
                    continue
                # 3. Look for and mine Karbonite
                elif tryMineKarbonite(unit):
                    # print("mined")
                    # we mined and there's still more, stay in place and move on
                    continue
                # 4. Walk towards karbonite
                elif numRockets < ROCKETS_WANTED and tryBlueprint(unit, bc.UnitType.Rocket):
                    # print('blueprinted')
                    numRockets += 1
                    continue
                elif EARTH_KARBONITE_MAP[unit.location.map_location().x][unit.location.map_location().y] < 5:
                    # print("walked down")
                    walkDownMap(unit, EARTH_KARBONITE_MAP)
                # 5. Wander
                else:
                    # print("wandered")
                    tryMove(unit, d)
        workerBench.end()

        factoryBench.start()
        # Factory logic
        for unit in factories:
            garrison = unit.structure_garrison()
            if len(garrison) > 0:
                d = randMoveDir(unit)
                if gc.can_unload(unit.id, d):
                    # print('unloaded a knight!')
                    gc.unload(unit.id, d)
                    continue
            if numWorkers < WORKERS_WANTED and gc.can_produce_robot(unit.id, bc.UnitType.Worker):
                gc.produce_robot(unit.id, bc.UnitType.Worker)
                numWorkers += 1
            # don't produce units if we need the karbonite for rocket building
            if ROCKETS_WANTED > 0 and gc.karbonite() < ROCKET_COST:
                continue
            elif numRangers > (1+numHealers) * 4 and gc.can_produce_robot(unit.id,bc.UnitType.Healer):
                gc.produce_robot(unit.id, bc.UnitType.Healer)
                numHealers += 1
            elif gc.can_produce_robot(unit.id, bc.UnitType.Ranger):
                gc.produce_robot(unit.id, bc.UnitType.Ranger)
                numRangers += 1
                continue
        factoryBench.end()

        '''
        for unit in knights:
            if unit.location.is_on_map():
                # Attack in range enemies
                adjacent = senseAdjacentEnemies(unit.location.map_location())
                for other in adjacent:
                    if gc.is_attack_ready(unit.id) and gc.can_attack(unit.id, other.id):
                        # print('attacked a thing!')
                        gc.attack(unit.id, other.id)
                        break
                # Move towards enemies
                walkDownMap(unit, ENEMY_MAP)
                nearby = gc.sense_nearby_units_by_team(unit.location.map_location(), 50, ENEMY_TEAM)
                for other in nearby:
                    tryMove(unit,unit.location.map_location().direction_to(other.location.map_location()))
                wander(unit.id)
                
        '''
            # okay, there weren't any dudes around
            # wander(unit.id)
    except Exception as e:
        print('Error:', e)
        # use this to show where the error was
        traceback.print_exc()

    turnBench.end()
    # send the actions we've performed, and wait for our next turn.
    gc.next_turn()

    # these lines are not strictly necessary, but it helps make the logs make more sense.
    # it forces everything we've written this turn to be written to the manager.
    sys.stdout.flush()
    sys.stderr.flush()