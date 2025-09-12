"""
This tiny script seems to fix the path issue that prevented PyWikibot scripts from being run in any folder.
Suggested by claude.ai with JPT 250911
It seems to be only needed once when initializing PyWikibot
"""
import os
import sys
sys.path.insert(0, os.getcwd())