'''
common.file
'''
import os
import errno
import csv
import gettext
import logging
import json

class FileManagerError(Exception):
  pass

class FileManager:

  def __init__(self, output_dir, logger=None):
    # parameters
    self.output_dir = output_dir
    self.logger = logger or logging.getLogger(__name__)
    # internal
    self._ = gettext.gettext
    # check dirs
    try:
        os.makedirs(self.output_dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
          raise FileExistsError(self._('Cannot create output dir'))

  def add_dir(self, dir_name):
    path = os.path.join(self.output_dir, dir_name)
    try:
      os.makedirs(path)
    except OSError as e:
      if e.errno != errno.EEXIST:
        raise FileExistsError(self._('Cannot add dir'))
    return path
  
  def get_dir(self, dir_name):
    return os.path.join(self.output_dir, dir_name)
  
  def _output_file_path(self, dir_name, file_name):
    if dir_name:
      return os.path.join(self.get_dir(dir_name), file_name)
    else:
      return os.path.join(self.output_dir, file_name)

  def start_csv_file(self, file_name, hrow):
    with open(self._output_file_path(None, file_name), 'w', newline = '') as csvfile:
      writer = csv.writer(csvfile)
      if hrow:
        writer.writerow(hrow)

  def append_csv_file(self, file_name, row):
    with open(self._output_file_path(None, file_name), 'a', newline = '') as csvfile:
      writer = csv.writer(csvfile)
      if row:
        writer.writerow(row)

  def write_csv_file(self, dir_name, file_name, hrow, rows):
    with open(
      self._output_file_path(dir_name, file_name),
      'w',
      newline = '',
      encoding='utf-8'
      ) as csvfile:
      writer = csv.writer(csvfile)
      if hrow:
        writer.writerow(hrow)
      if rows:
        for r in rows:
          writer.writerow(r)

  def write_txt_file (self, file_name, data):
    with open(self._output_file_path(None, file_name), 'w', encoding='utf-8') as txtfile:
      if data:
        for key, val in data.items():
          txtfile.write('{}: {}\n'.format(key, val))
  
  def read_json_file(self, file_name):
    if not file_name:
      return None
    data = None
    if os.path.isfile(file_name):
      with open(file_name) as json_data:
        data = json.load(json_data)
    return data
