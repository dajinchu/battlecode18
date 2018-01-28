import battlecode as bc
import random
import sys
import traceback
from enum import Enum
import time
import math
import rocketmath
#import fakerocketmath as rocketmath
import dijkstramath as dmap


print("pystarting")

# A GameController is the main type that you talk to the game with.
# Its constructor will connect to a running game.
gc = bc.GameController()

print("pystarted")

# It's a good idea to try to keep your bots deterministic, to make debugging easier.
# determinism isn't required, but it means that the same things will happen in every thing you run,
# aside from turns taking slightly different amounts of time due to noise.
random.seed(6137)

# disable timing logs for production code
TIMING_DISABLED = False

# SPEC CONSTANTS
REPLICATE_COST = 60
ROCKET_COST = 150

# CODING CONSTANTS
MY_TEAM = gc.team()
ENEMY_TEAM = bc.Team.Red if MY_TEAM == bc.Team.Blue else bc.Team.Blue

ALL_DIRS = list(bc.Direction)

MOVE_DIRS = list(bc.Direction)
MOVE_DIRS.remove(bc.Direction.Center)

# Order to attack units. First in list is higher priority
RANGER_PRIORITY = [bc.UnitType.Mage,bc.UnitType.Healer,bc.UnitType.Ranger,bc.UnitType.Knight,bc.UnitType.Worker,bc.UnitType.Factory,bc.UnitType.Rocket]
KNIGHT_PRIORITY = [bc.UnitType.Factory,bc.UnitType.Mage,bc.UnitType.Healer,bc.UnitType.Ranger,bc.UnitType.Knight,bc.UnitType.Worker,bc.UnitType.Rocket]
OVERCHARGE_PRIORITY = [bc.UnitType.Mage,bc.UnitType.Ranger,bc.UnitType.Knight]

COMBAT_UNITTYPE = {bc.UnitType.Mage,bc.UnitType.Ranger,bc.UnitType.Knight,bc.UnitType.Healer}

EARTHMAP = gc.starting_map(bc.Planet.Earth)
MARSMAP = gc.starting_map(bc.Planet.Mars)
THIS_PLANETMAP = gc.starting_map(gc.planet())
HEIGHT = THIS_PLANETMAP.height
WIDTH = THIS_PLANETMAP.width
MARS_WIDTH = MARSMAP.width
MARS_HEIGHT = MARSMAP.height
EARTH_WIDTH = EARTHMAP.width
EARTH_HEIGHT = EARTHMAP.height

dmap.setSize(WIDTH,HEIGHT)

# Keeping track of enemy initial spawns and factory locations, deleting if we seem them no longer there
ENEMY_LOCATION_MEMORY = {unit.location.map_location().y*WIDTH+unit.location.map_location().x
                         for unit in THIS_PLANETMAP.initial_units if unit.team != MY_TEAM}

# Instead of instantiating new MapLocations constantly, we make them ALL at the start and recycle them
# I AM NOT SURE IF THIS ACTUALLY SAVES TIME, (doesn't appear to hurt though)
EARTH_MAPLOCATIONS = [bc.MapLocation(bc.Planet.Earth, i % EARTH_WIDTH, int(i / EARTH_WIDTH)) for i in
                      range(EARTH_WIDTH * EARTH_HEIGHT)]
MARS_MAPLOCATIONS = [bc.MapLocation(bc.Planet.Mars, i % MARS_WIDTH, int(i / MARS_WIDTH)) for i in
                     range(MARS_WIDTH * MARS_HEIGHT)]

orbitpattern = gc.orbit_pattern
# b = (orbitpattern.center * math.pi) / 100
rocketmath.setup(50, 2, 125)

def MapLocation(planetEnum, x, y):
    if planetEnum == bc.Planet.Earth:
        return EARTH_MAPLOCATIONS[y * EARTH_WIDTH + x]
    else:
        return MARS_MAPLOCATIONS[y * MARS_WIDTH + x]

def MapLocationFlat(planetEnum, flatxy):
    if planetEnum == bc.Planet.Earth:
        return EARTH_MAPLOCATIONS[flatxy]
    else:
        return MARS_MAPLOCATIONS[flatxy]

