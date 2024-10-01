'''  cross_links.py 
 
 Python script to process XML data files to produce suggestions for cross-linking pages
 
 Ideally this script processes an XML file created by a backup of the entire wiki site

 Scans an exported XML file of the entire site
 1) Imports the list of pages produced by sitemap.py
 2) Scans XML file pages to identify links already in place to other pages
 3) Identifies likely matches with pages not already linked
 3) Produces a list of suggested cross linking candidates
 
 Version 5: 240914
 
 Fixed mistake in replacing linked text in the clean wikitext with dashes to prevent linking to links created
   dashes have to be inserted within the EditString object
 Fixed bug in EditString package in which the replacement of text at the end of the string did not generate an edit entry
 Fixed bug in generating match_name which meant that no links to named people were suggested
 Curly apostrophies in text and names no longer prevent matching - replaced by straight apostrophies 
 (last line 952)  
 
 Version 6.1: 240926
 Improved user interface includes hyperlinks to pages under review, ability to walk forwards and backwards to
 review links before declaring the page done, ability to undo links created, ability to exclude specific pages from
 consideration as potential links. Link sites are displayed as yellow (potential), green (created) or red (excluded).
 
 Version 6.2: 240928
 Restricts text selection such that selected text cannot extend past edit points.

 Version 6.3: 241001
 Can view edited text with highlighted links for checking purposes.
 Added explanatory comments
 Curly apostrophe fix does not affect editing text, only search text in locating potential links
  
'''
import os
import re 
from urllib.parse import unquote
import pywikibot

import colorama
from colorama import Fore, Back, Style, Cursor

log_file_name = "crosslink_log.txt"                                           # log file name
outfile = open(log_file_name,"w",encoding="utf-8")                            # log file reporting all operations completed

pages_input_file_name = "demo_batch.txt"                                      # list of pages to be processed
pages_done_file_name = "pages_crosslinked.txt"                                # list of pages completed
wkg_folder = "C:/Users/HP/OneDrive - Close Comfort Pty Ltd/Documents/Python/" # working directory (with slash)
site_URL = "https://ehwa.mywikis.wiki/wiki/"
pages_file_name = "ehwa_summaries.txt"                                        # list of pages on site with names, summaries


#=========================================================================================================
#
# Function to clear terminal window
#
#
def clear_window():  
  # Fore, Back and Style are convenience classes for the constant ANSI strings that set
  #     the foreground, background and style. They don't have any magic of their own.
  FORES = [ Fore.BLACK, Fore.RED, Fore.GREEN, Fore.YELLOW, Fore.BLUE, Fore.MAGENTA, Fore.CYAN, Fore.WHITE ]
  BACKS = [ Back.BLACK, Back.RED, Back.GREEN, Back.YELLOW, Back.BLUE, Back.MAGENTA, Back.CYAN, Back.WHITE ]
  STYLES = [ Style.DIM, Style.NORMAL, Style.BRIGHT ]
  
  pair = os.get_terminal_size()
  os.system('cls')
  
  MINX, MAXX = 1,pair[0]-2
  MINY, MAXY = 1,pair[1]-10
  
  colorama.just_fix_windows_console()
  pos = lambda x, y: Cursor.POS(x, y)
 
  string = pos(1,1) + Back.BLACK + " " 
  for x in range(MINX,1+MAXX):
    string += " " 
  string += Back.BLACK + " "
  print(string)
  print(Style.RESET_ALL,pos(1,MAXY+3)," ")
  return (MAXX, MAXY)
  
def print_normal_text_at(x, y, text):  
  # Fore, Back and Style are convenience classes for the constant ANSI strings that set
  #     the foreground, background and style. They don't have any magic of their own.
  FORES = [ Fore.BLACK, Fore.RED, Fore.GREEN, Fore.YELLOW, Fore.BLUE, Fore.MAGENTA, Fore.CYAN, Fore.WHITE ]
  BACKS = [ Back.BLACK, Back.RED, Back.GREEN, Back.YELLOW, Back.BLUE, Back.MAGENTA, Back.CYAN, Back.WHITE ]
  STYLES = [ Style.DIM, Style.NORMAL, Style.BRIGHT ]

  colorama.just_fix_windows_console()
  pos = lambda x, y: Cursor.POS(x, y)

  string = pos(x,y)+Fore.WHITE+Back.BLACK + text
  print(string,end='')
  return

def print_magenta_text_at(x, y, text):  
  # Fore, Back and Style are convenience classes for the constant ANSI strings that set
  #     the foreground, background and style. They don't have any magic of their own.
  FORES = [ Fore.BLACK, Fore.RED, Fore.GREEN, Fore.YELLOW, Fore.BLUE, Fore.MAGENTA, Fore.CYAN, Fore.WHITE ]
  BACKS = [ Back.BLACK, Back.RED, Back.GREEN, Back.YELLOW, Back.BLUE, Back.MAGENTA, Back.CYAN, Back.WHITE ]
  STYLES = [ Style.DIM, Style.NORMAL, Style.BRIGHT ]

  colorama.just_fix_windows_console()
  pos = lambda x, y: Cursor.POS(x, y)

  string = pos(x,y)+Fore.MAGENTA+Back.BLACK + text
  print(string,end='')
  return

def print_green_text_at(x, y, text):  
  # Fore, Back and Style are convenience classes for the constant ANSI strings that set
  #     the foreground, background and style. They don't have any magic of their own.
  FORES = [ Fore.BLACK, Fore.RED, Fore.GREEN, Fore.YELLOW, Fore.BLUE, Fore.MAGENTA, Fore.CYAN, Fore.WHITE ]
  BACKS = [ Back.BLACK, Back.RED, Back.GREEN, Back.YELLOW, Back.BLUE, Back.MAGENTA, Back.CYAN, Back.WHITE ]
  STYLES = [ Style.DIM, Style.NORMAL, Style.BRIGHT ]

  colorama.just_fix_windows_console()
  pos = lambda x, y: Cursor.POS(x, y)

  string = pos(x,y)+Fore.GREEN+Back.BLACK + text
  print(string,end='')
  return

