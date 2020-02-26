import unittest
import gettext
import time
from datetime import datetime
from src.common.time import (
  TimeManager, TimeManagerError, TimeUnit, get_time, get_duration
)

_ = gettext.gettext

class TestTimeManager(unittest.TestCase):
  def setUp(self):
    self.tman = TimeManager()

  def test_start(self):
    dts = datetime.now()
    self.tman.start()
    dte = datetime.now()
    self.assertTrue(
      self.tman.dt_start >= dts and self.tman.dt_start <= dte,
      _('incorrect start time')
    )
  
  def test_end(self):
    dts = datetime.now()
    self.tman.end()
    dte = datetime.now()
    self.assertTrue(
      self.tman.dt_end >= dts and self.tman.dt_end <= dte,
      _('incorrect end time')
    )
  
  def test_time(self):
    with self.assertRaises(TimeManagerError):
      self.tman.time(TimeUnit.second)
    self.tman.start()
    with self.assertRaises(TimeManagerError):
      self.tman.time(TimeUnit.second)
    time.sleep(1)
    self.tman.end()
    self.assertTrue(self.tman.time(TimeUnit.second) > 0)

class TestTimeFunctions(unittest.TestCase):
  def test_get_time(self):
    dts = datetime.now()
    val = get_time()
    dte = datetime.now()
    self.assertTrue(
      val >= dts and val <= dte,
      _('incorrect get_time return value')
    )
  
  def test_get_duration(self):
    dts = datetime.now()
    time.sleep(1)
    dte = datetime.now()
    val = get_duration(dts, dte, TimeUnit.second)
    # acepted error 20 miliseconds
    self.assertTrue(
      val >= 0.998 and val <= 1.002,
      _('incorrect get_duration return value')
    )
