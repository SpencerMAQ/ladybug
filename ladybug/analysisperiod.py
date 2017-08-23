"""Ladybug analysis period class."""
from .dt import DateTime
from datetime import datetime, timedelta
# SQ: Essentially checked, OK

# Notes
# Code doesn't check if _endMonth >= _startMonth, not sure why, maybe that's okay with E+, I dunno
# Uses strftime instead of format method

class AnalysisPeriod(object):
    """Ladybug Analysis Period.

    A continuous analysis period between two days of the year between certain hours

    Attributes:
        stMonth:    An integer between 1-12 for starting month (default = 1)
        stDay:      An integer between 1-31 for starting day (default = 1).
                    Note that some months are shorter than 31 days.
        stHour:     An integer between 0-23 for starting hour (default = 0)
        endMonth:   An integer between 1-12 for ending month (default = 12)
        endDay:     An integer between 1-31 for ending day (default = 31)
                    Note that some months are shorter than 31 days.
        endHour:    An integer between 0-23 for ending hour (default = 23)
        timestep:   An integer number from 1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30, 60
    """

    # class attributes
    _validTimesteps = {1: 60, 2: 30, 3: 20, 4: 15, 5: 12,
                       6: 10, 10: 6, 12: 5, 15: 4, 20: 3, 30: 2, 60: 1}
    _numOfDaysEachMonth = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)

    # SQ Done
    # TODO: handle timestep between 1-60
    def __init__(self, stMonth=1, stDay=1, stHour=0, endMonth=12,
                 endDay=31, endHour=23, timestep=1):
        """Init an analysis period."""

        stMonth     = stMonth or 1
        stDay       = stDay or 1
        stHour      = stHour or 0
        endMonth    = endMonth or 12
        endDay      = endDay or 31
        endHour     = endHour or 23
        timestep    = timestep or 1

        # calculate start time and end time ## START TIME
        # DateTime returns 2015 Jan 01 00h 00m by default
        self.stTime = DateTime(int(stMonth), int(stDay), int(stHour))

        # Simply ensures that if the input endDay is greater than the num of
        # days in that month, it will change that instead to the max num for that month

        # tuples are zero-index so you'll have to do int(endMonth) - 1
        if int(endDay) > self._numOfDaysEachMonth[int(endMonth) - 1]:
            # _numOfDaysEachMonth is a tuple containing the num of days per month
            end = self._numOfDaysEachMonth[endMonth - 1]
            print "Updated endDay from {} to {}".format(endDay, end)
            endDay = end

        # ## END TIME
        self.endTime = DateTime(int(endMonth), int(endDay), int(endHour))


        # stTime and endTime are both datetime objects in which you can use
        # normal datetime attributes
        # TODO: I'm not sure but I think this simply states whether there is at least
        # one overnight day inside the DateTime object
        if self.stTime.hour <= self.endTime.hour:
            self.overnight = False  # each segments of hours will be in a single day
        else:
            self.overnight = True

        # A reversed analysis period defines a period that starting month is after
        # ending month (e.g DEC to JUN)
        # TODO: what are reversed analysis period for?
        if self.stTime.hoy > self.endTime.hoy:
            self.reversed = True
        else:
            self.reversed = False

        # check time step
        if timestep not in self._validTimesteps:
            raise ValueError("Invalid timestep."
                             "Valid values are %s" % str(self._validTimesteps))

        # calculate time stamp
        self.timestep = timestep
        self.minuteIntervals = timedelta(1 / (24.0 * self.timestep))
        # sample computation:
        # 24 * 60
        # datetime.timedelta(1/1440) -> datetime.timedelta(0, 60)
        # stored as days, second, microsecond, there 60seconds for 60 timesteps in an hour

        # calculate timestamps and hoursOfYear
        # A dictionary for datetimes. Key values will be minute of year
        self._timestampsData = []
        self._calculateTimestamps()

        # ### IMPORTANT
        # When passed inside the ladybug component, repr() is automatically
        # called for display but the object is still an AnalysisPeriod object

    # SQ Done
    @classmethod
    def fromAnalysisPeriod(cls, analysisPeriod=None):
        """Create and AnalysisPeriod from an analysis period.

        This method is useful to be called from inside Grasshopper or Dynamo
        """
        # SQ This is also a named constructor creating the an AnalysisPeriod object from default args
        if not analysisPeriod:
            return cls()

        # see @property isAnalysisPeriod
        elif hasattr(analysisPeriod, 'isAnalysisPeriod'):
            return analysisPeriod
        elif isinstance(analysisPeriod, str):
            try:
                return cls.fromAnalysisPeriodString(analysisPeriod)
            except Exception as e:
                raise ValueError(
                    "{} is not convertable to an AnalysisPeriod: {}".format(
                        analysisPeriod, e)
                )


    @classmethod
    def fromAnalysisPeriodString(cls, analysisPeriodString):
        """Create an Analysis Period object from an analysis period string.
        Basically creates it from the 'analysisPeriod' output of the
        LB_AnalysisPeriod Component

        sample: 1/1 to 3/31 between 0 to 23 @1
        """
        # %s/%s to %s/%s between %s to %s @%s
        ap = analysisPeriodString.lower().replace(' ', '') \
            .replace('to', ' ') \
            .replace('/', ' ') \
            .replace('between', ' ') \
            .replace('@', ' ')
        try:
            stMonth, stDay, endMonth, endDay, stHour, endHour, timestep = ap.split(' ')
            return cls(stMonth, stDay, stHour, endMonth, endDay, endHour, int(timestep))
        except Exception as e:
            raise ValueError(str(e))

    # SQ used for the named constructor 'fromAnalysisPeriod', i.e. if hasattr, simply return it
    @property
    def isAnalysisPeriod(self):
        """Return True."""
        return True

    # SQ implementation detail
    def isPossibleHour(self, hour):
        """Check if a float hour is a possible hour for this analysis period."""
        if hour > 23 and self.isPossibleHour(0):
            hour = int(hour)
        if not self.overnight:
            return self.stTime.hour <= hour <= self.endTime.hour
        else:
            return self.stTime.hour <= hour <= 23 or \
                   0 <= hour <= self.endTime.hour

    def _calcTimestamps(self, stTime, endTime):
        """Calculate timesteps between start time and end time.

        Use this method only when start time month is before end time month.
        """
        # calculate based on minutes
        # I have to convert the object to DateTime because of how Dynamo
        # works: https://github.com/DynamoDS/Dynamo/issues/6683
        # Do not modify this line to datetime
        curr = datetime(stTime.year, stTime.month, stTime.day, stTime.hour,
                        stTime.minute)
        endTime = datetime(endTime.year, endTime.month, endTime.day,
                           endTime.hour, endTime.minute)

        while curr <= endTime:
            if self.isPossibleHour(curr.hour + (curr.minute / 60.0)):
                time = DateTime(curr.month, curr.day, curr.hour, curr.minute)
                self._timestampsData.append(time.moy)
            curr += self.minuteIntervals

        if self.timestep != 1 and curr.hour == 23 and self.isPossibleHour(0):
            # This is for cases that timestep is more than one
            # and last hour of the day is part of the calculation
            curr = endTime
            for i in range(self.timestep)[1:]:
                curr += self.minuteIntervals
                time = DateTime(curr.month, curr.day, curr.hour, curr.minute)
                self._timestampsData.append(time.moy)

    def _calculateTimestamps(self):
        """Return a list of Ladybug DateTime in this analysis period."""
        if not self.reversed:
            self._calcTimestamps(self.stTime, self.endTime)
        else:
            self._calcTimestamps(self.stTime, DateTime.fromHoy(8759))
            self._calcTimestamps(DateTime.fromHoy(0), self.endTime)

    # SQ 2nd output for the AnalysisPeriod Component
    # SQ NOTE: moy stands for MINUTE of year, not month of year
    @property
    def datetimes(self):
        """A sorted list of datetimes in this analysis period."""
        # sort dictionary based on key values (minute of the year)
        return tuple(DateTime.fromMoy(moy) for moy in self._timestampsData)

    @property
    def hoys(self):
        """A sorted list of hours of year in this analysis period."""
        return tuple(moy / 60.0 for moy in self._timestampsData)

    @property
    def intHoys(self):
        """A sorted list of hours of year as float values in this analysis period."""
        return tuple(int(moy / 60) for moy in self._timestampsData)

    # SQ Done
    # Simply checks if all days are included in the timestamps
    @property
    def isAnnual(self):
        """Check if an analysis period is annual."""
        return True if len(self._timestampsData) / self.timestep == 8760 \
            else False

    # SQ apparently used inside sunpath.py
    # TODO: SQ I have no idea what this is
    # SQ from what I understand, this simply checks if a certain moy is
    # SQ included inside the timestapsData
    # SQ NOTE: VERY IMPORANT
    # SQ as based on the comments below, start hours and end hours are applied daily, not
    # on the ends, it makes more sense that way
    def isTimeIncluded(self, time):
        """Check if time is included in analysis period.

        Return True if time is inside this analysis period,
        otherwise return False

        Args:
            time: A DateTime to be tested

        Returns:
            A boolean. True if time is included in analysis period
        """
        # time filtering in Ladybug and honeybee is slightly different since
        # start hour and end hour will be applied for every day.
        # For instance 2/20 9am to 2/22 5pm means hour between 9-17
        # during 20, 21 and 22 of Feb.
        return time.moy in self._timestampsData

    # SQ DONE
    def ToString(self):
        """Overwrite .NET representation."""
        return self.__repr__()

    # SQ DONE
    def __str__(self):
        """Return analysis period as a string."""
        return self.__repr__()

    # SQ DONE
    def __repr__(self):
        """Return analysis period as a string."""
        return "%s/%s to %s/%s between %s to %s @%d" % \
               (self.stTime.month, self.stTime.day,
                self.endTime.month, self.endTime.day,
                self.stTime.hour, self.endTime.hour,
                self.timestep)
