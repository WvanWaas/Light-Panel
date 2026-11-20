"""Resolve only explicitly configured thermostat commands, within HA capabilities."""
import math
from fastapi import HTTPException

def thermostat_action(data,config,states):
    entity=data.get('entity_id')
    if entity not in config.get('thermostats',{}).values():raise HTTPException(403,'Thermostaat niet toegestaan.')
    source=states.get(entity,{})
    if source.get('state') in [None,'unknown','unavailable']:raise HTTPException(409,'Thermostaat momenteel niet beschikbaar.')
    attributes=source.get('attributes',{})
    if data.get('key')=='thermostat_temperature':
        value=data.get('temperature');minimum=attributes.get('min_temp');maximum=attributes.get('max_temp');step=attributes.get('target_temp_step')
        if type(value) not in [int,float] or not math.isfinite(value):raise HTTPException(422,'Voer een geldige temperatuur in.')
        if any(type(v) not in [int,float] or not math.isfinite(v) for v in [minimum,maximum,step]) or step<=0:raise HTTPException(409,'Temperatuurbereik of stapgrootte ontbreekt in HA.')
        if not minimum<=value<=maximum:raise HTTPException(422,f'Temperatuur moet tussen {minimum:g} en {maximum:g} °C liggen.')
        steps=(value-minimum)/step
        if abs(steps-round(steps))>1e-5:raise HTTPException(422,f'Gebruik stappen van {step:g} °C.')
        return {'service':'climate.set_temperature','entity_id':entity,'data':{'temperature':value}}
    if data.get('key')=='thermostat_mode':
        mode=data.get('hvac_mode')
        if not isinstance(mode,str) or mode not in attributes.get('hvac_modes',[]):raise HTTPException(422,'Deze stand wordt niet ondersteund door de thermostaat.')
        return {'service':'climate.set_hvac_mode','entity_id':entity,'data':{'hvac_mode':mode}}
    raise HTTPException(403,'Thermostaatactie niet toegestaan.')
