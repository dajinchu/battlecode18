import abc

import battlecode as bc
from run import gc

class VisionSensor(abc.ABC):
    # int int -> [Union ID PossibleUnit]
    # Returns, according to our best knowledge, either
    # the unit ID at the given location, or information
    # about a unit that /might/ be there.
    @abc.abstractmethod
    def senseUnitAt(self, x, y, planet):
        pass

class NaiveVisionSensor(VisionSensor):
    def __init__(self):
        # The *lastSense variables are of the type
        # VecUnit.

        this.earth_lastSense = None
        this.earth_lastRoundSensed = -1
        this.earth_defaultSenseLocation = MapLocation(bc.Planet.Earth, 0, 0)

        this.mars_lastSense = None
        this.mars_lastRoundSensed = -1
        this.mars_defaultSenseLocation = MapLocation(bc.Planet.Mars, 0, 0)

    # int int Planet -> [Union ID PossibleUnit]
    # Implementing from the VisionSensor abstract base
    # class (ABC). This is a naive vision implementation
    # that only accounts for units of which their location
    # and existence is certain (relying directly on the
    # GameController's sense_unit_at_location method). This
    # implementation does not try to estimate where units
    # could be, and only returns 
    def senseUnitAt(self, x, y, planet):
        if planet == bc.Planet.Earth:
            earth_resenseIfNecessary()
            return searchVecUnitFor(x, y, earth_lastSense)
        else:
            mars_resenseIfNecessary()
            return searchVecUnitFor(x, y, mars_lastSense)

    # None -> None
    # Resenses earth if necessary.
    def earth_resenseIfNecessary(self):
        # Have we already sensed from the GameController
        # this round?
        if earth_lastRoundSensed < gc.round():
            earth_lastSense = gc.sense_nearby_units(earth_defaultSenseLocation, 1000)

    # None -> None
    # Resenses mars if necessary
    def mars_resenseIfNecessary(self):
        # Have we already sensed from the GameController
        # this round?
        if mars_lastRoundSensed < gc.round():
            mars_lastSense = gc.sense_nearby_units(mars_defaultSenseLocation, 1000)

    # int int VecUnit -> ID
    # Searches the given VecUnit for a unit at (x, y).
    def searchVecUnitFor(self, x, y, vecunit):
        for unit in vecunit:
            unitLocation = unit.location.map_location()

            if unitLocation.x = x and unitLocation.y = y:
                return unit.id

        return 0
