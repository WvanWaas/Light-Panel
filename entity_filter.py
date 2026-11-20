"""Keep only states used by the dashboard instead of copying the whole HA installation."""
import re
from measurements import EXTRA_MEDIA
ENTITY=re.compile(r'^(?:alarm_control_panel|sensor|binary_sensor|sun|light|weather|calendar|climate|fan|switch|input_select|input_boolean|cover|media_player|camera|script|automation|select|number|button|person|device_tracker)\.[a-z0-9_]+$')
def configured_entities(config):
    notifications=config.get('notifications',{})
    found={'sun.sun','sensor.example_daylight_percentage',notifications.get('garage_entity','binary_sensor.example_garage_open'),notifications.get('handled_entity','input_boolean.example_waste_handled')}
    p1=config.get('p1_day',{})
    found.update(p1.get(k) or default for k,default in [('import','sensor.p1_meter_energy_import'),('export','sensor.p1_meter_energy_export'),('power','sensor.p1_meter_power')])
    def visit(value):
        if isinstance(value,dict):
            for item in value.values():visit(item)
        elif isinstance(value,list):
            for item in value:visit(item)
        elif isinstance(value,str) and ENTITY.fullmatch(value):found.add(value)
    visit(config)
    found.update(entity for _,entity in EXTRA_MEDIA.values())
    return found
class EntityFilter:
    def __init__(self,config):self.ids=configured_entities(config);self.auto_weather=not config.get('weather')
    def includes(self,entity):return entity in self.ids or self.auto_weather and entity.startswith('weather.')
    def select(self,rows):return [row for row in rows if self.includes(row.get('entity_id',''))]
