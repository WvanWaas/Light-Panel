"""Local dashboard test cards. Never sends a message to emergency services or HA."""
import datetime as dt
import uuid
from fastapi import HTTPException

KINDS={'fire':'Brandweer','ambulance':'Ambulance','grip':'GRIP','flight':'Vliegtuig','aurora':'Noorderlicht','sites':'Websites','energy':'Laadmoment','air':'Luchten'}
def test_card(kind,now=None):
    if kind not in KINDS:raise HTTPException(400,'Kies een beschikbare testmelding.')
    now=now or dt.datetime.now(dt.timezone.utc)
    seconds=1800 if kind=='grip' else 300 if kind=='flight' else 600
    item={'id':uuid.uuid4().hex[:20],'kind':'flight' if kind=='flight' else 'p2000' if kind in ('fire','ambulance','grip') else kind,'title':'TEST · '+KINDS[kind],'message':'TESTMELDING · '+('Amsterdam → Londen' if kind=='flight' else 'Voorbeeld voor de kaartenbak'),'time':now.isoformat(),'expires_at':(now+dt.timedelta(seconds=seconds)).isoformat(),'priority':30 if kind=='flight' else 80,'is_test':True}
    if kind=='flight':
        item['last_seen']=now.isoformat()
        item['flight']={'vehicle':'plane','code':'TEST123','registration':'TEST','origin':'Amsterdam','destination':'Londen','origin_country':'NL','destination_country':'GB','airline':'TESTVLUCHT','model':'Voorbeeldtoestel','altitude_m':1200,'speed_kmh':350}
    elif kind in ('fire','ambulance','grip'):item['service']=kind
    return item