def getWalls(planetmap):
    impass = set()
    for x in range(planetmap.width):
        for y in range(planetmap.height):
            if not planetmap.is_passable_terrain_at(MapLocation(planetmap.planet, x, y)):
                impass.add(y * planetmap.width + x)
    return impass

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
    return senseEnemies(MapLocation(planet, 0, 0), 10000)


def senseAllByType(planet, unitType):
    return gc.sense_nearby_units_by_type(MapLocation(planet, 0, 0), 10000, unitType)

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
def tryBuildRepairStructures(unit, blueprints):
    # First try to build directly adjacent factories
    structureToWorkOn = None
    highestHealth = -1
    for s in blueprints:
        # Build the factory if it isn't already finished
        if s.health > highestHealth and unit.location.is_adjacent_to(s.location):
            structureToWorkOn = s
            highestHealth = s.health
    if structureToWorkOn:
        if structureToWorkOn.structure_is_built():
            # already built, should repair
            if gc.can_repair(unit.id, structureToWorkOn.id):
                gc.repair(unit.id, structureToWorkOn.id)
        else:
            # unbuilt, build
            if gc.can_build(unit.id, structureToWorkOn.id):
                gc.build(unit.id, structureToWorkOn.id)
        # return true only if factory build is still in progress
        return not structureToWorkOn.structure_is_built()
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
            return True
    return False

# return flattened location of walking down the grid from flatLoc, numGo times
def traverseMap(loc,grid,numGo):
    currLoc = loc
    for n in numGo:
        if numGo > 0:
            currLoc = traverseMapUp(currLoc,grid)
    return currLoc

def traverseMapUp(loc,grid):
    unit_maploc = unit.location.map_location()
    loc = dmap.flattenMapLoc(unit_maploc)
    largestLocs = [loc]
    largest = grid[loc]
    adjacents = dmap.adjacentInBounds(loc)
    for adj in adjacents:
        if grid[adj] <= largest and (adj in factoryLocs or gc.is_occupiable(MapLocationFlat(THIS_PLANETMAP.planet,adj))):
            if grid[adj] == largest:
                # if it is equally small just append this loc
                largestLocs.append(adj)
            else:
                # it set a new bar for largest, set the largest value and reset largestLocs
                largest = grid[adj]
                largestLocs = [adj]
    # of all the good choices, pick a random one
    randloc = random.choice(largestLocs)
    return randloc

def traverseMapDown(loc,grid):
    smallestLocs = [loc]
    smallest = grid[loc]
    adjacents = dmap.adjacentInBounds(loc)
    for adj in adjacents:
        if grid[adj] <= smallest and (adj in factoryLocs or gc.is_occupiable(MapLocationFlat(THIS_PLANETMAP.planet,adj))):
            if grid[adj] == smallest:
                # if it is equally small just append this loc
                smallestLocs.append(adj)
            else:
                # it set a new bar for smallest, set the smallest value and reset smallestLocs
                smallest = grid[adj]
                smallestLocs = [adj]
    # of all the good choices, pick a random one
    randloc = random.choice(smallestLocs)
    return randloc

# Finds a direction bringing you down the map
def downMapDir(unit,grid):
    unit_maploc = unit.location.map_location()
    loc = traverseMapDown(dmap.flattenMapLoc(unit_maploc),grid)
    return unit_maploc.direction_to(MapLocationFlat(unit_maploc.planet,loc))

# Finds a direction bringing you up the map
def upMapDir(unit,grid):
    unit_maploc = unit.location.map_location()
    loc = traverseMapUp(dmap.flattenMapLoc(unit_maploc),grid)
    return unit_maploc.direction_to(MapLocationFlat(unit_maploc.planet,loc))

# Move unit down a dijkstraMap
def walkDownMap(unit, grid):
    tryMove(unit, downMapDir(unit,grid))

# Move unit up a dijkstraMap
def walkUpMap(unit, grid):
    tryMove(unit, upMapDir(unit,grid))

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
            flatxy = dmap.flattenXY(adjLoc.x, adjLoc.y)
            if not flatxy in THIS_PLANET_WALLS and gc.is_occupiable(adjLoc):
                goals.append([flatxy, 0])
    return dmap.dijkstraMap(goals, WALL_GRAPH)

