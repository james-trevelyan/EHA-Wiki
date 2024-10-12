'''  check_links.py 
 
 Python script to process XML data file backup to detect external links and then
 verify the link can be accessed and is not dead.
 
 Ideally this script processes an XML file created by a backup of the entire wiki site

 Scans an exported XML file of the entire site
 1) Imports the list of pages produced by sitemap.py
 2) Scans XML file pages to identify links already in place to other pages
 3) Identifies likely matches with pages not already linked
 3) Produces a list of suggested cross linking candidates
 
 Version 0-1: 240831
 Version 6.5 241010
 

'''
import os
import re 
import requests
from urllib.parse import unquote
import time

log_file_name = "checklink_log.txt"                                                        # log file name
outfile = open(log_file_name,"w",encoding="utf-8")                                         # log file reporting all operations completed

wkg_folder = wkg_folder = "C:/Users/HP/OneDrive - Close Comfort Pty Ltd/Documents/Python/" # working directory (with slash)
xml_data_file = "eha.xml"                                                                  # XML file to be analyzed
exceptions_file_name = "link_exceptions.txt"                                               # exceptions file
broken_links_file_name = "broken_links_wiki.txt"                                           # broken links list in wiki format
ref_pages_list_name = "eha_pages.txt"                                                       # reference file list
states = ['National','New South Wales','Queensland','Victoria','Tasmania','South Australia','Australian Capital Territory','Western Australia','Northern Territory']
broken_links_file = open(wkg_folder + broken_links_file_name, "w", encoding = "utf-8" )



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

  editing.reset(wikitext)
  earch_string = wikitext
  
#  m_pt = 0
#  search_string = editing.n_string()
#  finished = False
#  while not finished:
#    pat_p = re.search(r'<ref(.+?)<\/ref>', search_string[m_pt:]) # remove <ref> ... </ref> references
#    if pat_p != None:
#      en_pt = pat_p.end() + m_pt
#      st_pt = pat_p.start() + m_pt
#      print("snipping <ref> ... </ref>",str(s_pt),str(m_pt))  
#      search_string = editing.snip(st_pt,en_pt)
#      m_pt = st_pt 
#    else:
#      finished = True
  
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
#    pat_p = re.search(r'<(.+?)>', search_string[m_pt:]) # remove < --- > wiki directives
    pat_p = re.search(r'&lt;(.+?)&gt;', search_string[m_pt:]) # remove < --- > wiki directives
    
    if pat_p != None:
      en_pt = pat_p.end() + m_pt
      st_pt = pat_p.start() + m_pt
#      print("snipping <  > ",str(s_pt),str(m_pt))  
      search_string = editing.snip(st_pt,en_pt)
      m_pt = st_pt 
    else:
      finished = True

#   editing.checker() 

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

#==========================================================================================
#
# Function to extract birth year and death year from a person's biographical entry
#
#
def lifespan(text):
  instance = re.search(r'[\(](\d{4})', text)
  if instance:
    instance2 = re.search(r'[\s-]{1,5}([-\d]{4})[\)]', text[instance.end():])
    if instance2:
      output_text = instance.group(1) + "-" + instance2.group(1)
    else:
      output_text = instance.group(1) + "- ----"
  else:
    output_text = ""
  return  output_text

#==========================================================================================
#
# function to reformat timestamp from yyyy-mm-dd to mmm yyyy
#
#
def timestamp_mon_year(text):
    m = text[5:7]
    if m == "01":
      mm = "Jan "
    elif m == "02":
      mm = "Feb "
    elif m == "03":
      mm = "Mar "
    elif m == "04":
      mm = "Apr "
    elif m == "05":
      mm = "May "
    elif m == "06":
      mm = "Jun "
    elif m == "07":
      mm = "Jul "
    elif m == "08":
      mm = "Aug "
    elif m == "09":
      mm = "Sep "
    elif m == "10":
      mm = "Oct "
    elif m == "11":
      mm = "Nov "
    elif m == "12":
      mm = "Dec "
    else:
      mm = "*** "
    return (mm + text[:4])

