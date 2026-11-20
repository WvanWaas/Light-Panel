"""P1 counter energy × matching Tibber intervals; missing data never means zero."""
import asyncio,datetime as dt,math,time
from fastapi import HTTPException
import httpx
UTC=dt.timezone.utc
DEFAULTS={'import':'sensor.p1_meter_energy_import','export':'sensor.p1_meter_energy_export','power':'sensor.p1_meter_power'}
def numeric(value):return float(value) if type(value) in [int,float] and math.isfinite(value) else None
def stamp(value):
    try:
        if isinstance(value,(int,float)):return dt.datetime.fromtimestamp(value/1000 if value>1e11 else value,UTC)
        result=dt.datetime.fromisoformat(value.replace('Z','+00:00'))
        return result.astimezone(UTC) if result.tzinfo else None
    except (ValueError,TypeError,AttributeError,OverflowError):return None

def series(rows,start,cutoff,field):
    result={}
    for row in rows if isinstance(rows,list) else []:
        if not isinstance(row,dict):continue
        a,b=stamp(row.get('start')),stamp(row.get('end'));value=numeric(row.get(field))
        if not a or not b or a<start or b>cutoff or (b-a).total_seconds()!=300:continue
        if field=='change' and value is not None:
            if value < -1e-8:value=None
            elif value<0:value=0.0
        result[a]=(b,value)
    return result

def analyze(statistics,sources,prices,start,cutoff,export_mode='unknown',export_rate=None):
    if export_mode not in ['unknown','same','fixed']:raise HTTPException(400,'Kies een geldige terugleverberekening.')
    if export_mode=='fixed' and (numeric(export_rate) is None or not -10<=export_rate<=10):raise HTTPException(400,'Voer een geldige terugleverprijs in EUR/kWh in.')
    imported=series(statistics.get(sources['import'],[]),start,cutoff,'change');exported=series(statistics.get(sources['export'],[]),start,cutoff,'change');power=series(statistics.get(sources['power'],[]),start,cutoff,'mean')
    price_rows=[]
    for point in prices.get('points',[]):
        a,b,p=stamp(point.get('start')),stamp(point.get('end')),numeric(point.get('price'))
        if a and b and b>a and p is not None:price_rows.append({'start':a,'end':b,'price':p,'import_kwh':0.,'export_kwh':0.,'import_seconds':0,'export_seconds':0,'import_cost_eur':0.,'export_value_eur':0.})
    price_rows.sort(key=lambda p:p['start'])
    # Overlapping prices are ambiguous; never assign energy twice.
    for previous,current in zip(price_rows,price_rows[1:]):
        if current['start']<previous['end']:raise HTTPException(503,'Overlappende prijsperioden; berekening niet betrouwbaar.')
    points=[];import_sum=export_sum=0.;import_seconds=export_seconds=0;matched_seconds=0;price_time_sum=0.;cost=export_value=priced_import=priced_export=0.;priced_import_seconds=priced_export_seconds=0;common_net=common_import_cost=common_export_value=0.;common_seconds=0
    a=start
    while a+dt.timedelta(minutes=5)<=cutoff:
        b=a+dt.timedelta(minutes=5);iv=imported.get(a,(None,None))[1];ev=exported.get(a,(None,None))[1];pv=power.get(a,(None,None))[1]
        if iv is not None:import_sum+=iv;import_seconds+=300
        if ev is not None:export_sum+=ev;export_seconds+=300
        # Counter-derived signed average is a fallback, not a substitute for missing kWh.
        kw=pv/1000 if pv is not None else (iv-ev)*12 if iv is not None and ev is not None else None
        matches=[p for p in price_rows if p['start']<=a and b<=p['end']]
        rate=matches[0]['price'] if len(matches)==1 else None
        period=matches[0] if len(matches)==1 else None
        if rate is not None and iv is not None:
            cost+=iv*rate;priced_import+=iv;priced_import_seconds+=300;matched_seconds+=300;price_time_sum+=rate*300
            period['import_kwh']+=iv;period['import_seconds']+=300;period['import_cost_eur']+=iv*rate
        export_price=rate if export_mode=='same' else export_rate if export_mode=='fixed' else None
        if ev is not None and period is not None:
            period['export_kwh']+=ev;period['export_seconds']+=300
        if ev is not None and export_price is not None:
            export_value+=ev*export_price;priced_export+=ev;priced_export_seconds+=300
            if period is not None:period['export_value_eur']+=ev*export_price
        if iv is not None and ev is not None and rate is not None and export_price is not None:
            common_import_cost+=iv*rate;common_export_value+=ev*export_price;common_net+=iv*rate-ev*export_price;common_seconds+=300
        points.append({'start':a.isoformat(),'end':b.isoformat(),'power_kw':kw,'power_basis':'P1-gemiddelde' if pv is not None else 'Uit energietellers' if kw is not None else None,'import_kwh':iv,'export_kwh':ev,'price':rate})
        a=b
    expected=max(0,int((cutoff-start).total_seconds()));coverage=lambda seconds:seconds/expected if expected else 0.
    reference_rate=price_time_sum/matched_seconds if matched_seconds else None
    reference_cost=priced_import*reference_rate if reference_rate is not None else None
    net=common_net if common_seconds else None
    periods=[]
    for p in price_rows:
        expected_period=max(0,(min(p['end'],cutoff)-max(p['start'],start)).total_seconds())
        if not expected_period:continue
        periods.append({'start':p['start'].isoformat(),'end':p['end'].isoformat(),'price':p['price'],'expected_seconds':expected_period,
                        'import_kwh':p['import_kwh'] if p['import_seconds'] else None,'export_kwh':p['export_kwh'] if p['export_seconds'] else None,
                        'import_cost_eur':p['import_cost_eur'] if p['import_seconds'] else None,
                        'export_value_eur':p['export_value_eur'] if export_mode!='unknown' and p['export_seconds'] else None,
                        'import_complete':p['import_seconds']==expected_period,'export_complete':p['export_seconds']==expected_period})
    return {'points':points,'periods':periods,'as_of':max((stamp(p['end']) for p in points if p['import_kwh'] is not None or p['export_kwh'] is not None or p['power_kw'] is not None),default=None),
            'import_kwh':import_sum if import_seconds else None,'export_kwh':export_sum if export_seconds else None,
            'import_cost_eur':cost if priced_import_seconds else None,'export_value_eur':export_value if priced_export_seconds else None,'net_cost_eur':net,'net_import_cost_eur':common_import_cost if common_seconds else None,'net_export_value_eur':common_export_value if common_seconds else None,
            'effective_import_price':cost/priced_import if priced_import>0 else None,'reference_price':reference_rate,'reference_cost_eur':reference_cost,
            'timing_difference_eur':reference_cost-cost if reference_cost is not None else None,'priced_import_kwh':priced_import if priced_import_seconds else None,
            'expected_seconds':expected,'net_coverage':coverage(common_seconds),'import_coverage':coverage(import_seconds),'export_coverage':coverage(export_seconds),'priced_import_coverage':coverage(priced_import_seconds),
            'export_mode':export_mode,'export_rate':export_rate if export_mode=='fixed' else None,'complete':bool(expected) and import_seconds==expected and export_seconds==expected and priced_import_seconds==expected,
            'priced_as_of':max((stamp(p['end']) for p in points if p['import_kwh'] is not None and p['price'] is not None),default=None),
            'basis':'P1-tellerveranderingen per 5 minuten × prijs van die periode. Geen vaste kosten, saldering of jaarafrekening.'}