def append_normal_text(text):
  # Fore, Back and Style are convenience classes for the constant ANSI strings that set
  #     the foreground, background and style. They don't have any magic of their own.
  FORES = [ Fore.BLACK, Fore.RED, Fore.GREEN, Fore.YELLOW, Fore.BLUE, Fore.MAGENTA, Fore.CYAN, Fore.WHITE ]
  BACKS = [ Back.BLACK, Back.RED, Back.GREEN, Back.YELLOW, Back.BLUE, Back.MAGENTA, Back.CYAN, Back.WHITE ]
  STYLES = [ Style.DIM, Style.NORMAL, Style.BRIGHT ]

  colorama.just_fix_windows_console()
  pos = lambda x, y: Cursor.POS(x, y)

  string = Fore.WHITE+Back.BLACK + text
  print(string,end='')
  return

def append_colour_text(text, accepted):
  # Fore, Back and Style are convenience classes for the constant ANSI strings that set
  #     the foreground, background and style. They don't have any magic of their own.
  FORES = [ Fore.BLACK, Fore.RED, Fore.GREEN, Fore.YELLOW, Fore.BLUE, Fore.MAGENTA, Fore.CYAN, Fore.WHITE ]
  BACKS = [ Back.BLACK, Back.RED, Back.GREEN, Back.YELLOW, Back.BLUE, Back.MAGENTA, Back.CYAN, Back.WHITE ]
  STYLES = [ Style.DIM, Style.NORMAL, Style.BRIGHT ]

  colorama.just_fix_windows_console()
  pos = lambda x, y: Cursor.POS(x, y)

  if accepted == 0:
    string = Fore.WHITE+Back.YELLOW + text
  elif accepted == 1:
    string = Fore.WHITE+Back.MAGENTA + text
  elif accepted == 2:
    string = Fore.WHITE+Back.GREEN + text
  elif accepted == 3:
    string = Fore.WHITE+Back.MAGENTA + text
  elif accepted > 3:
    string = Fore.WHITE+Back.RED + text
  elif accepted == -1:
    string = Fore.MAGENTA+Back.BLACK + text  
    
  print(string,end='')
  return

def finish_print(y):
  colorama.just_fix_windows_console()
  pos = lambda x, y: Cursor.POS(x, y)
  print(Style.RESET_ALL,pos(1,y)," ")
  return


  
#===========================================================================================================
# test_char_input.py
#
# input single character
# https://stackoverflow.com/questions/510357/how-to-read-a-single-character-from-the-user

# import os

def _read_one_wide_char_win():
    """Wait keyhit return chr. Get only 1st chr if multipart key like arrow"""
    return msvcrt.getwch()

def _char_can_be_escape_win(char):
    """Return true if char could start a multipart key code (e.g.: arrows)"""
    return True if char in ("\x00", "à") else False # \x00 is null character

def _dump_keyboard_buff_win():
    """If piece of multipart keycode in buffer, return it. Else return None"""
    try:                       # msvcrt.kbhit wont work with msvcrt.getwch
        msvcrt.ungetwch("a")   # check buffer status by ungetching wchr
    except OSError:            # ungetch fails > something in buffer so >
        return msvcrt.getwch() # return the buffer note: win multipart keys
    else:                      # are always 2 parts. if ungetwch does not fail
        _ = msvcrt.getwch()    # clean up and return empty string
        return ""

def _read_one_wide_char_nix():
    """Wait keyhit return chr. Get only 1st chr if multipart key like arrow"""
    old_settings = termios.tcgetattr(sys.stdin.fileno()) # save settings
    tty.setraw(sys.stdin.fileno()) # set raw mode to catch raw key w/o enter
    wchar = sys.stdin.read(1)
    termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, old_settings)
    return wchar

def _char_can_be_escape_nix(char):
    """Return true if char could start a multipart key code (e.g.: arrows)"""
    return True if char == "\x1b" else False # "\x1b" is literal esc-key

def _dump_keyboard_buff_nix():
    """If parts of multipart keycode in buffer, return them. Otherwise None"""
    old_settings = termios.tcgetattr(sys.stdin.fileno()) # save settings
    tty.setraw(sys.stdin.fileno()) # raw to read single key w/o enter
    os.set_blocking(sys.stdin.fileno(), False) # dont block for empty buffer
    buffer_dump = ""
    while char := sys.stdin.read(1):
        buffer_dump += char
    os.set_blocking(sys.stdin.fileno(), True) # restore normal settings
    termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, old_settings)
    if buffer_dump:
        return buffer_dump
    else:
        return ""

if os.name == "nt":
    import msvcrt
    read_one_wdchar = _read_one_wide_char_win
    char_can_escape = _char_can_be_escape_win
    dump_key_buffer = _dump_keyboard_buff_win
if os.name == "posix":
    import termios
    import tty
    import sys
    read_one_wdchar = _read_one_wide_char_nix
    char_can_escape = _char_can_be_escape_nix
    dump_key_buffer = _dump_keyboard_buff_nix


def getch_but_it_actually_works():
#    """Returns a printable character or a keycode corresponding to special key
#    like arrow or insert. Compatible with windows and linux, no external libs
#    except for builtins. Uses different builtins for windows and linux.
#
#    This function is more accurately called:
#    "get_wide_character_or_keycode_if_the_key_was_nonprintable()"
#
#    e.g.:
#        * returns "e" if e was pressed
#        * returns "E" if shift or capslock was on
#        * returns "x1b[19;6~'" for ctrl + shift + F8 on unix
#
#
#    You can use string.isprintable() if you need to sometimes print the output
#    and sometimes use it for menu control and such. Printing raw ansi escape
#    codes can cause your terminal to do things like move cursor three rows up.
#
#    Enter will return "\ r" on all platforms (without the space seen here)
#    as the enter key will produce carriage return, but windows and linux
#    interpret it differently in different contexts on higher level
#    """
    wchar = read_one_wdchar()    # get first char from key press or key combo
    if char_can_escape(wchar):   # if char is escapecode, more may be waiting
        dump = dump_key_buffer() # dump buffer to check if more were waiting.
        return wchar + dump      # return escape+buffer. buff could be just ""
    else:                        # if buffer was empty then we return a single
        return wchar             # key like "e" or "\x1b" for the ESC button
        
