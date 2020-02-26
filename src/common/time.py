'''
common.time
'''
import gettext
import logging
from enum import Enum
from datetime import datetime, timedelta

class TimeUnit(Enum):
  second=0
  minute=1
  hour=2
  day=3

def get_time():
  return datetime.now()

def get_duration(start, end, unit=TimeUnit.second):
  if not start or not end:
    return None
  duration = int(timedelta.total_seconds(end - start))
  if unit.value > TimeUnit.second.value:
    duration = duration / 60
  if unit.value > TimeUnit.minute.value:
    duration = duration / 60
  if unit.value > TimeUnit.hour.value:
    duration = duration / 24
  return duration

class TimeManagerError(Exception):
  pass

class TimeManager:

  def __init__(self, logger=None):
    # parameters
    self.logger = logger or logging.getLogger(__name__)
    # internal
    self._ = gettext.gettext
    self.dt_start = None
    self.dt_end = None

  def start(self):
    self.dt_start = get_time()
  
  def end(self):
    self.dt_end = get_time()
  
  def time(self, unit=TimeUnit.second):
    if not self.dt_start:
      raise TimeManagerError(self._('Time not started'))
    if not self.dt_end:
      raise TimeManagerError(self._('Time not ended'))
    return get_duration(self.dt_start, self.dt_end, unit)
