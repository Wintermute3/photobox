#!/usr/bin/env python

VERSION = '1.407.121' # Y.YMM.DDn
PROGRAM = 'photobox.py'
CONTACT = 'bright.tiger@gmail.com'

# -------------------------------------------------------------------------------
# Graphical photo management layer on top of a neo4j database.
# -------------------------------------------------------------------------------

import os, sys, tempfile, subprocess, time, datetime, pprint, glob

def CrashAndBurn(library):
  print()
  print( "*** Unable to load python library '%s'!" % (library))
  print()
  os._exit(1)

try:
  from py2neo import neo4j, node, rel
except:
  CrashAndBurn('py2neo')

# -------------------------------------------------------------------------------
# Do a command and return the result as a string.  If an error occurs, prefix
# the return string with '*** Error: '.
# -------------------------------------------------------------------------------

def DoCmd(Command):
  TempFileName = tempfile.mktemp()
  rc = subprocess.call("%s" % Command, shell=True,
         stdout=open(TempFileName, 'w'),
           stderr=subprocess.STDOUT)
  TempFile = open(TempFileName)
  Text = TempFile.readlines()
  TempFile.close()
  os.unlink(TempFileName)
  if rc == 0:
    Output = []
    Output += [Line.rstrip() for Line in Text]
  else:
    Output = ['*** Error: %s' % (Text)]
  return Output

# -------------------------------------------------------------------------------
# Issue a neo4j/cypher query to the remote system.
# -------------------------------------------------------------------------------

def Neo4j(Hostname, Command):
  Command = Command.replace('"','\\"')
  Text = DoCmd("ssh %s 'echo \"%s\" | /opt/neo4j/bin/neo4j-shell'" % (Hostname, Command))
  Output = []
  for Line in Text.split('\n'):
    Line = Line.strip()
    if len(Line) > 0:
      Output += [Line]
  return Output

# -------------------------------------------------------------------------------
# Assure neo4j is running (start it if not already running).
# -------------------------------------------------------------------------------

def Neo4j_Init():
  Running = False
  print('Neo4j Server...check...', end='', flush=True)
  Text = DoCmd('neo4j info')
  for Line in Text:
    if 'Neo4j Server is running at pid ' in Line:
      Running = True
      break
    if 'Neo4j Server is not running' in Line:
      print('starting...', end='', flush=True)
      DoCmd('neo4j start')
      print('check...', end='', flush=True)
      Text = DoCmd('neo4j info')
      for Line in Text:
        if Line.startswith('Neo4j Server is running at pid '):
          Running = True
          time.sleep(2)
      break
  if Running:
    print('running')
  else:
    print('not running!')
    for Line in Text:
      print(Line)
  return Running

# -------------------------------------------------------------------------------
# Our schema is built out on the following node types:
#
#   pix . . . . filename, filesize, color/monochrome flag, image dimensions and tags:
#                 human-readable/searchable keywords
#                 human-readable freeform text
#                 machine-readable/searchable keywords
#   set . . . . name, ordered group of photos
#
# -------------------------------------------------------------------------------

SetIndex = None

def AddSetToSet(Name, Parent):
  global SetIndex
  Set, = db.create({'name': Name})
  Set.add_labels('Set')
  SetIndex.add('name', Name, Set)
  print('>>> Added Set %s: [%s]' % (Set._id, Set['name']))
  if Parent:
    db.create(rel(Set, 'IN', Parent))
  return Set

def NewSet(Name):
  return AddSetToSet(Name, None)

def GetSetByName(Name):
  Set, = SetIndex.get('name', Name)
  return Set

from PIL import Image

PixIndex = None

def NewPixList(Filter):
  global PixIndex
  Filenames = glob.glob(Filter)
  Pixs = []
  for Filename in Filenames:
    Pix, = db.create({'filename': Filename})
    Pixs += [Pix]
    Pix.add_labels('Pix')
    PixIndex.add('filename', Filename, Pix)
    print('>>> Added Pix %s: [%s]' % (Pix._id, Pix['filename']))
    #x = Image.open(Filename)
    #x.thumbnail((128,128))
    #x.show()
  return Pixs

def AddPixListToSet(PixList, Set):
  for Pix in PixList:
    db.create(rel(Pix, 'IN', Set))

def GetPixListByFilename(Filename):
  return PixIndex.get('filename', Filename)

def GetRelListOfPix(Pix):
  return Pix.match_outgoing(rel_type='IN')
  #return list(graph_db.match(start_node=Pix, rel_type='IN'))

def GetSetByNames(Pix):
  return list(graph_db.match(start_node=Pix, rel_type='IN'))


#  neo4j.Path(Pix, 'IN', )

#import matplotlib.pyplot as plt

#def ShowPhotos(Set):
#  x=plt.imread(Filename)
#  plt.imshow(x)
#  plt.show()

if Neo4j_Init():
  db = neo4j.GraphDatabaseService('http://localhost:7474/db/data/')
  db.clear() # always start with an empty database.

  SetIndex = db.get_or_create_index(neo4j.Node, 'Set')
  PixIndex = db.get_or_create_index(neo4j.Node, 'Pix')

  Families = NewSet('Families')

  AddSetToSet( 'Nagy'      , Families)
  AddSetToSet( 'Tyson'     , Families)
  AddSetToSet( 'Hedgepeth' , Families)
  AddSetToSet( 'Strickland', Families)
  AddSetToSet( 'Kosik'     , Families)
  AddSetToSet( 'Marmaro'   , Families)
  AddSetToSet( 'Caps'      , Families)
  AddSetToSet( 'Rankin'    , Families)

  Friends = NewSet('Friends')
  Circus = AddSetToSet('Circus', Friends)

  PixList = NewPixList('*.jpg')
  if len(PixList) == 0:
    print('*** No jpg files found in working directory!')
    os._exit(1)

  AddPixListToSet(PixList, Circus)

  # Choose a picture (in Circus)

  PixList = GetPixListByFilename('20130713_150852.jpg')
  if len(PixList) == 0:
    print('*** No 20130713_150852.jpg file found in working directory!')
    os._exit(1)

  # Unlink it from all sets (Circus)

  for Rel in GetRelListOfPix(PixList[0]):
    Rel.delete()

  # Link it to two new sets

  AddPixListToSet(PixList, GetSetByName('Tyson'))
  AddPixListToSet(PixList, GetSetByName('Nagy' ))

# -------------------------------------------------------------------------------
# End.
# -------------------------------------------------------------------------------