#===========================================================================================================
#
# EditString class allows 'snip' to remove text from the original string and the result is in the new string. 
#            allows 'replace' to replace text found in the new string, but the result is impleted on the original string.
# Application - remove unwanted wiki text codes from text, and then search the resulting clean string for keywords which
#               appear in the original text string. When needed, replace text in the original string by finding it in
#               the new string.          
# 
#  the internal data "edits" is a list of tuples defining the edits:
#  start of edit in o_strong
#  end of edit in o_string
#  position of edit in n_string
#  end of edit in n-string
#  0 = snip or 1 = replace
#
#  d_string is the same as n_string but with dashes where text is replaced (replace_n_dashes)
#
#  version 240914-241001 (editlist method added)
#
import re

class EditString:
  def __init__(self):
    self.__cut_pt = 0
    self.__ins_pt = 0
    self.__o_string = ""
    self.__n_string = ""
    self.__d_string = "" # dashed string
    self.__edits = []
    
  def __str__(self):
    return f"{str(self.__cut_pt)} {str(self.__cut_pt)} {str(self.__edits)}\n\"{self.__o_string}\"\n\"{self.__n_string}\"\n\"{self.__d_string}\""
    
  def set_o_string(self, text):
    self.__o_string = text
    self.__n_string = text
    self.__d_string = text
    return
    
  def reset(self,text):
    self.__cut_pt = 0
    self.__ins_pt = 0
    self.__o_string = text
    self.__n_string = text
    self.__d_string = text
    self.__edits = []
    return
  
  def n_string(self):
    return self.__n_string
    
  def o_string(self):
    return self.__o_string
    
  def d_string(self):
    return self.__d_string  
    
  def editlist(self):
    return self.__edits;  
    
  def snip(self, st_pt, en_pt):  # remove a section of the string: the string to be edited is in n_string. o_string remains unchanged.
                                 # st_pt, en_pt are positions on the n_string which is returned edited after the snip
    offset = 0
    snipped = False
    new_edits =[]
    length = en_pt - st_pt
    #print("Snip at:",str(st_pt))

    if self.__edits == []:
      new_edits = [(st_pt, en_pt, st_pt, en_pt, 0)]
      self.__n_string = self.__n_string[:st_pt] + self.__n_string[en_pt:]
      self.__d_string = self.__d_string[:st_pt] + self.__d_string[en_pt:]
      snipped = True
      #print("0-snip")

    else:
      for edit in self.__edits:
        if edit[2] >= st_pt:
          if not snipped:
            new_edits += [(st_pt + offset, en_pt + offset, st_pt, en_pt, 0)]  # creat edit record and delete text from n_string
            snipped = True
            self.__n_string = self.__n_string[:st_pt] + self.__n_string[en_pt:]
            self.__d_string = self.__d_string[:st_pt] + self.__d_string[en_pt:]
            #print("-snip-")
          new_edits += [(edit[0], edit[1], edit[2]-length, edit[3]-length, 0)] # subsequent edits all have to be mvoed back after n_string shortened
        else:  
          new_edits += [edit]  # build new list of edits
          offset += edit[1] - edit[0]  # increment offset by length of snipped section
          #print("skip")

    if not snipped:
      new_edits += [(st_pt + offset, en_pt + offset, st_pt, en_pt, 0)]
      snippped = True
      self.__n_string = self.__n_string[:st_pt] + self.__n_string[en_pt:]
      self.__d_string = self.__d_string[:st_pt] + self.__d_string[en_pt:]
      #print("snip-*")

    self.__edits = new_edits
    return self.__n_string    
      
      
  def checker(self):
    o_string = self.__o_string
    n_string = self.__n_string
    offset = 0
    for edit in self.__edits:
      print("edit",str(edit[0]), str(edit[1]), str(edit[2]), o_string[edit[0]:edit[1]])
      if offset != edit[0] - edit[2]:
        print("Offset mismatch:",str(offset), str(edit[0]-edit[2]))
      offset += edit[1] - edit[0]
      if o_string[edit[1]:edit[1]+5] != o_string[edit[1]:edit[1]+5]:
        print("mismatched text original:",o_string[edit[1]:edit[1]+5]," edited:", o_string[edit[1]:edit[1]+5])
    return  

  
  def offset(self, st_pt):  # find offset to text locations in original string for a position st_pt in new string
    offset = 0
    inserted = False
    for edit in self.__edits:
      if edit[0] >= st_pt + offset: # edit lies beyond st_p
        pass
      else:
        offset += edit[1] - edit[0]
    return offset

  def limits(self, st_pt):  # return limits for selecting text in n_string
    offset = 0
    last_p = 0
    for edit in self.__edits:
      if edit[2] >= st_pt: # edit lies beyond st_p
        return (last_p, edit[2])
      else:
        offset += edit[1] - edit[0]
        last_p = edit[3]
    return (edit[3],len(self.__n_string))

  def replace(self, st_pt, en_pt, text):  # replace text from st_pt to en_pt in original string
  #
  # where new text is inserted into the o_string, we create an edit which shows 
  # that the text was effectively deleted from the original string (even though
  # it was never really there in the first place
  #
    new_o_string = self.__o_string[:st_pt] + text + self.__o_string[en_pt:]
    new_edits = []
    offset = 0
    diff = len(text) - (en_pt - st_pt)
    inserted = False
    for edit in self.__edits:
      if edit[0] >= st_pt:
        if not inserted:
          inserted = True
          new_edits += [(st_pt, st_pt + diff, st_pt-offset, en_pt-offset, 1)] # creat new edit entry
        new_edits += [(edit[0] + diff, edit[1]+diff, edit[2], edit[3], edit[4])]
      else:
        offset += edit[1] - edit[0]
        new_edits += [edit]

    if not inserted:
      new_edits += [(st_pt, st_pt + diff, st_pt - offset, en_pt - offset, 1)] # create new entry at end of list
     
    self.__edits = new_edits   
    self.__o_string = new_o_string
    return new_o_string
  
  def replace_n_dashes(self, st_pt, en_pt):  # replace n_string text equivalent to st_pt:en_pt with dashes
    offset = 0
    diff = (en_pt - st_pt)
    i = 0
    dashes = ""
    while i < diff:
      dashes += "-"
      i += 1
    inserted = False
    for edit in self.__edits:
      if edit[0] >= st_pt:
        if not inserted:
          inserted = True
          self.__d_string = self.__d_string[:st_pt-offset] + dashes + self.__d_string[en_pt-offset:]
      else:
        offset += edit[1] - edit[0]
     
    return self.__d_string
       