# Produces an approximate dijkstra map of the enemy attack ranges.
def enemyAttackMap(planetMap):
    eList  = []
    for e in senseAllEnemies(planetMap.planet):
        loc = e.location.map_location()
        if e.unit_type == bc.UnitType.Ranger or e.unit_type == bc.UnitType.Knight or e.unit_type == bc.UnitType.Mage:
            eList.append([dmap.flattenXY(loc.x,loc.y),-int(math.sqrt(e.attack_range()/2))])
    return dmap.dijkstraMap(eList,NO_WALL_GRAPH)

# Produces a map for fleeing, using the map of enemy attack ranges
def fleeMap(enemyAttackMap):
    goalLocs = []
    for idx, cell in enumerate(enemyAttackMap):
            if cell < 0 and not (idx in THIS_PLANET_WALLS):
                goalLocs.append([idx, cell])
    return dmap.dijkstraMap(goalLocs,WALL_GRAPH)

# Build map towards enemy TODO UNUSED
def mapToEnemy(planetMap):
    s = time.time()
    enemies = senseAllEnemies(planetMap.planet)
    enemyLocs = []
    for e in enemies:
        loc = e.location.map_location()
        enemyLocs.append([dmap.flattenMapLoc(loc), 0])
    if not enemies:
        for loc in ENEMY_LOCATION_MEMORY:
            enemyLocs.append([loc,0])
    m = dmap.dijkstraMap(enemyLocs, WALL_GRAPH)
    # print('\n'.join([''.join(['{:4}'.format(item) for item in row])for row in m]))
    # print("build enemy map took " + str(time.time()-s))
    return m


# Build map for rangers where goals are in range
def rangerMap(planetMap, atkRange):
    enemies = senseAllEnemies(planetMap.planet)
    enemyLocs = []
    if enemies:
        for e in enemies:
            loc = e.location.map_location()
            enemyLocs.append([dmap.flattenXY(loc.x, loc.y), 0])
    # If we can't see any enemies head towards where we last saw them. currently only remembers factory locations
    elif ENEMY_LOCATION_MEMORY:
        for loc in ENEMY_LOCATION_MEMORY:
            enemyLocs.append([loc,0])
    # find distances to enemy, ignoring walls, because rangers can shoot over
    distMap = dmap.dijkstraMap(enemyLocs, NO_WALL_GRAPH)

    goalLocs = []

    realAtkRange = int(math.sqrt(atkRange/2))
    # now find where the distance is right for rangers
    for idx, value in enumerate(distMap):
        if value == realAtkRange:
            goalLocs.append([idx, 0])

    # now pathfind to those sweet spot
    rangerMap = dmap.dijkstraMap(goalLocs, WALL_GRAPH)

    return rangerMap


TOTAL_KARBONITE = 0
KARBONITE_LOCS = []

# Iterate through all spots to find karbonite
# count total karbonite and record their locations and amounts
def initKarbonite():
    global TOTAL_KARBONITE
    for i in range(WIDTH*HEIGHT):
        k = THIS_PLANETMAP.initial_karbonite_at(MapLocationFlat(THIS_PLANETMAP.planet, i))
        if k >= 5:
            KARBONITE_LOCS.append((i,0))
        TOTAL_KARBONITE += k


initKarbonite()


# Build a Dijkstra Map for earth's karbonite using vision and initial
def updateKarbonite():
    global TOTAL_KARBONITE
    global KARBONITE_LOCS

    KARBONITE_LOCS[:] = [k for k in KARBONITE_LOCS if
                         not gc.can_sense_location(MapLocationFlat(THIS_PLANETMAP.planet,k[0]))
                         or gc.karbonite_at(MapLocationFlat(THIS_PLANETMAP.planet,k[0]))]
    #TOTAL_KARBONITE = 0
    #for k in KARBONITE_LOCS:
    #    TOTAL_KARBONITE += k[1]
    return dmap.dijkstraMap(KARBONITE_LOCS, WATER_GRAPH)

