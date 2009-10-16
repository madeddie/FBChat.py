#!/usr/bin/python

import mechanize
from mechanize import Browser
import re
import simplejson
import time
import random
import urllib
import sys
 
import threading
from pprint import pprint
 
class FacebookChat (object):
  def __init__ (self, email, password):
    self.email = email
    self.password = password
 
  def login (self):
    self.agent = Browser()
    self.agent.addheaders = [("User-Agent", """Mozilla/5.0 (Macintosh; U; \
                               Intel Mac OS X 10.5; en-US; rv:1.9.0.1) \
                               Gecko/2008070206 Firefox/3.0.1""")]
    self.agent.open("http://facebook.com/login.php")
    self.agent.form = list(self.agent.forms())[0]
 
    self.agent.form["email"] = self.email
    self.agent.form["pass"] = self.password
    body = self.agent.submit().read()

    #self.uid = int('1474791909')
    self.uid = int(re.match(""".+<input type="hidden" id="user" name="user" value="(\d+)" />.+""", body, re.S).group(1))
    #self.channel=re.match('.+"channel(\d+)".+', body, re.S).group(1)
    self.channel = '17'
    self.post_form_id = re.match(""".+<input type="hidden" id="post_form_id" name="post_form_id" value="([^"]+).+""", body, re.S).group(1)
 
    self.seq = None
 
  def wait_for_messages (self):
    self.determine_initial_seq_number() if self.seq == None else None
 
    while True:
      json = self.parse_json(self.agent.open(self.get_message_url(self.seq)).read())
      if json['t'] == 'continue': continue # no messages yet, keep waiting
      if json['t'] == 'refresh':
        #MM
        self.login()
        continue  
      break
    self.seq += 1
 
    out = []
    for info in [m for m in json['ms'] if m['type'] == 'msg' and m['from'] != self.uid]:
      info.update(info['msg'])
      del info['msg']
      #print info
      out.append( (info['from'], time.localtime(info['time']/1000), info['text']) )
 
    return out
 
  def send_message (self, uid, text):
    r = self.agent.open('http://www.facebook.com/ajax/chat/send.php', urllib.urlencode( {
      'msg_text' : text,  
      'msg_id' : random.randint(0, 999999999),  
      'client_time' : long(time.time() * 1000),  
      'to' : uid,  
      'post_form_id' : self.post_form_id 
    }))
 
  def buddy_list (self):
    json = self.parse_json(self.agent.open('http://www.facebook.com/ajax/presence/update.php', urllib.urlencode( {
      'buddy_list' : 1, 'force_render' : 1, 'post_form_id' : self.post_form_id, 'user' : self.uid } )).read())
    json = json['payload']['buddy_list']['userInfos']
 
    return json
 
  def determine_initial_seq_number (self):
    # -1 will always be a bad seq number so fb will tell us what the correct one is  
    self.agent.set_handle_robots(False)
    json = self.parse_json(self.agent.open(self.get_message_url(-1)).read())
    self.seq = int(json['seq'])
 
  def get_message_url(self, seq): 
    return "http://0.channel%s.facebook.com/x/0/false/p_%u=%u" % (self.channel, self.uid, seq)
 
  # get rid of initial js junk, like 'for(;;);'  
  def parse_json (self, s):
    return simplejson.loads(re.sub("""^[^{]+""", '', s))  
 
  def debuginfo (self):
    return "email: " + self.email + ", uid: " + str(self.uid) + ", channel: " +\
            self.channel + ",  seq: " + str(self.seq)
 
 
class ReadThread (threading.Thread):
  def run (self):
    global chat
    while True:
      print chat.wait_for_messages()
 
if __name__ == '__main__':
  global chat
 
  chat = FacebookChat(sys.argv[1], sys.argv[2])
  chat.login()
  json = chat.buddy_list()
  for user in json:
    print user, json[user]['name']
  t = ReadThread()
  t.start()
 
  errs = 0
  while True:
    try:
      s = raw_input().split(" ", 1)
      try:
        id = long(s[0])
        m = s[1]
        print "sending"
        chat.send_message(id, m)
        errs = 0
      except:
        action = s[0]
        if action == 'buddylist' or action == 'blist':
          print "buddylist loading"
          json = chat.buddy_list()
          for user in json:
            print user, json[user]['name']
          errs = 0
        elif action == 'quit':
          print "quitting..."
          errs = 5
          quit()
        elif action == 'info':
          print chat.debuginfo()
          errs = 0
        elif action == 'reseq' or action == 'resquence':
          print "resequencing"
          chat.determine_initial_seq_number()
          errs = 0
        elif action == 'relogin':
          print "relogging in"
          chat.login()
          errs = 0
        else:
          print action
    except Exception as inst:
      errs += 1
      if errs > 5: break
      print "oops"
      print inst
  quit()
