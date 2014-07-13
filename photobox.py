#!/usr/bin/env python

VERSION = '1.407.121' # Y.YMM.DDn
PROGRAM = 'photobox.py'
CONTACT = 'bright.tiger@gmail.com'

# -------------------------------------------------------------------------------
# Graphical photo management layer on top of a neo4j database.
# -------------------------------------------------------------------------------

import os, sys, math
import tempfile, subprocess, time, datetime, pprint, glob

def CrashAndBurn(library):
  print()
  print( "*** Unable to load python library '%s'!" % (library))
  print()
  os._exit(1)

try:
  from py2neo import neo4j, node, rel
except:
  CrashAndBurn('py2neo')

try:
  from tkinter import *
except:
  CrashAndBurn('tkinter')

try:
  from PIL import Image, ImageTk
except:
  CrashAndBurn('PIL.Image/ImageTk')

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
# Our schema is built out of the following node types:
#
#   pix . . . . filename, filesize, color/monochrome flag, image dimensions and tags:
#                 human-readable/searchable keywords
#                 human-readable freeform text
#                 machine-readable/searchable keywords
#
#   set . . . . name, ordered group of photos
# -------------------------------------------------------------------------------

db = None

SetIndex = None

def AddSetToSet(Name, Parent):
  global SetIndex, db
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

PixIndex = None

def AddPixListFromFilePathMask(Filter):
  global PixIndex
  Filenames = glob.glob(Filter)
  Pixs = []
  for Filename in Filenames:
    Pix, = db.create({'filename': Filename})
    Pixs += [Pix]
    Pix.add_labels('Pix')
    PixIndex.add('filename', Filename, Pix)
    print('>>> Added Pix %s: [%s]' % (Pix._id, Pix['filename']))
  return Pixs

def ShowPix(Pix):
  Image.open(Pix['filename']).show()

def ShowPixList(PixList):
  for Pix in PixList:
    ShowPix(Pix)

def ShowPixListThumbnails(PixList):
  for Pix in PixList:
    x = Image.open(Pix['filename'])
    x.thumbnail((128,128))
    x.show()

def AddPixListToSet(PixList, Set):
  global db
  for Pix in PixList:
    db.create(rel(Pix, 'IN', Set))

def GetPixByFilename(Filename):
  try:
    return PixIndex.get('filename', Filename)[0]
  except:
    return None

def GetRelListOfPix(Pix):
  return Pix.match_outgoing(rel_type='IN')

def GetSetByNames(Pix):
  global db
  return list(graph_db.match(start_node=Pix, rel_type='IN'))

def Neo4j_Test():
  global db, SetIndex, PixIndex
  if Neo4j_Init():
    db = neo4j.GraphDatabaseService('http://localhost:7474/db/data/')
    db.clear() # always start with an empty database until we are debugged

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

    PixList = AddPixListFromFilePathMask('images/*.jpg')
    if len(PixList) == 0:
      print('*** No jpg files found in working directory!')
      os._exit(1)

    AddPixListToSet(PixList, Circus)

    #ShowPixList(PixList)
    ShowPixListThumbnails(PixList)

    # Choose a picture (in Circus)

    Pix = GetPixByFilename('images/20130713_150852.jpg')
    if not Pix:
      print('*** No images/20130713_150852.jpg file found in working directory!')
      os._exit(1)

    #ShowPix(Pix)

    # Unlink it from all sets (Circus)

    for Rel in GetRelListOfPix(Pix):
      Rel.delete()

    # Link it to two new sets

    AddPixListToSet([Pix], GetSetByName('Tyson'))
    AddPixListToSet([Pix], GetSetByName('Nagy' ))

def makeThumbs(imgdir, size=(100, 100), thumbdir='thumbs'):
  if not os.path.exists(thumbdir):
    os.mkdir(thumbdir)
  thumbs = []
  size = 128, 128
  for imgfile in glob.glob('%s/*.jpg' % (imgdir)):
    #print('imgfile = [%s]' % (imgfile))
    file, ext = os.path.splitext(imgfile)
    base = file.split('/')[-1]
    basefile = '%s%s' % (base, ext)
    thumbpath = 'thumbs/%s.jpg' % (base)
    if os.path.exists(thumbpath):
      thumbobj = Image.open(thumbpath)
      thumbs.append((basefile, thumbobj))
    else:
      thumbobj = Image.open(imgfile)
      thumbobj.thumbnail(size, Image.ANTIALIAS)
      thumbobj.save(thumbpath, 'JPEG')
      thumbs.append((basefile, thumbobj))
  return thumbs

class ViewOne(Toplevel):
  def __init__(self, imgdir, imgfile):
    Toplevel.__init__(self)
    self.title(imgfile)
    imgpath = os.path.join(imgdir, imgfile)
    imgobj  = ImageTk.PhotoImage(file=imgpath)
    Label(self, image=imgobj).pack( )
    #print(imgpath, imgobj.width(), imgobj.height()) # size in pixels
    self.savephoto = imgobj # keep reference on me

def viewer(imgdir, kind=Toplevel, cols=None):
  win = kind( )
  win.title('Viewer')
  thumbs = makeThumbs(imgdir)
  if not cols:
    cols = int(math.ceil(math.sqrt(len(thumbs)))) # fixed or N x N
  savephotos = []
  while thumbs:
    thumbsrow, thumbs = thumbs[:cols], thumbs[cols:]
    row = Frame(win)
    row.pack(fill=BOTH)
    for (imgfile, imgobj) in thumbsrow:
      photo   = ImageTk.PhotoImage(imgobj)
      link    = Button(row, image=photo)
      handler = lambda savefile=imgfile: ViewOne(imgdir, savefile)
      link.config(command=handler)
      link.pack(side=LEFT, expand=YES)
      savephotos.append(photo)

  Button(win, text='Quit', command=win.quit).pack(fill=X)
  return win, savephotos

def Tk_Test():
  main, save = viewer('images', kind=Tk)
  main.mainloop()

#Neo4j_Test()
Tk_Test()

# -------------------------------------------------------------------------------
# End.
# -------------------------------------------------------------------------------
