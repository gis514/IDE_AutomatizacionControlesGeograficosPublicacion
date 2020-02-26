'''
enums.py
'''

from enum import Enum

class Rule(Enum):
  invalid='invalid'
  duplicate='duplicate'
  multipart='multipart'
  intersect='intersect'
  null = 'null'
  all='all'
