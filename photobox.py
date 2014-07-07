#!/usr/bin/env python

VERSION = '1.407.061' # Y.YMM.DDn
PROGRAM = 'photobox.py'
CONTACT = 'bright.tiger@gmain.com'

# -------------------------------------------------------------------------------
# Graphical photo management layer on top of a neo4j database.
# -------------------------------------------------------------------------------

import os, sys, tempfile, subprocess, time, datetime, pprint
from optparse import OptionParser

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
# Command-line parameters with default values.
# -------------------------------------------------------------------------------

Hostname      = None
CsvFile       = 'doc/users-p3.csv'
NewLimit      = 0
CsvSkip       = 0
LoginUsername = 'admin'
LoginPassword = '11111'
LoginDomain   = 'voalte.com'
RestFlag      = False
PatchFlag     = False
ZapFlag       = False
QueryFlag     = False
TraceFlag     = False

# -------------------------------------------------------------------------------
# Show usage help and exit.
# -------------------------------------------------------------------------------

def ShowVersion():
  print
  print( '%s %s' % (PROGRAM, VERSION))
  print

def ShowHelp():
  ShowVersion()
  print('Given a csv file containing a set of users, add them to a p3 vds system (if newusers is')
  print('greater than 0), else query p3 vds system.')
  print
  print('  Usage:  %s hostname [-c csvfile] [-s csvskip] [-n newusers]' % (sys.argv[0]))
  print('                        [-u username] [-p password] [-d domain]')
  print('                          [-t] [-z] [-q] [-r] [-x] [-v]')
  print
  print('  parameter     default            description')
  print('  -----------   ----------------   ----------------------------------------')
  print('     hostname                      hostname or ipv4 of target p3 vds system')
  print('  -c csvfile    doc/users-p3.csv   csv file to read user definitions from')
  print('  -s csvskip    0                  number of users to skip from csv file')
  print('  -n newusers   0                  number of users to read from csv file')
  print('  -u username   admin              p3 vds voalte_admin credential')
  print('  -p password   11111              p3 vds voalte_admin credential')
  print('  -d domain     voalte.com         p3 vds voalte_admin credential')
  print('  -t            false              trace debug information to console')
  print('  -z            false              zap database back to clean install state')
  print('  -q            false              query and list table contents')
  print('  -r            false              use rest api for initial user query')
  print('  -x            false              execute temporary neo4j roles-patch')
  print('  -v                               report script version')
  print

# -------------------------------------------------------------------------------
# Parse command-line parameters for server address and quiet flag.
# -------------------------------------------------------------------------------

def GetCommandLineParameters():
  global Hostname, CsvFile, NewLimit, CsvSkip, LoginUsername, LoginPassword, LoginDomain
  global ZapFlag, RestFlag, TraceFlag, PatchFlag, QueryFlag
  try:
    Hostname = sys.argv[1]
    if Hostname.startswith('-'):
      if Hostname == '-v':
        ShowVersion()
      else:
        ShowHelp()
      os._exit(1)
  except:
    pass
  parser = OptionParser()
  parser.add_option('-c', dest='CsvFile'      , default=CsvFile      )
  parser.add_option('-n', dest='NewLimit'     , default=NewLimit     )
  parser.add_option('-s', dest='CsvSkip'      , default=CsvSkip      )
  parser.add_option('-u', dest='LoginUsername', default=LoginUsername)
  parser.add_option('-p', dest='LoginPassword', default=LoginPassword)
  parser.add_option('-d', dest='LoginDomain'  , default=LoginDomain  )
  parser.add_option('-t', dest='TraceFlag'    , default=TraceFlag    , action='store_true')
  parser.add_option('-z', dest='ZapFlag'      , default=ZapFlag      , action='store_true')
  parser.add_option('-q', dest='QueryFlag'    , default=QueryFlag    , action='store_true')
  parser.add_option('-r', dest='RestFlag'     , default=RestFlag     , action='store_true')
  parser.add_option('-x', dest='PatchFlag'    , default=PatchFlag    , action='store_true')
  parser.add_option('-v', dest='VersionFlag'  , default=False        , action='store_true')
  (options, args) = parser.parse_args(sys.argv[2:])
  if options.VersionFlag:
    ShowVersion()
    os._exit(1)
  if Hostname is None or Hostname == '':
    ShowHelp()
    os._exit(1)
  CsvFile       = options.CsvFile
  NewLimit      = int(options.NewLimit)
  CsvSkip       = int(options.CsvSkip)
  LoginUsername = options.LoginUsername
  LoginPassword = options.LoginPassword
  LoginDomain   = options.LoginDomain
  TraceFlag     = options.TraceFlag
  ZapFlag       = options.ZapFlag
  QueryFlag     = options.QueryFlag
  RestFlag      = options.RestFlag
  PatchFlag     = options.PatchFlag

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
    if Line.startswith('Neo4j Server is running at pid '):
      Running = True
      break
    if Line == 'Neo4j Server is not running':
      print('starting...', end='', flush=True)
      DoCmd('neo4j start')
      print('check...', end='', flush=True)
      Text = DoCmd('neo4j info')
      for Line in Text:
        if Line.startswith('Neo4j Server is running at pid '):
          Running = True
      break
  if Running:
    print('running')
  else:
    print('not running!')

Neo4j_Init()
db = neo4j.GraphDatabaseService("http://localhost:7474/db/data/")
db.clear()
michael, lauren, suzanne, john, gail, jeff_m, jeff_k, joy = db.create(
  {'name': 'michael', 'gender':   'male'},
  {'name': 'lauren' , 'gender': 'female'},
  {'name': 'suzanne', 'gender': 'female'},
  {'name': 'john'   , 'gender':   'male'},
  {'name': 'gail'   , 'gender': 'female'},
  {'name': 'jeff_m' , 'gender':   'male'},
  {'name': 'jeff_k' , 'gender':   'male'},
  {'name': 'joy'    , 'gender': 'female'}
)

michael.add_labels('Family')
lauren .add_labels('Family')
suzanne.add_labels('Family')
john   .add_labels('Family')

gail  .add_labels('Relative')
jeff_m.add_labels('Relative')
jeff_k.add_labels('Relative')
joy   .add_labels('Relative')

db.create(rel(michael, "SPOUSE", gail  ))
db.create(rel(lauren , "SPOUSE", jeff_m))
db.create(rel(suzanne, "SPOUSE", jeff_k))
db.create(rel(john   , "SPOUSE", joy   ))

db.create(rel(michael, "SIBLING", lauren ))
db.create(rel(michael, "SIBLING", suzanne))
db.create(rel(michael, "SIBLING", john   ))

db.create(rel(michael, "BROTHER", john   ))
db.create(rel(lauren , "BROTHER", suzanne))


# -------------------------------------------------------------------------------
# End.
# -------------------------------------------------------------------------------