class EnergyDayProvider:
    def __init__(self,provider):self.provider=provider;self.cache={};self.lock=asyncio.Lock()
    async def day(self,date='',export_mode='unknown',export_rate=None,refresh=False,now=None):
        if export_mode not in ['unknown','same','fixed']:raise HTTPException(400,'Onbekende teruglevermethode.')
        if export_mode=='fixed' and (numeric(export_rate) is None or not -10<=export_rate<=10):raise HTTPException(400,'Ongeldige terugleverprijs.')
        p=self.provider;now=now or dt.datetime.now(p.zone())
        try:day=dt.date.fromisoformat(date) if date else now.date()
        except ValueError:raise HTTPException(400,'Ongeldige datum.')
        if day>now.date() or (now.date()-day).days>7:raise HTTPException(400,'Kies vandaag of maximaal zeven dagen geleden.')
        start=dt.datetime.combine(day,dt.time.min,p.zone()).astimezone(UTC);end=dt.datetime.combine(day+dt.timedelta(days=1),dt.time.min,p.zone()).astimezone(UTC)
        cutoff=min(end,dt.datetime.fromtimestamp(math.floor(now.timestamp()/300)*300,UTC))
        config=p.config().get('p1_day',{});sources={k:config.get(k) or value for k,value in DEFAULTS.items()}
        key=(day.isoformat(),tuple(sources.values()))
        async with self.lock:
            cached=self.cache.get(key)
            if not refresh and cached and time.monotonic()-cached['time']<120:statistics,cached_cutoff=cached['data'];cutoff=cached_cutoff
            else:
                if p.connection()[2]:raise HTTPException(503,'Geen P1-statistieken zonder Home Assistant.')
                if cutoff<=start:statistics={}
                else:
                    try:
                        async with p.client() as client:
                            response=await client.post('api/services/recorder/get_statistics',params={'return_response':''},json={'start_time':start.isoformat(),'end_time':cutoff.isoformat(),'statistic_ids':list(sources.values()),'period':'5minute','types':['change','mean'],'units':{'energy':'kWh','power':'W'}});response.raise_for_status()
                        statistics=response.json().get('service_response',{}).get('statistics',{})
                        if not isinstance(statistics,dict):raise ValueError()
                    except (httpx.HTTPError,ValueError,TypeError,AttributeError):raise HTTPException(503,'P1-historie niet bereikbaar. Controleer HA-statistieken en de P1-bronnen.')
                self.cache={key:{'time':time.monotonic(),'data':(statistics,cutoff)}}
        prices=await p.day_prices(day.isoformat());analysis=analyze(statistics,sources,prices,start,cutoff,export_mode,export_rate)
        for field in ['as_of','priced_as_of']:
            if analysis[field] is not None:analysis[field]=analysis[field].isoformat()
        return {'date':day.isoformat(),'start':start.isoformat(),'end':end.isoformat(),'timezone':str(p.zone()),'sources':sources,'prices':prices,'analysis':analysis,'generated_at':now.isoformat()}