#       
# The undo method is implemented for a snip and a replace. However, in practice, only a replace undo is possible
# because the snip has removed the text from the n_string.
# 
# As presently structured, the edits remain out of sight and cannot easily be accessed to decide which "undo" operations
# should be executed. However, we could display all the edits and decide which to undo.  Needs further thought while
# considering the user experience and controls for this.
#
#      
  def undo(self, st_pt, en_pt): # undo edit at this location in new string
    new_edits = []
    offset = 0
    undone = False
    diff = 0
    edit_type = -1
    for edit in self.__edits:
      
      if edit[2] == st_pt and edit[3] == en_pt:
        edit_type = edit[4]
        if edit_type == 1:
          undone = True
          self.__o_string = self.__o_string[:edit[0]] + self.__n_string[st_pt:en_pt] + self.__o_string[edit[1]+(edit[3]-edit[2]):]
          self.__d_string = self.__d_string[:edit[2]] + self.__n_string[st_pt:en_pt] + self.__d_string[edit[3]:]
          diff = (edit[1] - edit[0])
          print("Diff (replace)",str(diff))
        elif edit_type == 0:
          undone = True
          self.__n_string = self.__n_string[:edit[2]] + self.__o_string[edit[0]:edit[1]] + self.__n_string[edit[3]:]
          self.__d_string = self.__d_string[:edit[2]] + self.__o_string[edit[0]:edit[1]] + self.__d_string[edit[3]:]
          diff = (en_pt - st_pt)
          print("Diff (snip)",str(diff))
          
      else:
        if edit_type == -1:
          new_edits += [(edit[0], edit[1], edit[2], edit[3], edit[4])]
        elif edit_type == 0:
          new_edits += [(edit[0], edit[1], edit[2] + diff, edit[3] + diff, edit[4])]
        elif edit_type == 1:
          new_edits += [(edit[0] - diff, edit[1] - diff, edit[2], edit[3], edit[4])]
          
      offset += edit[1] - edit[0]
      
    self.__edits = new_edits
    return
   
    
#_____________________________________________________________________________________
#
# Function to clean up wiki text and present as much plain text as possible using editing class
#
#
def clean_wikitext(wikitext,editing):

  search_string = wikitext
  text_p = re.search(r'\<text(.+?)\>', search_string)  # search for start of text
  if text_p != None:
    en_pt = text_p.end()
#    print("snip <text",str(en_pt))  
    search_string = editing.snip(0,en_pt)  # cut off opening XML 
  
  m_pt = 0
  search_string = editing.n_string()
  finished = False
  pat_p = re.search(r'References', search_string[m_pt:]) # remove References and all following text
  if pat_p != None:
      en_pt = len(search_string)
      st_pt = pat_p.start() + m_pt
#      print("snipping References... ",str(s_pt),str(m_pt))  
      search_string = editing.snip(st_pt,en_pt) # in case of references, cut off all of the rest of the text

  m_pt = 0
  search_string = editing.n_string()
  finished = False
  while not finished:
    pat_p = re.search(r'<ref(.+?)<\/ref>', search_string[m_pt:]) # remove <ref> ... </ref> references
    if pat_p != None:
      en_pt = pat_p.end() + m_pt
      st_pt = pat_p.start() + m_pt
#      print("snipping <ref> ... </ref>",str(s_pt),str(m_pt))  
      search_string = editing.snip(st_pt,en_pt)
      m_pt = st_pt 
    else:
      finished = True
  
#  editing.checker() 
  m_pt = 0
  search_string = editing.n_string()
  finished = False
  while not finished:
    pat_p = re.search(r'\{\{(.+?)\}\}', search_string[m_pt:]) # remove {{ --- }} references
    if pat_p != None:
      en_pt = pat_p.end() + m_pt
      st_pt = pat_p.start() + m_pt
#      print("snipping {{ ... }}",str(s_pt),str(m_pt))  
      search_string = editing.snip(st_pt,en_pt)
      m_pt = st_pt 
    else:
      finished = True
        
#  editing.checker() 
  m_pt = 0
  search_string = editing.n_string()
  finished = False
  while not finished:
    pat_p = re.search(r'\[\[(.+?)\]\]', search_string[m_pt:],re.MULTILINE | re.DOTALL) # remove [[ --- ]] links
    if pat_p != None:
      en_pt = pat_p.end() + m_pt
      st_pt = pat_p.start() + m_pt
#      print("snipping [[ ... ]]",str(s_pt),str(m_pt))  
      search_string = editing.snip(st_pt,en_pt)
      m_pt = st_pt 
    else:
      finished = True

#  editing.checker() 
  m_pt = 0
  search_string = editing.n_string()
  finished = False
  while not finished:
    pat_p = re.search(r'<(.+?)>', search_string[m_pt:]) # remove < --- > wiki directives
    if pat_p != None:
      en_pt = pat_p.end() + m_pt
      st_pt = pat_p.start() + m_pt
#      print("snipping <  > ",str(s_pt),str(m_pt))  
      search_string = editing.snip(st_pt,en_pt)
      m_pt = st_pt 
    else:
      finished = True


#  outfile.write("\n\n================\n" + editing.n_string() + "\n================\n\n")  
  return editing

#____________________________________________________________________________________________________
#
# function to read list from a file
#
def read_list_file(file_name):
  with open(file_name,"r",encoding="utf-8") as file:
    list = file.read().splitlines()
  file.close()  
  return list 


#=====================================================================================
#
# Function to parse text with separator character - ignoring trailing and leading spaces
#
#
def separate_text(sep, text):

  items = []
  found = True
  m_pt = 0
  en_pt = 0
  n_items = 0
  while found:
    #print(text[m_pt:])
    sep_p = re.search(sep,text[m_pt:])
    if sep_p == None:
      found = False
      item = text[m_pt:]
    else:
      n_items += 1
      st_pt = sep_p.start()
      en_pt = sep_p.end()
      item = text[m_pt:st_pt + m_pt]
    
      
    #print(str(m_pt), str(st_pt), str(en_pt), item)
    if len(item) > 0:
      while item[0] == " ":
        item = item.lstrip(" ")
        if len(item) == 0:
          break
    if len(item) > 0:
      while item[len(item)-1] == " " and len(item) > 0:
        item = item.rstrip(" ")
        if len(item) == 0:
          break
    items += [item]    
    m_pt = en_pt + m_pt
    if n_items > 10:
      found = False

  return items