#==========================================================================================
#
# Function to reformat page name as Person:<surname>, <forenames>
#
#
def reformat(page_name):
    profile = False
    name_loc = re.search("Person:",page_name) # check for "Person:" or "Profile:"
    if not name_loc:
      name_loc = re.search("Profile:",page_name)
      profile = name_loc
    if name_loc:                            # this is a "Person:" page name - don't do anything otherwise
        page_name = page_name[name_loc.end():]  # strip "Person:"
        # Find the text in brackets provided by perplaxity.ai
        bracket_text = re.findall(r'\((.*?)\)', page_name)
        # Remove the text in brackets from the original string
        page_name = re.sub(r'\((.*?)\)', '', page_name)
        
        page_name = re.sub("_"," ",page_name)   # substitute _ with whitespace
        page_name = page_name.rstrip("\n")  # remove \n character if present
        page_name = page_name.lstrip(" ")   # remove whitespace from front
        page_name = page_name.rstrip(" ")   # and from end too
        if not re.search(",", page_name):       # no comma found in name - need to reformat
            forenames = ""                      # initialize
            family_name = page_name             # in case of single name only
            while space_loc := re.search(r'\s', page_name):                 # search for next whitespace char
                forenames = forenames + ' ' + page_name[:space_loc.start()] # add this name to fornames
                page_name = page_name[space_loc.end():]                     # trim text
                family_name = page_name                                     # rest will be family name unless another space found
            if profile:
              page_name = "Profile:" + family_name + ',' + forenames       # reformat the page title
            else:
              page_name = "Person:" + family_name + ',' + forenames       # reformat the page title
            
            if bracket_text:
                page_name = page_name + ' (' + ', '.join(bracket_text) + ')'  # replace bracket string at end
           
        else:                                                           # comma found - name format already in correct format               
          if profile:
            page_name = "Profile:" + page_name
          else:
            page_name = "Person:" + page_name
            
    return(page_name)


#==========================================================================================
#
# Function to test link
#
#
def test_link(URL):
    
  response = requests.get(URL, stream=True)
  if response.status_code == 200:
    success = True
  else:
    outfile.write("Inaccessible URL (status code:" + str(response.status_code) + "): " + URL + "\n")
    print("Inaccessible URL (status code:" + str(response.status_code) + "): " + URL)
    success = False
  return success

