"""Local sun and moon calculations; coordinates remain on the dashboard server."""
import asyncio,datetime as dt,math
from astral import Observer
from astral.sun import sunrise,sunset
from astral.moon import moonrise,moonset,phase
import httpx
LABELS=['Nieuwe maan','Wassende sikkel','Eerste kwartier','Wassende maan','Volle maan','Afnemende maan','Laatste kwartier','Afnemende sikkel']

def calculate(observer,day,zone):
    fraction=phase(day)/28
    result={'date':day.isoformat(),'timezone':str(zone),'phase':fraction,'phase_label':LABELS[int(fraction*8+.5)%8],'sunrise':None,'sunset':None,'moonrise':None,'moonset':None}
    if observer is not None:
        for key,fn in [('sunrise',sunrise),('sunset',sunset),('moonrise',moonrise),('moonset',moonset)]:
            try:
                value=fn(observer,date=day,tzinfo=zone)
                result[key]=value.isoformat() if value and value.astimezone(zone).date()==day else None
            except ValueError:pass
    return result

class Astronomy:
    def __init__(self,provider):self.provider=provider;self.cache={};self.lock=asyncio.Lock()
    async def today(self,now=None):
        p=self.provider;now=now or dt.datetime.now(p.zone());day=now.date()
        async with self.lock:
            if day in self.cache:return self.cache[day]
            observer=None
            if not p.connection()[2]:
                try:
                    async with p.client() as client:
                        response=await client.get('api/config');response.raise_for_status();config=response.json()
                    lat,lon=config.get('latitude'),config.get('longitude')
                    if type(lat) in (int,float) and type(lon) in (int,float) and math.isfinite(lat) and math.isfinite(lon) and -90<=lat<=90 and -180<=lon<=180:observer=Observer(lat,lon)
                except (httpx.HTTPError,ValueError,TypeError,AttributeError):pass
            result=calculate(observer,day,p.zone())
            if observer is not None:self.cache={day:result}
            return result