#===============================================================================================================
#
#  Function to identify overlapping link suggestions
#
#  Link list details - see functions below
#  Each link suggestion has an acceptance status (5th element of tuple):
#  0 - suggested link not yet accepted
#  1 - two or more overlapping link suggestions - user can only select one
#  2 - accepted link
#  3 - link overlaps with a link accepted by user - cannot be selected
#
#  Each group of numbers in the overlap table specifies what is to happen with the acceptance status
#  Group element 1: previous link status
#  Group element 2: current link status
#  Group element 3: new value for previous link status to
#  Group element 4: new value for current link status 
#
def mark_overlaps(linklist):
  overlap_table = [[0,0,1,1], [1,0,1,1], [0,1,1,1], [1,1,1,1], [2,0,2,3], [0,2,3,2], [2,2,2,2], [2,1,2,3], [1,2,3,2], [3,0,1,1], [0,3,1,1], [3,3,3,3], [2,3,2,3], [3,2,3,2], [1,3,1,1], [3,1,1,1]]
  

  st = 0   # used to remember parameters of previous link
  en = 0
  ac = 0
  i = 0
  for link in linklist:
    outfile.write("CL: " + str(link[0]) + "-" + str(link[1]) + " " + str(link[2]) + "-" + str(link[3]) + " " + str(link[4]) + " " + link[5] + " " + link[6][4] + "\n")
    newlink = link
    if link[2] <= en and i > 0:                # this link starts before end of previous link  => overlap
      outfile.write("overlap detected\n")

      if ac == 2 and link[4] == 2:             # two links accepted at same location: should never occur
        print("Overlapping link created!")  
        time.sleep(0.5)
        outfile.write("Overlapping link created to " + link[5] + " (" + str(st) + "--" + str(en) + " and " + str(link[2]) + "--" + str(link[3]) + "\n")
      for group in overlap_table:
        if ac == group[0] and link[4] == group[1]:
          linp = linklist[i-1] # label prev link 
          prevlink = (linp[0], linp[1], linp[2], linp[3], group[2], linp[5], linp[6])      
          linklist[i-1] = prevlink
          newlink = (link[0], link[1], link[2], link[3], group[3], link[5], link[6])  
                

    linklist[i] = newlink
    st = link[2]
    en = link[3]
    ac = link[4]
    i += 1
  return linklist            

#===============================================================================================================
#
# Function to advance to next link
#
def nextlink(link_p,direction,linklist):
  n = len(linklist)
  last_p = link_p
  done = False
  if direction > 0:
    while not done and link_p < n-1:
      link_p += 1
      if linklist[link_p][4] <= 3:
        done = True
        outfile.write("Move forwards to link " + str(link_p) + "\n")
        return link_p   
    if not done:
      outfile.write("No further valid links left after " + str(last_p) + "\n")
      print("End of suggested links")
      time.sleep(0.5)
      return last_p # no others to look at        
  else:
    while not done and link_p > 0:
      link_p -= 1
      if linklist[link_p][4] <= 3:
        done = True
        outfile.write("Move back to link " + str(link_p) + "\n")
        return link_p   
    if not done:
      outfile.write("No further valid links left before " + str(last_p) + "\n")
      return last_p # no others to look at        
    
    return last_p
  
#================================================================================================================
#
# function to display edited text for checking
#
#
def display_edited_text(editing):
  editlist = editing.editlist()  # retrieve edit location list and original text (with insertions)
  text = editing.o_string()
  ntext = editing.n_string()
  pair = clear_window()          #  clear window and get size of display area
  maxx = int(pair[0])
  maxy = int(pair[1])
  m_pt = 0                       # progress pointer
  for edit in editlist:
  
    if m_pt == 0:
      print_normal_text_at(1,1,text[m_pt:edit[0]])  # show normal text to next edit 
    else:
      append_normal_text(text[m_pt:edit[0]])
      
    if edit[4] == 0:                                # original text snipped
      append_colour_text(text[edit[0]:edit[1]], -1) # display original text snipped out in magenta
      m_pt = edit[1]
    else:
      append_colour_text(text[edit[0]:edit[0] + (edit[1] - edit[0]) + (edit[3] - edit[2])], 2) # display inserted text in green highlight
      m_pt = edit[0] + (edit[1] - edit[0]) + (edit[3] - edit[2])
      
  append_normal_text(text[m_pt:])                   # display last chunk of text
  done = False
  while not done:
    char = getch_but_it_actually_works()   #  check the operator's response (if any)
    if char == "e" or char == "E":
      done = True
    elif ord(char[0]) == 3:                #  ctrl-C pressed
      print("\n^C\n")
      done = True
    else:
      time.sleep(0.1)  
      
  return    


#================================================================================================================
#
# function to allow operator to evaluate link suggestions
#
# st_pt, en_pt are the start and end of the match in the new string (edited, cleaned wikitext)
# editing is the object containing the strings
# pagetitle is the page which appears to match and would be used as a link
# surrounding text enables the matched word to be seen in context
#

import time
def evaluate_links(editing, linklist, scan_page_link):
  sc_pg_link = re.sub(" ","_",scan_page_link)
  quit = False
  