#==========================================================================================
#
# Function to test link
#
#
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def fetch_data_with_retry(url, timeout=5, retries=3):
#    """
#    Fetches data from a URL with retry mechanism in case of ReadTimeout error.
#    """
    session = requests.Session()
    retry_strategy = Retry(
        total=retries,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
 
    error_code = ""
    try:
        response = session.get(url, timeout=timeout)
        response.raise_for_status()
        return error_code
    except requests.exceptions.ReadTimeout:
        #print("ReadTimeout error: Server did not respond within the specified timeout.")
        outfile.write("ReadTimeout error: Server did not respond within the specified timeout:" + URL + "\n")
        error_code = "timeout"
    except requests.exceptions.RequestException as e:
        #print(f"Link error: {e}")
        outfile.write(f"An error occurred: {e}" + "\n")
        error_code = str(e)[0:3]
        if error_code == "HTT":
          error_code = "Timeout"
    return error_code
 
 
def search_exceptions(pagetitle, URL, error_code, exceptions):
  items=[]
  for exception in exceptions:
    items = separate_text(r'\|',exception)
    if items[0] == pagetitle:
      if items[1] == URL:
        if items[2] == error_code:
          return True
#  print(items,pagetitle,URL,error_code)        
  return False

#==========================================================================================
#
#
# Main processing code
#
#
# Exceptions file contains a list of pages and links with known errors that are expected, e.g. 403 errors (requires login, forbodden access)
# Links are tested and if error is listed already in exceptions file, do not report it.
# 
# Broken links file contains the listing of errors not in the exceptions file.
# 
# Vertical bars delimit the exceptions file (page | link | error code)
# 
# 



new_exceptions = []

exceptions = read_list_file(wkg_folder + exceptions_file_name)
ref_pages_list = read_list_file(wkg_folder + ref_pages_list_name)

with open(xml_data_file, 'rb') as file:
    content = file.read()
    filetext = content.decode('utf-8')
file.close()


# Process the XML file, page by page

remaining_file_text = filetext
page_data = True
pages = []
numpage = 0
broken_links = []

while page_data:
  page_date = False
  nlinks = 0
  print("Page ",str(numpage),"\r",end='')
  numpage += 1
  page_match = re.search(r'<page>(.+?)</page>', remaining_file_text, re.DOTALL)     # find next page
  if page_match != None:                                       
    page_data = True                                                           # there is another page
    page_text = page_match.group(1)
    remainder = remaining_file_text[:page_match.start()]                       # string up to just before start of <page>
    remaining_file_text = remaining_file_text[page_match.end():]               # discard this text from remaining text

    title_match = re.search(r'<title>(.+?)</title>',page_text)                  # title defined?
    if title_match:
      pagetitle = title_match.group(1)                                         # retrieve page title
      newpagetitle = reformat(pagetitle)                                       # reformat
      cat_string = ""
      for page in ref_pages_list:
        page_items = separate_text(r'\|', page)
        if page_items[1] == pagetitle:
          cat_string = page_items[2]                                           # extract page categories
        
      # extract info from page depending on namespace value
      namespace_match = re.search(r'<ns>(.+?)</ns>',page_text)
      timestamp_match = re.search(r'<timestamp>(.+?)</timestamp>',page_text)
      redirect_match = re.search(r'#REDIRECT', page_text)
      
      if namespace_match:
        namespace = namespace_match.group(1)
      else:
        outfile.write("No namespace found\n")
      if timestamp_match:
        timestamp = timestamp_match.group(1)
      else:
        timestamp = "none"
      retain_page = False
      
      retain_page = False
      if namespace == "0":   # main pages
        if redirect_match:
          retain_page = False
        elif re.search('Css:',pagetitle):
          retain_page = False
        elif re.search('Forum:',pagetitle):  
          retain_page = False
        elif re.search('Home:',pagetitle):  
          retain_page = False
        elif re.search('Includepopup:',pagetitle):  
          retain_page = False
        elif re.search('Includes:',pagetitle):  
          retain_page = False
        elif re.search('Legal:',pagetitle):  
          retain_page = False
        elif re.search('Main:',pagetitle):  
          retain_page = False
        elif re.search('Maps Home',pagetitle):  
          retain_page = False
        elif re.search('Popuptes:',pagetitle):  
          retain_page = False
        elif re.search('Search:',pagetitle):  
          retain_page = False
        elif re.search('Sitema:',pagetitle):  
          retain_page = False
        elif re.search('System:',pagetitle):  
          retain_page = False
        elif re.search('Tes:',pagetitle):  
          retain_page = False
        elif re.search('Events:',pagetitle):  
          retain_page = False
        elif re.search('Help:',pagetitle):  
          retain_page = False
        elif re.search('Sitemap',pagetitle):
          retain_page = False
        elif re.search('Broken links',pagetitle):
          retain_page = False
        elif re.search('Edit Cheat Sheet',pagetitle):
          retain_page = False
        else:  
          retain_page = True
      elif namespace == "3000":
        retain_page = True
      elif namespace == "3002":
        retain_page = True
      elif namespace == "3004":
        retain_page = True
      elif namespace == "3006":
        retain_page = True
      elif namespace == "3008":
        retain_page = True
         
      if retain_page:
        print("Namespace:",namespace, pagetitle)
        outfile.write("\n\nProcessing page " + pagetitle + "\n")
        text_match = re.search(r'<text(.+?)<\/text>', page_text, re.DOTALL)     # find next page
        if text_match != None:
          wikitext = text_match.group(1) 
          editing = EditString()
          editing = clean_wikitext(wikitext, editing)  
          cleantext = editing.n_string()
          
          found = True 
          text_length = len(cleantext)
          m_pt = 0
          while found:
            link_p = re.search(r'\[(.+?)\]', cleantext[m_pt:], re.DOTALL)  # search for links [ .... ]
            if link_p != None:
              link_text = link_p.group(1)
              link_items = separate_text(r'\s',link_text)
              if len(link_items) >= 1:
                if link_items[0][0:4] == "http":  # link found
                  URL = link_items[0]
                  outfile.write("URL: " + URL + "\n")
                  nlinks += 1
                  print("Page ",str(numpage),"    link# ",str(nlinks),"\r",end='')
                  
#                  test_link(URL)
                  error_code = fetch_data_with_retry(URL)  # test the external link
                  if error_code != "":
                    if search_exceptions(pagetitle, URL, error_code, exceptions):  # if already in exceptions list, ignore this apparently broken link
                      outfile.write("Link identified in exceptions:" + URL + "\n")
                    else:
                      print("Link error:", error_code,"in",pagetitle,"not in exceptions list (URL:", URL,")")
                      location = int(m_pt*100/text_length)
                      error_text = pagetitle + "|" + str(location) + "|" + error_code + "|" + URL + "|" + cat_string 
                      broken_links += [error_text]
                      new_exceptions += [pagetitle + "|" + URL + "|" + error_code]
                  
                  time.sleep(0.5)
              m_pt = link_p.end() + m_pt   
            else:
              found = False      
        
           
        page_entry = (newpagetitle + " | " + pagetitle )
        outfile.write(page_entry + "\n")
      
      
  else:
    page_data = False      


if len(new_exceptions) > 0:
  exceptions_file = open(wkg_folder + exceptions_file_name, "a", encoding = "utf-8")
  for exception in new_exceptions:
    exceptions_file.write(exception + "\n")
  exceptions_file.close()  
    
if len(new_exceptions) > 0:   
  outstring = ""
  for state in states:
    nlinks = 0 
    outstring = "\n\n==" + state + "==\n\n"
    for link in broken_links:
      items = separate_text(r'\|',link)
      page = items[0]
      position = items[1]
      URL = items[3]
      error_code = items[2]
      cat_string = items[4]
      cats = separate_text(r'\;', cat_string)
      for cat in cats:
        if cat == state:
          nlinks += 1
          outstring += "[[" + page + "]] at " + position + "% has link error " + error_code + " for URL [" + URL + " " + URL + "]<br>\n"

    if nlinks > 0:
      broken_links_file.write(outstring + "\n\n")

broken_links_file.close()          

#pages_done_file.close()
outfile.close()

            
