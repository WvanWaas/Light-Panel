"""Validate only supported operations for explicitly allowlisted lights."""
import math
from fastapi import HTTPException
DIM_MODES={'brightness','color_temp','hs','xy','rgb','rgbw','rgbww','white'}
COLOR_MODES={'hs','xy','rgb','rgbw','rgbww'}
def light_action(data,config,states):
    entity=data.get('entity_id')
    if entity not in config.get('lights',[]):raise HTTPException(403,'Lamp niet toegestaan.')
    source=states.get(entity,{})
    if source.get('state') not in ['on','off']:raise HTTPException(409,'Lamp momenteel niet beschikbaar.')
    if set(data)-{'key','entity_id','brightness_pct','rgb_color','color_temp_kelvin'}:raise HTTPException(422,'Onbekende lampinstelling.')
    attrs=source.get('attributes',{});modes=set(attrs.get('supported_color_modes') or [])
    output={}
    def integer(value,minimum,maximum):
        return type(value) is int and minimum<=value<=maximum
    if 'brightness_pct' in data:
        if not modes&DIM_MODES:raise HTTPException(422,'Deze lamp ondersteunt geen dimmen.')
        if not integer(data['brightness_pct'],0,100):raise HTTPException(422,'Helderheid moet tussen 0 en 100% liggen.')
        output['brightness_pct']=data['brightness_pct']
    if 'rgb_color' in data:
        if not modes&COLOR_MODES:raise HTTPException(422,'Deze lamp ondersteunt geen kleurkeuze.')
        rgb=data['rgb_color']
        if not isinstance(rgb,list) or len(rgb)!=3 or not all(integer(v,0,255) for v in rgb):raise HTTPException(422,'Ongeldige RGB-kleur.')
        output['rgb_color']=rgb
    if 'color_temp_kelvin' in data:
        if 'color_temp' not in modes:raise HTTPException(422,'Deze lamp ondersteunt geen instelbaar witlicht.')
        minimum,maximum=attrs.get('min_color_temp_kelvin'),attrs.get('max_color_temp_kelvin')
        if not all(type(v) in [int,float] and math.isfinite(v) for v in [minimum,maximum]) or minimum>maximum:raise HTTPException(409,'Witlichtbereik ontbreekt in HA.')
        if not integer(data['color_temp_kelvin'],minimum,maximum):raise HTTPException(422,'Witlichtinstelling buiten het lampbereik.')
        output['color_temp_kelvin']=data['color_temp_kelvin']
    if not output:raise HTTPException(422,'Kies een lampinstelling.')
    if 'rgb_color' in output and 'color_temp_kelvin' in output:raise HTTPException(422,'Kies kleur of witlicht, niet beide tegelijk.')
    return {'service':'light.turn_on','entity_id':entity,'data':output}