#  nbefore = 40
#  nafter = 40
# 
#  linklist items consist of:
#  start, end of potential match in cleantext
#  start, end of selected match in cleantext
#  0 = suggestion, 1 = accepted, 2 = excluded
#  match_link - page that link must point to
#  page_items
#
#  page_items consists of 
#  [0]  -  page name of scanned page
#  [1]  -  lifespan
#  [2]  -  categories
#  [3]  -  summary
#  [4]  -  name of potential match
#  [5]  -  lifespan
#  [6]  -  categories
#  [7]  -  summary

  link_p = 0        # link pointer
  last_p = 1
  done = False
  rewrite = True    #   rewrite details of the page being scanned and suggested link
  redraw = True     #   redraw the text where the link is to be placed
  
  
  while not done and len(linklist) > 0:
    linklist = mark_overlaps(linklist)  # check for overlapping link locations and set accept status accordingly
    if last_p != link_p or rewrite:                                     
      pair = clear_window()             #  clear window and get size of display area
      maxx = int(pair[0])
      maxy = int(pair[1])
      y1 = 2
      y3 = maxy - 1
      y2 = int(((maxy - 1) + 2)/2)
      link = linklist[link_p]          # get current link details
      st_pt = link[0]                  # suggested link location
      en_pt = link[1]
      text_limits = editing.limits(st_pt) # find out limits of text that can be selected for link
      st_pt_act = link[2]              # location of link text selected by user
      en_pt_act = link[3]
      accepted = link[4]               # acceptance status
      pagelink = link[5]               # page that we should link to
      display_items = link[6]          # items to be displayed to user
      nbefore = int((maxx-(en_pt-st_pt))/2 - 10)  # extend of context to be displayed
      nafter = int(nbefore + 8)
      
      offset = editing.offset(st_pt)
      cleantext = editing.n_string()   # text that can be displayed to user
      len_text = len(cleantext)
      position = int((100*st_pt)/len(cleantext))  # relative position of link suggestion
      cleantext = re.sub(r'\n',r' ',cleantext)    # remove \n instances so text appears on single line
  
      outfile.write("List of potential links: " + str(len(linklist)) + " links in list\n")
      for link in linklist:
        outfile.write("Link: " + str(link[0]) + " " + str(link[4]) + " " + link[5] + " " + link[6][4] + "\n")
        
      # display info to user  

      print_normal_text_at(1,y1,"Scanning page: " + display_items[0] + " (" + display_items[1] + ") [" + site_URL + sc_pg_link + "]")
      print_normal_text_at(1,y1+1,display_items[2])
      print_normal_text_at(3,y1+3,display_items[3])
      pg_link = re.sub(" ","_",pagelink)
      print_green_text_at(1,y2,"Suggest link at " + str(position) + "%: " + pagelink + "  (" + display_items[5] + ") [" + site_URL + pg_link + "]")
      print_green_text_at(1,y2+1,display_items[6])
      print_normal_text_at(3,y2+3,display_items[7])
      finish_print(maxy + 1)
      rewrite = False
  
    #  display text on either side of suggested link location with the link text highlighted
    #
    if redraw:
      linklen = en_pt_act - st_pt_act
      half_link = int(linklen/2)
      from_pt = st_pt_act - nbefore + half_link
      to_pt = en_pt_act + nafter - half_link
      if from_pt < text_limits[0] and accepted <= 1:
        print_magenta_text_at(1,y3,cleantext[from_pt:text_limits[0]])    # before link accepted, display out of bounds text in magenta
        append_normal_text(cleantext[text_limits[0]:st_pt_act])          # text that can be selected is in white
      else:  
        print_normal_text_at(1,y3,cleantext[from_pt:st_pt_act])          
        
      append_colour_text(cleantext[st_pt_act:en_pt_act], accepted)       # display highlighted link text
      
      if to_pt > text_limits[1] and accepted <= 1: 
        append_normal_text(cleantext[en_pt_act:text_limits[1]])          # before link accepted 
        append_colour_text(cleantext[text_limits[1]:to_pt],-1)           # print text beyond limits in magenta
      else:
        append_normal_text(cleantext[en_pt_act:to_pt])                   # display white text
        
      finish_print(maxy + 1)                                             # return cursor to bottom of screen
      last_p = link_p
      redraw = False

    char = getch_but_it_actually_works()   #  check the operator's response (if any)
    if accepted <= 1: # link is not yet implemented
      if char == "àK":                       #  left arrow key pressed
        if st_pt_act > text_limits[0]:
          st_pt_act -= 1                     #    move left bar one character to the left
      elif char == "r":                      #  reset bar positions
        st_pt_act = st_pt                    #    restore st and en
        en_pt_act = en_pt   
      elif char == "àM":                     #  right arrow key pressed
        if en_pt_act < text_limits[1]:
          en_pt_act += 1                     #    move right bar one character to the right
      elif char == "àH":                     #  up arrow key pressed
        if en_pt_act < text_limits[1]:
          en_pt_act += 1                     #    move right bar one character to the right
        if st_pt_act > text_limits[0]:
          st_pt_act -= 1                     #    move left bar one character to the left
      elif char == "àP":                     #  down arrow key pressed
        en_pt_act -= 1                       #  
        st_pt_act += 1                       #  contract selection both ways
      newlink = (st_pt, en_pt, st_pt_act, en_pt_act, accepted, pagelink, display_items) 
      linklist[link_p] = newlink
      redraw = True
          
    if char == "q" or char == "Q":          #  want to quit and abandon page editing
      quit = True
      done = True
    elif ord(char[0]) == 3:                 #  ctrl-C pressed - quit
      print("\n^C\n")
      quit = True
      done = True
    elif char == "d" or char == "D":        # user accepts editing on this page
      done = True  
    elif char == "x":                       # exclude all suggested links like this one
      i = 0
      for lint in linklist:
        if pagelink == lint[5]:
          newlink = (lint[0], lint[1], lint[2], lint[3], lint[4]+4, lint[5], lint[6]) # exclude consideration of links to this page
          linklist[i] = newlink
        i += 1
      outfile.write("List of potential links: " + str(len(linklist)) + " links in list\n")
      for link in linklist:
          outfile.write("Link: " + str(link[0]) + "-" + str(link[1]) + " " + str(link[2]) + "-" + str(link[3]) + " " + str(link[4]) + " " + link[5] + " " + link[6][4] + "\n")
                 
      if char == "x":
        link_p = nextlink(link_p, 1,linklist)
      if char == "X":
        link_p = nextlink(link_p, -1,linklist)
      rewrite = True
      redraw = True
    elif char == "y" or char == "Y":        # user wants to accept link suggestion
      if accepted == 3:                     # this one cannot be accepted because it overlaps a link already accepted
        print("Cannot create overlapping link!")
        time.sleep(1.0)
        
      if accepted <= 1 and accepted != 3:   # link available for acceptance                         
        #print("\n(Accepted)\n")
        wikitext = editing.o_string()       # get the original text
        orig_text = wikitext[st_pt_act + offset:en_pt_act + offset] # at the location of the link
        #print("\n\nOriginal text:",orig_text)  
        
        editing.replace(st_pt_act + offset, en_pt_act + offset, "[[" + pagelink + "|" + orig_text + "]]") # insert link in o_string
           
        offset1 = editing.offset(st_pt_act)        # will change offset
        wikitext = editing.o_string()              # get that section of o_string to record in log file
        outfile.write("Offset:" + str(offset1) + " change:" + str(offset1-offset) + "\n")
        outfile.write("\nCreated wlink:\"" + wikitext[st_pt_act-100+offset:en_pt_act+180+offset] + "\"\n")
        newlink = (st_pt, en_pt, st_pt_act, en_pt_act, 2, pagelink, display_items) # update list of links
        linklist[link_p] = newlink
        outfile.write("List of potential links: " + str(len(linklist)) + " links in list\n")
        for link in linklist:
          outfile.write("Link: " + str(link[0]) + "-" + str(link[1]) + " " + str(link[2]) + "-" + str(link[3]) + " " + str(link[4]) + " " + link[5] + " " + link[6][4] + "\n")
        accepted = 2
        if char == "y":
          link_p = nextlink(link_p, 1,linklist)      # advance to next suggested link
        if char == "Y":
          link_p = nextlink(link_p, -1,linklist)     # go to previous suggested link location
        rewrite = True
        redraw = True
    elif char == "N" or char == "n":        # user wants to skip this link suggestion and go to next one (or previous one)
      if char == "n" :
        link_p = nextlink(link_p, 1,linklist)
      if char == "N":
        link_p = nextlink(link_p, -1,linklist)
      redraw = True
      rewrite = True  
    elif char == "v" or char == "V":        # user wants to see the o_string text to reveal edits
      display_edited_text(editing)
      rewrite = True    
      redraw = True
    elif char == "U" or char == "u":        # user wants to undo link insertion
      if accepted == 2:
        editing.undo(st_pt_act,en_pt_act)
        offset1 = editing.offset(st_pt_act)    # will change
        wikitext = editing.o_string()          #
        outfile.write("Offset:" + str(offset1) + " change:" + str(offset1-offset) + "\n")
        outfile.write("\nRemoved wlink:\"" + wikitext[st_pt_act-100+offset:en_pt_act+180+offset] + "\"\n")
        newlink = (st_pt, en_pt, st_pt_act, en_pt_act, 0, pagelink, display_items) 
        linklist[link_p] = newlink
        outfile.write("List of potential links: " + str(len(linklist)) + " links in list\n")
        for link in linklist:
          outfile.write("Link: " + str(link[0]) + "-" + str(link[1]) + " " + str(link[2]) + "-" + str(link[3]) + " " + str(link[4]) + " " + link[5] + " " + link[6][4] + "\n")
        accepted = 0
        if char == "u":
          link_p = nextlink(link_p, 1,linklist)       # advance to next suggested link
        if char == "U":
          link_p = nextlink(link_p, -1,linklist)      # go to previous suggested link location
        rewrite = True
        redraw = True
    
    time.sleep(0.1)                        # wait ... so we don't overload the computer
  
      
  return (linklist, quit)


