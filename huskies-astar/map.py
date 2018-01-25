from run import gc
import run

# TODO list:
# - [X] Correctly store the Unit Matrix (maybe done?)
# - [ ] Correctly store the Terrain Matrix

class PossibleUnit:
    # PossibleUnitType [Float 0 < x < 1] -> PossibleUnit
    # Represents a unit that might exist. Includes the type
    # of the unit and a confidence rating: a float from 0 to
    # 1 (exclusive).
    def __init__(self, type, confidence):
        this.type = type
        this.confidence = confidence

class PossibleUnitType:
    enemy_worker = 1
    enemy_knight = 2
    enemy_ranger = 3
    enemy_mage = 4
    enemy_healer = 5
    enemy_factoryBlueprint = 6
    enemy_rocketBlueprint = 7

class TerrainType:
    none = 0 
    impassable = -1
    # Karbonite is stored as the amount of Karbonite

class Map:
    # Integer Integer Planet -> Map
    def __init__(self, width, height, planet):
        # Initialize fields

        # The Unit Matrix stores the ID of the unit at a certain location
        # (if it exists).
        self.unitMatrix = []

        # The Terrian Matrix stores the TerrainType of each location.
        self.terrainMatrix = []

        self.width = width
        self.height = height
        self.planet = planet

        # Initialize matrices
        initializeMatrices();

    @staticmethod
    # VisionSensor -> Map
    def constructMap(planet, sensor):
        # Construct the new map
        map = Map(run.WIDTH, run.HEIGHT, planet)

        for y in range(0, run.HEIGHT):
            for x in range(0, run.WIDTH):
                map.setUnitAt(x, y, sensor.senseUnitAt(x, y, planet))

    # None -> None
    # Initializes relevant matrices for this map
    def initializeMatrices(self):
        initializeMatrix(self.unitMatrix)
        initializeMatrix(self.terrainMatrix)

    # Matrix -> None
    # Initializes given matrix (of size self.width * self.height)
    def initializeMatrix(self, matrix):
        for row in range(0, self.height):
            self.matrix.append([])

            for col in range(0, self.width):
                matrix[row].append(0)

    # int int [Union ID PossibleUnit] -> None
    def setUnitAt(self, x, y, newUnit):
        unitMatrix[y][x] = newUnit

    # int int -> [Union ID PossibleUnit]
    def getUnitAt(self, x, y):
        return unitMatrix[y][x]
