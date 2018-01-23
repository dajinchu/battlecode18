import battlecode as bc
import random
import sys
import traceback
import collections as fast
import time
import math

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
gc.queue_research(bc.UnitType.Knight)
gc.queue_research(bc.UnitType.Knight)
gc.queue_research(bc.UnitType.Knight)
gc.queue_research(bc.UnitType.Rocket)
gc.queue_research(bc.UnitType.Ranger)
gc.queue_research(bc.UnitType.Healer)
gc.queue_research(bc.UnitType.Ranger)

# disable timing logs for production code
TIMING_DISABLED = False

# SPEC CONSTANTS
REPLICATE_COST = 15

# CODING CONSTANTS
MY_TEAM = gc.team()
ENEMY_TEAM = bc.Team.Red if MY_TEAM == bc.Team.Blue else bc.Team.Blue

ALL_DIRS = list(bc.Direction)

MOVE_DIRS = list(bc.Direction)
MOVE_DIRS.remove(bc.Direction.Center)

EARTHMAP = gc.starting_map(bc.Planet.Earth)
MARSMAP = gc.starting_map(bc.Planet.Mars)
THIS_PLANETMAP = gc.starting_map(gc.planet())
HEIGHT = THIS_PLANETMAP.height
WIDTH = THIS_PLANETMAP.width
MARS_WIDTH = MARSMAP.width
MARS_HEIGHT = MARSMAP.height
EARTH_WIDTH = EARTHMAP.width
EARTH_HEIGHT = EARTHMAP.height

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


# For worker try place factory blueprint
# spaces out the factories intelligently
def tryBlueprintFactory(unit):
    if gc.karbonite() > bc.UnitType.Factory.blueprint_cost():
        dirs = MOVE_DIRS
        for d in dirs:
            loc = unit.location.map_location().add(d)
            # check that the place we're thinking about blueprinting is not adjacent to existing factories
            adjacent = gc.sense_nearby_units_by_type(loc, 2, bc.UnitType.Factory)
            if not adjacent and gc.can_blueprint(unit.id, bc.UnitType.Factory, d):
                gc.blueprint(unit.id, bc.UnitType.Factory, d)
                return True
    return False


# For Worker, try to build on nearby factory blueprints.
# return true if we built and build is still in progress
def tryBuildFactory(unit):
    # First try to build directly adjacent factories
    adjacent = gc.sense_nearby_units_by_type(unit.location.map_location(), 2, bc.UnitType.Factory)
    factoryToBuild = None
    highestFactoryHealth = 0
    for factory in adjacent:
        # Build the factory if it isn't already finished
        if not factory.structure_is_built() and factory.health > highestFactoryHealth:
            factoryToBuild = factory
            highestFactoryHealth = factory.health
    if factoryToBuild and gc.can_build(unit.id, factory.id):
        gc.build(unit.id, factoryToBuild.id)
        # return true only if factory build is still in progress
        return not factory.structure_is_built()
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
def dijkstraMap(goals, walls):
    flen = 0
    # instantiate initial grid with "infinite" values
    grid = [[100 for i in range(HEIGHT)] for k in range(WIDTH)]
    frontier = fast.deque()
    for g in goals:
        frontier.append(g)
        grid[g[0]][g[1]] = g[2]
        flen += 1

    while flen:
        # pop the first
        curr = frontier.popleft()
        flen -= 1
        # set the value in the grid
        grid[curr[0]][curr[1]] = curr[2]
        # check cardinal directions for locations with higher v
        # add the locations to frontier if they have higher
        v = curr[2]
        x = curr[0] + 1
        y = curr[1]
        if 0 <= x < WIDTH and 0 <= y < HEIGHT and grid[x][y] > v + 1 and not (y * WIDTH + x in walls):
            grid[x][y] = v + 1
            frontier.append([x, y, v + 1])
            flen += 1
        x = curr[0] - 1
        y = curr[1]
        if 0 <= x < WIDTH and 0 <= y < HEIGHT and grid[x][y] > v + 1 and not (y * WIDTH + x in walls):
            grid[x][y] = v + 1
            frontier.append([x, y, v + 1])
            flen += 1
        x = curr[0]
        y = curr[1] + 1
        if 0 <= x < WIDTH and 0 <= y < HEIGHT and grid[x][y] > v + 1 and not (y * WIDTH + x in walls):
            grid[x][y] = v + 1
            frontier.append([x, y, v + 1])
            flen += 1
        x = curr[0]
        y = curr[1] - 1
        if 0 <= x < WIDTH and 0 <= y < HEIGHT and grid[x][y] > v + 1 and not (y * WIDTH + x in walls):
            grid[x][y] = v + 1
            frontier.append([x, y, v + 1])
            flen += 1
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


# Build map towards enemy
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
    for e in enemies:
        loc = e.location.map_location()
        enemyLocs.append([loc.x, loc.y, 0])

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
EARTH_KARBONITE_MAP = []


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

