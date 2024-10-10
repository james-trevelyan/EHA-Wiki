'''  summaries.py 
 
 Python script to process XML data files to produce summaries of person, profile, organisation pages
 
 This script downloads the text of pages not already listed in the summaries.txt file.

 Scans an exported XML file of the entire site
 1) Imports a pages file containing a list of pages as produced by the sitemap script
 2) Downloads each page text and asks OpenAI to generate a summary
 3) Writes a file comtaining all the original information, with summary text added to each entry
 
 Must be run in the site packages folder for user-based Python installation
 Note that the pages file can have the first item on each record edited for generating internal links.
 The second item is the wiki page address.
 
 Version 1.1 240829

'''
import os
import re 
from urllib.parse import unquote
import pywikibot
import time

outfile = open("summaries_log.txt","w",encoding="utf-8")            # log file reporting all operations completed

# Specify the folder paths - note that internally Python uses forward slashes, not backslashes as in Windows/MSDOS
wkg_folder = "C:/Users/HP/OneDrive - Close Comfort Pty Ltd/Documents/Python/" # working directory (with slash)
summaries_file_name = "summaries_eha.txt"                               # list of files available locally in media folder(s)
pages_file_name = "eha_pages_2.txt"                                # pages file name




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
  
#===========================================================================================================
#
# EditString class allows 'snip' to remove text from the original string and the result is in the new string. 
#            allows 'replace' to replace text found in the new string, but the result is impleted on the original string.
# Application - remove unwanted wiki text codes from text, and then search the resulting clean string for keywords which
#               appear in the original text string. When needed, replace text in the original string by finding it in
#               the new string.          
# 
import re

class EditString:
  def __init__(self):
    self.__cut_pt = 0
    self.__ins_pt = 0
    self.__o_string = ""
    self.__n_string = ""
    self.__edits = []
    
  def __str__(self):
    return f"{str(self.__cut_pt)} {str(self.__cut_pt)} {str(self.__edits)}\n\"{self.__o_string}\"\n\"{self.__n_string}\""
    
  def set_o_string(self, text):
    self.__o_string = text
    self.__n_string = text
    return
    
  def reset(self, text):
    self.__cut_pt = 0
    self.__ins_pt = 0
    self.__o_string = text
    self.__n_string = text
    self.__edits = []
    return
  
  def n_string(self):
    return self.__n_string
    
  def o_string(self):
    return self.__o_string
    
  def snip(self, st_pt, en_pt):  # remove a section of the string: the string to be edited is in n_string. o_string remains unchanged.
                                 # st_pt, en_pt are positions on the n_string which is returned edited after the snip
    offset = 0
    snipped = False
    new_edits =[]
    length = en_pt - st_pt
    #print("Snip at:",str(st_pt))

    if self.__edits == []:
      new_edits = [(st_pt, en_pt, st_pt)]
      self.__n_string = self.__n_string[:st_pt] + self.__n_string[en_pt:]
      snipped = True
      #print("0-snip")

    else:
      for edit in self.__edits:
        if edit[2] >= st_pt:
          if not snipped:
            new_edits += [(st_pt + offset, en_pt + offset, st_pt)]  # creat edit record and delete text from n_string
            snipped = True
            self.__n_string = self.__n_string[:st_pt] + self.__n_string[en_pt:]
            #print("-snip-")
          new_edits += [(edit[0], edit[1], edit[2]-length)] # subsequent edits all have to be mvoed back after n_string shortened
        else:  
          new_edits += [edit]  # build new list of edits
          offset += edit[1] - edit[0]  # increment offset by length of snipped section
          #print("skip")

    if not snipped:
      new_edits += [(st_pt + offset, en_pt + offset, st_pt)]
      snippped = True
      self.__n_string = self.__n_string[:st_pt] + self.__n_string[en_pt:]
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
      
  def replace(self, st_pt, en_pt, text):  # replace text from st_pt to en_pt in original string
    new_o_string = self.__o_string[:st_pt] + text + self.__o_string[en_pt:]
    new_edits = []
    offset = 0
    diff = len(text) - (en_pt - st_pt)
    inserted = False
    for edit in self.__edits:
      if edit[0] >= st_pt:
        if not inserted:
          inserted = True
          new_edits += [(st_pt, st_pt + diff, st_pt-offset)]
        new_edits += [(edit[0] + diff, edit[1]+diff, edit[2])]
      else:
        offset += edit[1] - edit[0]
        new_edits += [edit]
     
    self.__edits = new_edits   
    self.__o_string = new_o_string
    return new_o_string
   
    
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
    pat_p = re.search(r'\[\[(.+?)\]\]', search_string[m_pt:]) # remove [[ --- ]] links
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