def updateEnemyMemory():
    global ENEMY_LOCATION_MEMORY
    deleteLocs = set()
    # delete if we see it is now empty
    for loc in ENEMY_LOCATION_MEMORY:
        maploc = MapLocationFlat(THIS_PLANETMAP.planet,loc)
        if gc.can_sense_location(maploc):
            if not gc.has_unit_at_location(maploc) or gc.sense_unit_at_location(maploc).team == MY_TEAM:
                deleteLocs.add(loc)
    ENEMY_LOCATION_MEMORY.difference_update(deleteLocs)
    for e in senseAllByType(THIS_PLANETMAP.planet, bc.UnitType.Factory):
        if e.team != MY_TEAM:
            loc = e.location.map_location()
            ENEMY_LOCATION_MEMORY.add(loc.y*WIDTH + loc.x)

def manageResearch():
    research = gc.research_info()
    if (gc.planet() == bc.Planet.Earth and not research.has_next_in_queue()):
        if(STRAT == Strategy.KNIGHT_RUSH):
                gc.queue_research(bc.UnitType.Knight)
        gc.queue_research(bc.UnitType.Healer)
        gc.queue_research(bc.UnitType.Healer)
        gc.queue_research(bc.UnitType.Healer)
        gc.queue_research(bc.UnitType.Rocket)
        gc.queue_research(bc.UnitType.Mage)
        gc.queue_research(bc.UnitType.Mage)
        gc.queue_research(bc.UnitType.Mage)
        gc.queue_research(bc.UnitType.Mage)

def priorityAttack(unit, priorityList):
    if gc.is_attack_ready(unit.id):
        enemies = senseEnemies(unit.location.map_location(), unit.attack_range())
        if enemies:
            target = enemies[0]
            targetPriority = priorityList.index(enemies[0].unit_type)
            for e in enemies:
                priorityLevel = priorityList.index(e.unit_type)
                if priorityLevel < targetPriority:
                    target = e
                    targetPriority = priorityLevel
                elif priorityLevel == targetPriority and e.health < target.health:
                    target = e
            if gc.can_attack(unit.id, target.id):
                gc.attack(unit.id, target.id)

def knightAttack(unit):
    priorityAttack(unit,KNIGHT_PRIORITY)

def rangerAttack(unit):
    priorityAttack(unit,RANGER_PRIORITY)

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
enemyMapBench = Benchmark("Creating enemy range and flee map")
rangerMapBench = Benchmark("Creating ranger map")
healerMapBench = Benchmark("Creating healer map")
factoryMapBench = Benchmark("Creating factory map")
karboniteMapBench = Benchmark("Creating karbonite map")
hurtBench = Benchmark("Tracking hurt allies")
rangerBench = Benchmark("Handling rangers")
healerBench = Benchmark("Handling healers")
factoryBench = Benchmark("Handling factories")
workerBench = Benchmark("Handling workers")
countUnitsBench = Benchmark("Counting/sorting units")
visionBench = Benchmark("Checking vision of enemy units")
rocketMapBench = Benchmark("Creating map of rockets")
rocketBench = Benchmark("Handling rockets")

# Wall preprocessing
WATER = getWalls(EARTHMAP)
ROCKY = getWalls(MARSMAP)
THIS_PLANET_WALLS = WATER if gc.planet() == bc.Planet.Earth else ROCKY
WATER_GRAPH = dmap.adjacencyGraph(WATER)
ROCKY_GRAPH = dmap.adjacencyGraph(ROCKY)
WALL_GRAPH = WATER_GRAPH if gc.planet() == bc.Planet.Earth else ROCKY_GRAPH
NO_WALL_GRAPH = dmap.adjacencyGraph([])

# Dijkstra maps
ENEMY_RANGE_MAP = []
ENEMY_MAP = mapToEnemy(THIS_PLANETMAP)
FLEE_MAP = []
RANGER_MAP = []
HEALER_MAP = []
BLUEPRINT_MAP = []
EARTH_KARBONITE_MAP = []
ROCKET_MAP = []
ID_GO_TO_ROCKET = set()


#global var eh
WORKERS_WANTED = 0
FACTORIES_WANTED = 0
factoryLocs = set()

class Strategy(Enum):
    KNIGHT_RUSH = 1
    RANGER_HEALER = 2
    MAGES = 3

# ranger healer by default
STRAT = Strategy.RANGER_HEALER

# DECIDE WHETHER OR NOT TO KNIGHT_RUSH
if(gc.planet() == bc.Planet.Earth):
    for unit in EARTHMAP.initial_units:
        if unit.team == MY_TEAM and ENEMY_MAP[dmap.flattenMapLoc(unit.location.map_location())] < 20:
            STRAT = Strategy.KNIGHT_RUSH
            break

