"""Persistent notification archive, independent of stack visibility and expiry."""
import base64
import datetime as dt
import hashlib
import json
import sqlite3
import threading
import math
from contextlib import contextmanager
from pathlib import Path
from live_ticker import timestamp

CATEGORIES={'grip','fire','ambulance','flight','other','aurora','sites','energy','air','laundry','fault'}
def category(item):return item.get('service','other') if item.get('kind')=='p2000' and item.get('service') in CATEGORIES else item.get('kind') if item.get('kind') in CATEGORIES else 'other'
def history_id(item):return hashlib.sha256((str(item['id'])+'|'+str(item['time'])).encode()).hexdigest()[:24]

class NotificationArchive:
 def __init__(self,path):self.path=Path(path);self.lock=threading.RLock();self.ready=False;self.last={}
 @contextmanager
 def connect(self):
  self.path.parent.mkdir(parents=True,exist_ok=True)
  connection=sqlite3.connect(self.path,timeout=5)
  try:
   if not self.ready:
    connection.execute('PRAGMA journal_mode=WAL');connection.execute('CREATE TABLE IF NOT EXISTS cards(id TEXT PRIMARY KEY,original_id TEXT NOT NULL,event_time REAL NOT NULL,category TEXT NOT NULL,is_test INTEGER NOT NULL,payload TEXT NOT NULL)');connection.execute('CREATE INDEX IF NOT EXISTS cards_time ON cards(event_time DESC,id DESC)');connection.execute('CREATE TABLE IF NOT EXISTS feed_state(name TEXT PRIMARY KEY,payload TEXT NOT NULL)');connection.commit();self.path.chmod(0o600);self.ready=True
   yield connection
   connection.commit()
  except Exception:
   connection.rollback()
   raise
  finally:connection.close()
 def remember(self,items):
  with self.lock:
   rows=[];fingerprints={}
   for item in items:
    at=timestamp(item.get('time'))
    if at is None:continue
    key=history_id(item);copy={k:v for k,v in item.items() if k!='history_id'};copy.update(id=key,history_id=key,original_id=item['id']);payload=json.dumps(copy,ensure_ascii=False,sort_keys=True);fingerprints[key]=payload
    if self.last.get(key)!=payload:rows.append((key,item['id'],at.timestamp(),category(item),int(bool(item.get('is_test'))),payload))
   if rows:
    with self.connect() as db:db.executemany('INSERT INTO cards VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload',rows)
   self.last=fingerprints
 def page(self,categories='',before='',limit=50):
  if not 1<=limit<=100:raise ValueError()
  chosen=set(categories.split(',')) if categories else CATEGORIES
  if not chosen<=CATEGORIES:raise ValueError()
  where=['category IN ('+','.join('?' for _ in chosen)+')'];args=list(sorted(chosen))
  if before:
   try:
    if len(before)>300:raise ValueError()
    at,key=json.loads(base64.urlsafe_b64decode(before.encode()));at=float(at)
    if not math.isfinite(at):raise ValueError()
    if not isinstance(key,str) or len(key)>64:raise ValueError()
   except Exception:raise ValueError() from None
   where.append('(event_time<? OR (event_time=? AND id<?))');args.extend([at,at,key])
  with self.lock,self.connect() as db:
   rows=db.execute('SELECT event_time,id,payload FROM cards WHERE '+' AND '.join(where)+' ORDER BY event_time DESC,id DESC LIMIT ?',args+[limit+1]).fetchall()
  more=len(rows)>limit;rows=rows[:limit];cursor=base64.urlsafe_b64encode(json.dumps(rows[-1][:2]).encode()).decode() if more else None
  return {'items':[json.loads(row[2]) for row in rows],'next':cursor}
 def get(self,key):
  with self.lock,self.connect() as db:row=db.execute('SELECT payload FROM cards WHERE id=? OR original_id=? ORDER BY event_time DESC LIMIT 1',(key,key)).fetchone()
  return json.loads(row[0]) if row else None
 def clear_tests(self):
  with self.lock,self.connect() as db:db.execute('DELETE FROM cards WHERE is_test=1');self.last={}

 def load_feed_state(self):
  with self.lock,self.connect() as db:row=db.execute("SELECT payload FROM feed_state WHERE name='events'").fetchone()
  return json.loads(row[0]) if row else {}
 def save_feed_state(self,state):
  with self.lock,self.connect() as db:db.execute("INSERT INTO feed_state(name,payload) VALUES('events',?) ON CONFLICT(name) DO UPDATE SET payload=excluded.payload",(json.dumps(state,sort_keys=True),))