#================================================================================================================
#
# function to search for suggested new internal links
#
# 1) get list of existing internal links
# 2) for all person:, profile: pages in pages list, isolate the family name (before the comma), and search the clean text for references
# 3) for first reference only, calculate relative position (percentage), and add to list of suggested links
# 4) find how many other links to that page
#
#  have to eliminate self-references
#
# 
#
def suggested_links_list(pagetext, page_items, pages_list):

   page_link = page_items[1]  
   outfile.write("Page name:" + page_link + "   " + "Name_page:" + page_items[0])
   
   if page_link == "Sitemap":  # ignore the sitemap page
     return 
   if page_link == "Broken Links":  # ignore these pages too
     return 
   if page_link == "Edit Cheat Sheet":  # ignore these pages too
     return 
   page_name = page_items[0]  
   page_cats = page_items[2]
   
   editing = EditString()

   editing.reset(pagetext)
   editing = clean_wikitext(pagetext, editing) # generate clean version of text
   cleantext = editing.n_string()
   cleantext = re.sub("’","'",cleantext)       # clean up curly apostrophies
   outfile.write("\n\n== Clean Wikitext ==\n" + editing.n_string() + "\n= = = = = = = \n\n")  
   
   links_created = []
   
   length = len(cleantext)
   abort = False