# Research according to the strat
manageResearch()

while True:
    ROUND = gc.round()
    # We only support Python 3, which means brackets around print()
    if TIMING_DISABLED:
        print('pyround:', gc.round(), 'time left:', gc.get_time_left_ms(), 'ms')
    turnBench.start()

    # frequent try/catches are a good idea
    try:
        countUnitsBench.start()
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
        factoryLocs = set()
        for unit in gc.my_units():
            if unit.location.is_on_planet(THIS_PLANETMAP.planet):
                type = unit.unit_type
                if type == bc.UnitType.Factory:
                    if unit.max_health > unit.health:
                        factoryBlueprints.append(unit)
                    if unit.structure_is_built():
                        factoryLocs.add(dmap.flattenMapLoc(unit.location.map_location()))
                        factories.append(unit)
                elif type == bc.UnitType.Rocket:
                    if unit.max_health > unit.health:
                        rocketBlueprints.append(unit)
                    if unit.structure_is_built():
                        rockets.append(unit)
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
        numKnights = len(knights)
        numMages = len(mages)
        numHealers = len(healers)
        allBlueprints = factoryBlueprints + rocketBlueprints
        countUnitsBench.end()


        # update the ranger atkRange, because it can change with research.
        # SLIGHTLY BETTER TO UPDATE THIS JUST WHEN RESEARCH FINISHES INSTEAD OF POLLING EVERY TURN
        rangerAtkRange = 0  # This is dumb, but you need at least one ranger to find the atk range of the ranger
        if rangers:
            rangerAtkRange = rangers[0].attack_range()

        visionBench.start()
        # update our memory of enemy location
        updateEnemyMemory()
        visionBench.end()

        # update maps ONLY if we have computation time for it. It's okay to use outdated maps
        if gc.get_time_left_ms() > 400 or ROUND % 3 == 1:
            enemyMapBench.start()
            # Refresh enemy map
            ENEMY_RANGE_MAP = enemyAttackMap(THIS_PLANETMAP)
            FLEE_MAP = fleeMap(ENEMY_RANGE_MAP)
            enemyMapBench.end()

            ENEMY_MAP = mapToEnemy(THIS_PLANETMAP)

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
                for seq in [mages, rangers, knights, workers, healers]:
                    for ally in seq:
                        if ally.health < ally.max_health and ally.location.is_on_map():
                            loc = ally.location.map_location()
                            goals.append([dmap.flattenXY(loc.x,loc.y), int((ally.health - ally.max_health)/10)])
                HEALER_MAP = dmap.dijkstraMap(goals, WALL_GRAPH)
                healerMapBench.end()

            # refresh blueprint map
            BLUEPRINT_MAP = []
            if allBlueprints:
                factoryMapBench.start()
                blueprintLocs = [f.location.map_location() for f in allBlueprints]
                BLUEPRINT_MAP = adjacentToMap(blueprintLocs)
                dmap.logMap(BLUEPRINT_MAP)
                factoryMapBench.end()

            rocketMapBench.start()
            # refresh rocket map
            ROCKET_MAP = []
            if rockets:
                rocketlocs = [f.location.map_location() for f in rockets if len(f.structure_garrison())<f.structure_max_capacity()]
                ROCKET_MAP = adjacentToMap(rocketlocs)
            rocketMapBench.end()

        # refresh karbonite map
        if gc.get_time_left_ms() > 8000 or ROUND % 8 == 1:
            karboniteMapBench.start()
            EARTH_KARBONITE_MAP = updateKarbonite()
            karboniteMapBench.end()

        # ===================================================
        # Strategical decisions
        # refresh units_wanted TODO MAGIC NUMBERS

        # Knight Rush should not last past round 150
        if STRAT == Strategy.KNIGHT_RUSH and ROUND > 150:
            STRAT = Strategy.RANGER_HEALER

        maxworkers = 4 + int(TOTAL_KARBONITE/500)
        if ROUND == 1:
            WORKERS_WANTED = 4 + int(TOTAL_KARBONITE/2000)
        elif WORKERS_WANTED == numWorkers and gc.karbonite() > 80:
            # Increment only if we already hit the number we want, and we leave some karb buffer for the combat units
            if FACTORIES_WANTED == numFactories:
                # if we've got enough factories, we can feel free to just get more workers, up until maxworkers
                WORKERS_WANTED = min(WORKERS_WANTED + 1, maxworkers)

        print('workers wanted',WORKERS_WANTED," max workers",maxworkers," karbonite",TOTAL_KARBONITE)
        if ROUND == 1:
            FACTORIES_WANTED = 3+math.ceil(TOTAL_KARBONITE/2000)
        elif FACTORIES_WANTED == numFactories and gc.karbonite()>300:
            FACTORIES_WANTED += 1
        ROCKETS_WANTED = 0 if ROUND < 500 else int((numRangers+numHealers)/(8+(700-ROUND)/50))
        HEALERS_WANTED = int((numRangers+numKnights+numMages)/2)
        KNIGHTS_WANTED = 100 if STRAT == Strategy.KNIGHT_RUSH else 0
        RANGERS_WANTED = 150 if STRAT == Strategy.RANGER_HEALER else 0
        MAGES_WANTED = 150 if STRAT == Strategy.MAGES else 0

        # Have everyone ditch combat and flee to the rockets after round 700
        FLEE_TO_MARS = numRockets > 0 and ROUND > 700 and gc.planet() == bc.Planet.Earth
        # pause combat unit production if we need rockets and either can't afford rockets or have no workers
        # (and need to produce workers from factories)
        PAUSE_COMBAT_PRODUCTION = ROCKETS_WANTED > 0 and (numWorkers == 0 or gc.karbonite() < ROCKET_COST)
        # ===================================================

        # collect hurt rangers for healers to heal
        hurtBench.start()
        HURT_ALLIES = []
        if healers:
            for seq in [mages, rangers, knights, workers, healers]:
                for unitType, ally in enumerate(seq):
                    if ally.location.is_on_map():
                        if ally.health < ally.max_health:
                            HURT_ALLIES.append((unitType, ally.max_health - ally.health, ally.id))
            HURT_ALLIES.sort(key=lambda x: x)
            HURT_ALLIES = [x[2] for x in HURT_ALLIES]
        hurtBench.end()

        # rockets need to processed first so they can load units
        rocketBench.start()
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
                    nearby = senseAllies(unit.location.map_location(),25)
                    toldToCome = 0
                    for unit2 in nearby:
                        if unit2.unit_type in COMBAT_UNITTYPE:
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
        rocketBench.end()

        rangerBench.start()
        for unit in rangers:
            # Ranger logic
            if unit.location.is_on_map():
                rangerAttack(unit)
                if unit.id in ID_GO_TO_ROCKET or FLEE_TO_MARS:
                    walkDownMap(unit,ROCKET_MAP)
                elif unit.health < 170 and ENEMY_RANGE_MAP[dmap.flattenMapLoc(unit.location.map_location())] < 3:
                    walkUpMap(unit,FLEE_MAP)
                else:
                    walkDownMap(unit, RANGER_MAP)
                rangerAttack(unit)
        rangerBench.end()

        for unit in knights:
            if unit.location.is_on_map():
                loc = unit.location.map_location()
                knightAttack(unit)
                # Move towards enemies
                if unit.id in ID_GO_TO_ROCKET or FLEE_TO_MARS:
                    walkDownMap(unit,ROCKET_MAP)
                elif unit.health < 100 and ENEMY_RANGE_MAP[dmap.flattenMapLoc(unit.location.map_location())] < 3:
                    walkUpMap(unit,FLEE_MAP)
                else:
                    walkDownMap(unit, ENEMY_MAP)
                knightAttack(unit)

        for unit in mages:
            if unit.location.is_on_map():
                loc = unit.location.map_location()
                knightAttack(unit)
                # Move towards enemies
                if unit.id in ID_GO_TO_ROCKET or FLEE_TO_MARS:
                    walkDownMap(unit,ROCKET_MAP)
                elif unit.health < 100 and ENEMY_RANGE_MAP[dmap.flattenMapLoc(unit.location.map_location())] < 3:
                    walkUpMap(unit,FLEE_MAP)
                else:
                    walkDownMap(unit, ENEMY_MAP)
                knightAttack(unit)

        healerBench.start()
        for unit in healers:
            # Ranger logic
            if unit.location.is_on_map():
                if gc.is_heal_ready(unit.id):
                    for ally_id in HURT_ALLIES:
                        if gc.can_heal(unit.id, ally_id):
                            gc.heal(unit.id, ally_id)
                            break
                loc = dmap.flattenMapLoc(unit.location.map_location())
                if unit.id in ID_GO_TO_ROCKET or FLEE_TO_MARS:
                    walkDownMap(unit,ROCKET_MAP)
                elif HEALER_MAP[loc] == 100 or ENEMY_RANGE_MAP[loc] < 5:
                    walkUpMap(unit, FLEE_MAP)
                else:
                    walkDownMap(unit, HEALER_MAP)
        healerBench.end()

        workerBench.start()
        # Worker logic
        for unit in workers:
            if unit.location.is_on_map():
                mloc = unit.location.map_location()
                flatloc = dmap.flattenMapLoc(mloc)

                # MOVEMENT ====================================
                # Move towards blueprints to  build
                if BLUEPRINT_MAP and BLUEPRINT_MAP[flatloc] < 4:
                    walkDownMap(unit, BLUEPRINT_MAP)
                # Run away!
                elif ENEMY_RANGE_MAP[flatloc] < 3:
                    walkUpMap(unit,FLEE_MAP)
                # Walk towards karbonite
                elif EARTH_KARBONITE_MAP[flatloc]<40:
                    # print("walked down")
                    walkDownMap(unit, EARTH_KARBONITE_MAP)
                # stay safe if nothing to do
                else:
                    walkUpMap(unit,FLEE_MAP)

                # WORKER ACTIONS ==============================
                # look for and work on blueprints
                if tryBuildRepairStructures(unit, allBlueprints):
                    nothing =  1
                    # do nothing
                # Place blueprints if needed
                elif numFactories < FACTORIES_WANTED and tryBlueprint(unit, bc.UnitType.Factory):
                    numFactories += 1
                # Look for and mine Karbonite
                elif tryMineKarbonite(unit):
                    nothing =  1
                elif numRockets < ROCKETS_WANTED and tryBlueprint(unit, bc.UnitType.Rocket):
                    # print('blueprinted')
                    numRockets += 1

                # REPLICATION ==================================
                # 1. Replicate if needed
                replicateDir = randMoveDir(unit) # Replicate towards the enemy
                if numWorkers < WORKERS_WANTED and gc.karbonite() > REPLICATE_COST and gc.can_replicate(unit.id, replicateDir):
                    gc.replicate(unit.id, replicateDir)
                    numWorkers += 1
        workerBench.end()

        factoryBench.start()
        # Factory logic
        for unit in factories:
            garrison = unit.structure_garrison()
            for unit2 in garrison:
                d = randMoveDir(unit)
                if gc.can_unload(unit.id, d):
                    # print('unloaded a knight!')
                    gc.unload(unit.id, d)
            if numWorkers < WORKERS_WANTED:
                # Build worker if possible, if can't afford, do nothing (continue)
                if gc.can_produce_robot(unit.id, bc.UnitType.Worker):
                    gc.produce_robot(unit.id, bc.UnitType.Worker)
                    numWorkers += 1
                else:
                    continue
            # don't produce units if we need the karbonite for rocket building
            if PAUSE_COMBAT_PRODUCTION:
                continue
            elif numHealers < HEALERS_WANTED and gc.can_produce_robot(unit.id,bc.UnitType.Healer):
                gc.produce_robot(unit.id, bc.UnitType.Healer)
                numHealers += 1
            elif numKnights< KNIGHTS_WANTED and gc.can_produce_robot(unit.id, bc.UnitType.Knight):
                gc.produce_robot(unit.id, bc.UnitType.Knight)
                numKnights += 1
            elif numRangers< RANGERS_WANTED and gc.can_produce_robot(unit.id, bc.UnitType.Ranger):
                gc.produce_robot(unit.id, bc.UnitType.Ranger)
                numRangers += 1
            elif numMages < MAGES_WANTED and gc.can_produce_robot(unit.id, bc.UnitType.Mage):
                gc.produce_robot(unit.id, bc.UnitType.Mage)
                numMages += 1
        factoryBench.end()

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