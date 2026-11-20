"""Select only the configured local weather providers, in priority order."""
import re


def weather_source(config, states):
    primary = config.get('weather')
    fallbacks = config.get('weather_fallbacks', [])
    if not isinstance(fallbacks, list): fallbacks = []
    candidates = [primary, *fallbacks] if primary else sorted(k for k in states if k.startswith('weather.'))
    for entity in dict.fromkeys(x for x in candidates if isinstance(x, str) and re.fullmatch(r'weather\.[a-z0-9_]+', x)):
        current = states.get(entity, {})
        if current.get('state') and current['state'] not in ('unknown', 'unavailable'):
            return {'entity_id': entity, 'current': current, 'primary_entity_id': primary,
                    'is_fallback': bool(primary and entity != primary)}
    return None