#  editing.checker() 
  m_pt = 0
  search_string = editing.n_string()
  finished = False
  while not finished:
    pat_p = re.search(r'References', search_string[m_pt:]) # remove References and all following text
    if pat_p != None:
      en_pt = pat_p.end() + m_pt
      st_pt = pat_p.start() + m_pt
#      print("snipping References... ",str(s_pt),str(m_pt))  
      search_string = editing.snip(st_pt,len(search_string) - m_pt - 1) # in case of references, cut off all of the rest of the text
      m_pt = st_pt 
    else:
      finished = True

#   editing.checker() 

#  outfile.write("\n\n================\n" + editing.n_string() + "\n================\n\n")  
  return editing



#=====================================================================================
#
# Get Summary from OpenAI
#
#
from openai import OpenAI
# https://www.perplexity.ai/hub/blog/introducing-pplx-api
# Models: https://docs.perplexity.ai/docs/model-cards
# OpenAI home page: https://pypi.org/project/openai/
# https://github.com/openai/openai-python/tree/main/examples
#
def get_summary(prompt):

  
  YOUR_API_KEY = "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"
  
  messages = [
      {
          "role": "user",
          "content": prompt,
      },
  ]
  #print(messages)
  
  client = OpenAI(api_key=YOUR_API_KEY, base_url="https://api.perplexity.ai")
  
  # demo chat completion without streaming
  response = client.chat.completions.create(
      model="llama-3.1-sonar-large-128k-online", #"llama-3-sonar-small-32k-online",
      messages=messages,
  )
  
  reply = response.choices[0].message.content   
  print("First reply ",reply)  
     
#  period_p = re.search(r'\.',reply,re.DOTALL)
#  if period_p:
#    if period_p.end() < 10:  #  There is a period very soon in the reply text, look for the next one instead
#      reply_1 = reply[:period_p.end()]
#      reply_2 = reply[period_p.end():]
#      period_p = re.search(r'\.',reply_2,re.DOTALL)
#      short_reply = reply_1 + reply_2[:period_p.end()]
#    else:
#      short_reply = reply[:period_p.end()]
#  
  #print("Final reply: ",short_reply)

  return reply
#  return short_reply



#=======================================================================================================
#
# function to read list from a file
#
def read_list_file(file_name):
  with open(file_name,"r",encoding="utf-8") as file:
    list = file.read().splitlines()
  file.close()  
  return list 

 
#=======================================================================================================
#
#  Main Sequence
#
#  1) Read list of pages (will have items separated by | characters)
#     items: name on page, wiki_page, categories list, timestamp, lifespan (if present)
#  2) Retrieve wiki text, clean the text 
#  3) Ask for summary from OpenAI
#  4) Append summary to pages list item
#  5) Re-write pages list with summary info
#

page_list = read_list_file(wkg_folder + pages_file_name)
editing = EditString()
new_pages = []
summaries_file = open(wkg_folder+summaries_file_name,"a",encoding="utf-8")  

n_pages = 0

for page_entry in page_list:
  items = separate_text(r'\|',page_entry)
  n_pages += 1
  print(items)
  
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
    
  if success:
     
    outfile.write("\n\n\nPage text for " + page_name + ":============\n" + page_text + "\n============\n")
  
    editing.reset(page_text)
    editing = clean_wikitext(page_text, editing)
    
    cleantext = editing.n_string()
    
    p_items = separate_text(r'\:',page_name)
    print(p_items[0])
    if p_items[0] == "Person":
      prompt = "Summarize the following biography in about 20 words, emphasizing the engineering achievements, without mentioning the person's name. \n"
    elif p_items[0] == "Profile":
      prompt = "Summarize the following biography in about 20 words, emphasizing the engineering achievements, without mentioning the person's name. \n"
    elif p_items[0] == "Place":
      prompt = "Summarize the following place description in about 20 words, emphasizing the engineering achievements, without mentioning the place name. \n"
    elif p_items[0] == "Organisation":
      prompt = "Summarize the following description of an organisation in about 20 words, emphasizing the engineering achievements, without mentioning the organisation's name. \n"
    else:
      prompt = "Summarize the following text in about 20 words. \n"
    
        
    if len(cleantext)/6 > 50:  # longer than about 50 words?
    
      reply = get_summary(prompt + cleantext)
    
    else:
    
      reply = "Too short to summarise: " + cleantext[0:100] + "....." 
    
    outfile.write("Reply: " + reply + "\n\n")
    new_page_entry = page_entry + "|" + reply
    summaries_file.write(new_page_entry + "\n")
  
  time.sleep(4.0)  #  keep the process slower than 4 seconds per entry
  
summaries_file.close()  
outfile.close()  