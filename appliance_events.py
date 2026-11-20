"""Read-only appliance reminders. No HA service calls or device control."""
from live_ticker import timestamp

def appliance_events(engine, states, settings, now, online):
 if not online:
  engine.fault_since.clear()
  return
 wash=settings.get('laundry',{});machine=states.get(wash.get('entity'),{});door=states.get(wash.get('door'),{})
 status=machine.get('state');opened=door.get('state');changed=timestamp(machine.get('last_changed'))
 tracker=engine.appliances.setdefault('laundry',{})
 # An actual completion is required; an idle/off machine never starts a timer.
 if status=='program_ended' and changed and changed<=now:
  episode=changed.isoformat()
  if episode!=tracker.get('completion') and not tracker.get('pending'):
   tracker.update(completion=episode,pending=episode)
 pending=timestamp(tracker.get('pending'))
 door_changed=timestamp(door.get('last_changed'))
 # A later closed transition also proves the door was opened during downtime.
 handled=opened=='on' or pending and opened=='off' and door_changed and door_changed>pending
 if handled or status in ('in_use','programmed','program_interrupted','failure'):
  tracker.pop('pending',None);tracker.pop('card',None);engine.active.pop('laundry',None)
 elif pending and opened=='off' and status not in (None,'unknown','unavailable','not_connected'):
  delay=wash.get('delay_minutes',30)
  if (now-pending).total_seconds()>=delay*60:
   if tracker.get('card'):engine.active.setdefault('laundry',tracker['card'])
   engine.ongoing('laundry','laundry','Wasgoed vergeten?',f'De wasmachine is al minstens {delay} minuten klaar. De deur is nog niet geopend.',now)
   tracker['card']=engine.active['laundry']
 for group in settings.get('fault_groups',[]):
  key='fault:'+group['id'];problems=[];known=True
  for source in group['sources']:
   value=states.get(source['entity'],{}).get('state')
   if value in (None,'unknown','unavailable',''):
    known=False;continue
   if 'above' in source:
    try:active=float(value)>source['above']
    except (ValueError,TypeError):known=False;continue
   else:active=value in source.get('states',[])
   if active:problems.append(source['label']+' ('+str(value)+')')
  if problems:
   since=engine.fault_since.setdefault(key,now)
   if (now-since).total_seconds()>=settings.get('fault_delay_seconds',60):
    engine.ongoing(key,'fault',group['title'],' · '.join(problems),now)
  else:
   engine.fault_since.pop(key,None)
   if known:engine.active.pop(key,None)