#   pagetitle.lstrip(" ")
#   print("scanning page:",page_name,"|")

   ppn = False
   orgn = False
   next_name = ""
   if page_name[:7] == "Person:":             # check that this is a person page, and if so, extract the family name, and the next (first) name
     ppn = True
   elif page_name[:8] == "Profile:":
     ppn = True                               # keep the next section of 'page_name' as 'page_name'
   elif page_name[:13] == "Organisation:":
     orgn = True  

   #
   #  Person pages, extract page_surname (before comma), next name (after comma)
   #
   if ppn or orgn:
     name_text = page_items[0]
     if name_text[:7] == "Person:":             # check that this is a person page, and if so, extract the family name, and the next (first) name
       name_text = name_text[7:]
     elif name_text[:8] == "Profile:":
       name_text = name_text[8:]                # keep the next section of 'page_name' as 'page_name'
     elif name_text[:13] == "Organisation":
       name_text = name_text[13:]
     
     comma_p = re.search(r'\,', name_text)      # search for a comma
     if comma_p != None:                  
       page_surname = name_text[:comma_p.start()]   # extract surname
       next_names = name_text[comma_p.end():]       # from the rest
       items = separate_text(" ",next_names)
       next_name = items[0]
     else:
       page_surname = name_text
         
     if ppn:
       page_summary = page_items[5]
       page_lifespan = page_items[4]
     else:  
       page_summary = page_items[4]   ### to be changed once organisations have lifespan text added
       page_lifespan = ""
   #
   #  For organisation / place pages, extract page_surname (before vertical bar, simplified name), next_name is blank
   #
   else:
     page_surname = page_name                     # extract surname (before bar)
     name_text = page_items[0]     
     page_lifespan = ""
     page_summary = page_items[4]
     
   print("\n\nScannng page name, first name:",page_surname,"|",next_name)

   # Scan page text for every person name in the reference page list

   linklist = []
   for page in pages_list:  #  extract text delimited by vertical bars
     items = separate_text(r'\|',page)
     if len(items) > 4:  # otherwise insufficent data for reliable matching, possibly malformed entry in pages_list
       pp = False
       org = False
       others = False
       match_lifespan = ""
       pagetitle = items[0]   #  page name (possibly simplified for orgs and places)  
       #
       #  separate text on colon
       #
       name_items = separate_text(r'\:', pagetitle)
       match_cats = items[2]
       if name_items[0] == "Person":  
         names = separate_text(r',',name_items[1])
         pp = True
         match_name = names[0]
         match_lifespan = items[4]
         match_summary = items[5]
         match_link = items[1]
       elif name_items[0] == "Profile":
         names = separate_text(r',',name_items[1])
         match_name = names[0]
         pp = True
         match_lifespan = items[4]
         match_summary = items[5]
         match_link = items[1]
       elif name_items[0] == "Organisation":
         org = True
         match_name = name_items[1]
         match_lifespan = items[4]
         match_summary = items[5]
         match_link = items[1]
       elif name_items[0] == "Place":
         match_name = name_items[1]
         match_link = items[1]
         match_summary = items[4]
       else:
         match_name = pagetitle  
         match_summary = items[4]
         match_link = items[1]
  
                 
       #print("search for: " + name)
     
       match_name = re.sub("’","'",match_name)  # clean up curly apostrophies
       #outfile.write("Matching " + match_name + "\n")

       found = True
       stext = cleantext
       percent = 0.0
       nlinks = 0
       m_pt = 0
       accepted = False

   #  page_items consists of 
   #  [0]  -  page name of scanned page
   #  [1]  -  lifespan
   #  [2]  -  categories
   #  [3]  -  summary
   #  [4]  -  name of potential match
   #  [5]  -  lifespan
   #  [6]  -  categories
   #  [7]  -  summary

       display_items = (page_items[0], page_lifespan, page_cats, page_summary, match_name, match_lifespan, match_cats, match_summary)
       
       while found:                                                  # keep searching page text until there are no more instances of 'name'
         name_p = re.search(r'\b' + match_name + r'\b', stext[m_pt:])      # search for next instance
         if name_p != None and page_surname != match_name and next_name != match_name and page_link != match_link:  
         # must not match 'next_name' normally the first name of the person we are looking for, nor must a link refer to the same page
           st_pt = name_p.start()                                    # note start and end of instance
           en_pt = name_p.end()
           distance = st_pt                                          # check location... if next instance closer than 80 chars 
           linklist += [(st_pt + m_pt, en_pt + m_pt, st_pt + m_pt, en_pt + m_pt, 0, match_link, display_items)]
           m_pt = en_pt + m_pt                                      # search from here for next instance
           if len(stext[m_pt:]) < 30:                               # unless we are almost at the end of the page text
             found = False
         else:
           found = False                                            # there are no more instances anyway
         
   # Now linklist has all the potential link matches on the page - sort into order of position on the page
   linklist = sorted(linklist, key=lambda x: x[0])
   outfile.write("List of potential links: " + str(len(linklist)) + " links in list\n")
   for link in linklist:
     outfile.write("Link: " + str(link[0]) + " " + str(link[4]) + " " + link[5] + " " + link[6][4] + "\n")
   
   result = evaluate_links(editing, linklist, page_link)  # suggest links to operator
   linklist = result[0]                                  
   quit = result[1]
     
   if quit:
     abort = True
  
  
   if abort: 
     print("\nPage editing abandoned\n\n")  
   else:  
     print("\nPage completed\n\n")  
   
   #outfile.write("\n\n$$$= = = = = = =" + cleantext + "\n= = = = = = =\n\n")  
   
   for link in linklist:
     if link[4]:
       nlinks += 1
       
   return (abort,nlinks,editing.o_string())                  # return any signal that we want to exit, links list and new page text



#==========================================================================================
#
#
# Main processing code
#
#



# Read page file list
ref_pages_list = read_list_file(wkg_folder + pages_file_name)

# Process the list of pages to be done
pages_input_list = read_list_file(wkg_folder + pages_input_file_name)
pages_done_list = read_list_file(wkg_folder + pages_done_file_name)


pages_done_file = open(wkg_folder + pages_done_file_name,"a",encoding="utf-8")  

for pagetitle in pages_input_list:
  if pagetitle not in pages_done_list:

    items = separate_text(r'\|',pagetitle)          
    if len(items) < 4: # mal-formed entry in pages list
      outfile.write("Incorrectly formatted entry in pages list\n" + pagetitle + "\n\n")
    else:  
      if items[1] != "":   # check that wiki page name is provided
        outfile.write("\n\nProcessing page " + items[1] + " describing " + items[0] + "\n")
        
        success = True
        try:  
          page_name = items[1]  
          site = pywikibot.Site('en')
          page = pywikibot.Page(site, page_name)
          page_text = page.get()
        
        except pywikibot.exceptions.IsRedirectPageError:
          print("Redirect error:" + page_name)
          outfile.write("Redirect error:" + page_name + "\n")
          success = False
          
        except:
          print("Something else went wrong")   
          outfile.write("Something else went wrong: " + page_name + "\n")
          success = False
      
        #outfile.write("\n\n\nPage text:============\n" + page_text + "\n============\n")
      
      # 
      #  Check for new link suggestions
      #
        if success:
          result = suggested_links_list(page_text, items, ref_pages_list)
          
          quit = result[0]
          n_links_created = result[1]
          new_page_text = result[2]
          
          if n_links_created > 0 and not quit:
            outfile.write("\nNew page text:============\n" + new_page_text + "\n============\n")
            print("Uploading ",page_name)
            summary_text = str(n_links_created) + " new internal links created" 
            try: 
              result = page.put(new_page_text,summary=summary_text,force=True, asynchronous=True)
            except:
              print("Something went wrong with the modified page text upload")
              outfile.write("Something went wrong with the modified page text upload\n")
              time.sleep(2.5)
            print(str(result))
            
          else:
            time.sleep(0.5)  # slow down a little if no links found, especially for short pages  
          
  
          if quit:
            break
          else:
            pages_done_file.write(pagetitle + "\n")
  
      else:
        print("Page list error - no page link provided: ",name_page)
        time.sleep(1.0)

pages_done_file.close()
outfile.close()

            
