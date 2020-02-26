import unittest
import gettext
import os
import json
import csv
from datetime import datetime
from src.common.file import (
  FileManager, FileManagerError
)

_ = gettext.gettext

class TestFileManager(unittest.TestCase):
  def setUp(self):
    self.fman = FileManager(
      '_common-tests-file-test-output-dir_'
    )

  def test_add_dir(self):
    dir_name = 'dir_name'
    dir_path = self.fman.add_dir(dir_name)
    self.assertTrue(
      os.path.isdir(dir_path),
      _('dir was not added')
    )

  def test_get_dir(self):
    dir_name = 'dir_name'
    dir_path = self.fman.get_dir(dir_name)
    self.assertEqual(
      dir_path,
      os.path.join(self.fman.output_dir, dir_name),
      _('incorrect get_dir return value')
    )
  
  def test_start_csv_file(self):
    file_name = 'file_name.csv'
    hrow = ['Header A', 'Header B', 'Header C']
    self.fman.start_csv_file(file_name, hrow)
    file_path = os.path.join(self.fman.output_dir, file_name)
    self.assertTrue(
      os.path.isfile(file_path),
      _('csv file was not created')
    )
    ahrow = []
    with open(file_path, 'r', newline = '') as csvfile:
      reader = csv.reader(csvfile)
      ahrow = next(reader)
    self.assertEqual(
      hrow,
      ahrow,
      _('incorrect csv header')
    )
  
  def test_append_csv_file(self):
    file_name = 'file_name.csv'
    hrow = ['Header A', 'Header B', 'Header C']
    self.fman.start_csv_file(file_name, hrow)
    file_path = os.path.join(self.fman.output_dir, file_name)
    row = ['1', '1', '1']
    self.fman.append_csv_file(file_name, row)
    with open(file_path, 'r', newline = '') as csvfile:
      reader = csv.reader(csvfile)
      next(reader)
      arow = next(reader)
    self.assertEqual(
      row,
      arow,
      _('incorrect csv row')
    )
  
  def test_write_csv_file(self):
    file_name = 'file_name.csv'
    hrow = ['Header A', 'Header B', 'Header C']
    rows = [['1', '1', '1'], ['2', '2', '2'], ['3', '3', '3']]
    self.fman.write_csv_file(None, file_name, hrow, rows)
    file_path = os.path.join(self.fman.output_dir, file_name)
    with open(file_path, 'r', newline = '') as csvfile:
      reader = csv.reader(csvfile)
      ahrow = next(reader)
      arows = [next(reader), next(reader), next(reader)]
    self.assertEqual(
      hrow,
      ahrow,
      _('incorrect csv header')
    )
    self.assertEqual(
      rows,
      arows,
      _('incorrect csv rows')
    )

  def test_write_txt_file(self):
    file_name = 'file_name.txt'
    data = {
      'prop 1': '1',
      'prop 2': '2',
      'prop 3': '3'
    }
    self.fman.write_txt_file(file_name, data)
    file_path = os.path.join(self.fman.output_dir, file_name)
    with open(file_path, 'r', encoding='utf-8') as txtfile:
      text = txtfile.read()
    self.assertEqual(
      'prop 1: 1\nprop 2: 2\nprop 3: 3\n',
      text,
      _('incorrect text')
    )

  def test_read_json_file(self):
    file_name = 'file_name.json'
    data = json.dumps({
      'prop 1': '1',
      'prop 2': '2',
      'prop 3': '3'
    })
    file_path = os.path.join(self.fman.output_dir, file_name)
    with open(file_path, 'w', encoding='utf-8') as jsonfile:
      jsonfile.write(data)
    adata = json.dumps(self.fman.read_json_file(file_path))
    self.assertEqual(
      data,
      adata,
      _('incorrect json')
    )
  