while True:
    ROUND = gc.round()
    # We only support Python 3, which means brackets around print()
    print('pyround:', gc.round(), 'time left:', gc.get_time_left_ms(), 'ms')
    turnBench.start()

    # frequent try/catches are a good idea
    try:
        # sort our units
        factories = []
        factoryBlueprints = []
        workers = []
        rangers = []
        knights = []
        mages = []
        healers = []
        for unit in gc.my_units():
            type = unit.unit_type
            if type == bc.UnitType.Factory:
                factories.append(unit)
                if not unit.structure_is_built():
                    factoryBlueprints.append(unit)
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
        numRangers = len(rangers)
        numHealers = len(healers)

        # update the ranger atkRange, because it can change with research.
        # SLIGHTLY BETTER TO UPDATE THIS JUST WHEN RESEARCH FINISHES INSTEAD OF POLLING EVERY TURN
        rangerAtkRange = 0  # This is dumb, but you need at least one ranger to find the atk range of the ranger
        if rangers:
            rangerAtkRange = rangers[0].attack_range()

        # Refresh enemy map
        enemyMapBench.start()
        ENEMY_MAP = mapToEnemy(THIS_PLANETMAP)
        enemyMapBench.end()
        RANGER_MAP = []
        if rangers:
            rangerMapBench.start()
            RANGER_MAP = rangerMap(THIS_PLANETMAP, rangerAtkRange)
            rangerMapBench.end()

        # Healer map. Directs healers to get near rangers to heal them
        HEALER_MAP = []
        HURT_ALLIES = []
        if healers:
            healerMapBench.start()
            goals = []
            for ally in rangers:
                if ally.location.is_on_map():
                    loc = ally.location.map_location()
                    goals.append([loc.x, loc.y, ally.health - ally.max_health])
                    if ally.health < ally.max_health :
                        HURT_ALLIES.append(ally.id)
            HEALER_MAP = dijkstraMap(goals, THIS_PLANET_WALLS)
            healerMapBench.end()

        # refresh units_wanted
        WORKERS_WANTED = 4 + int(TOTAL_EARTH_KARBONITE/100)
        FACTORIES_WANTED = 3 + int(gc.karbonite()/300)

        # refresh factory map
        FACTORY_MAP = []
        if factoryBlueprints:
            factoryMapBench.start()
            factLocs = [f.location.map_location() for f in factoryBlueprints]
            FACTORY_MAP = adjacentToMap(factLocs)
            factoryMapBench.end()

        # refresh karbonite map
        if ROUND % 10 == 1:
            EARTH_KARBONITE_MAP = updateKarbonite()

        rangerBench.start()
        for unit in rangers:
            # Ranger logic
            if unit.location.is_on_map():
                walkDownMap(unit, RANGER_MAP)
                enemies = senseEnemies(unit.location.map_location(), unit.attack_range())
                for e in enemies:
                    if gc.is_attack_ready(unit.id) and gc.can_attack(unit.id, e.id):
                        gc.attack(unit.id, e.id)
        rangerBench.end()

        healerBench.start()
        for unit in healers:
            # Ranger logic
            if unit.location.is_on_map():
                walkDownMap(unit, HEALER_MAP)
                if gc.is_heal_ready(unit.id):
                    for ally_id in HURT_ALLIES:
                        if gc.can_heal(unit.id, ally_id):
                            gc.heal(unit.id, ally_id)
                            break
        healerBench.end()

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
            elif numWorkers == 0 and gc.can_produce_robot(unit.id, bc.UnitType.Worker):
                gc.produce_robot(unit.id, bc.UnitType.Worker)
                numWorkers += 1
            #elif numRangers > (1+numHealers) * 8 and gc.can_produce_robot(unit.id,bc.UnitType.Healer):
            #    gc.produce_robot(unit.id, bc.UnitType.Healer)
            #    numHealers += 1
            elif gc.can_produce_robot(unit.id, bc.UnitType.Knight):
                gc.produce_robot(unit.id, bc.UnitType.Knight)
                numRangers += 1
                continue
        factoryBench.end()

        workerBench.start()
        # Worker logic
        for unit in workers:
            if unit.location.is_on_map():
                d = randMoveDir(unit)
                # 1. Replicate if needed
                if numWorkers < WORKERS_WANTED and gc.karbonite() > REPLICATE_COST and gc.can_replicate(unit.id, d):
                    gc.replicate(unit.id, d)
                    numWorkers += 1
                # 2. look for and work on blueprints
                elif tryBuildFactory(unit):
                    # if we worked on factory, move on to next unit
                    # print("worked on factory")
                    continue
                elif FACTORY_MAP and FACTORY_MAP[unit.location.map_location().x][unit.location.map_location().y] < 4:
                    walkDownMap(unit, FACTORY_MAP)
                    continue
                # 0. Place blueprints if needed
                elif numFactories < FACTORIES_WANTED and tryBlueprintFactory(unit):
                    # print('blueprinted')
                    numFactories += 1
                    continue
                # 3. Look for and mine Karbonite
                elif tryMineKarbonite(unit):
                    # print("mined")
                    # we mined and there's still more, stay in place and move on
                    continue
                # 4. Walk towards karbonite
                elif EARTH_KARBONITE_MAP[unit.location.map_location().x][unit.location.map_location().y] < 5:
                    # print("walked down")
                    walkDownMap(unit, EARTH_KARBONITE_MAP)
                # 5. Wander
                else:
                    # print("wandered")
                    tryMove(unit, d)
        workerBench.end()

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
                '''nearby = gc.sense_nearby_units_by_team(unit.location.map_location(), 50, ENEMY_TEAM)
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