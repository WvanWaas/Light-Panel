"""Read-only availability checks for the configured company websites."""
import asyncio
import datetime as dt
import time
import httpx


class SiteMonitor:
    def __init__(self,client_factory=None,domains=()):
        self.domains=tuple(domains)
        self.client_factory=client_factory or (lambda:httpx.AsyncClient(timeout=8,follow_redirects=True,max_redirects=5,headers={'User-Agent':'HomeHub-Availability/1.0'}))
        self.results={}
        self.last_check=0
        self.lock=asyncio.Lock()

    async def check(self,force=False):
        async with self.lock:
            if self.results and time.monotonic()-self.last_check<(10 if force else 60):return self.payload()
            async with self.client_factory() as client:
                semaphore=asyncio.Semaphore(5)
                async def one(domain):
                    async with semaphore:
                        started=time.monotonic();code=None;reason=None
                        try:
                            async with asyncio.timeout(10):
                                async with client.stream('GET','https://'+domain) as response:code=response.status_code
                            status='online' if 200<=code<400 else 'protected' if code in (401,403) else 'error'
                        except (httpx.TimeoutException,TimeoutError):status,reason='offline','Time-out'
                        except httpx.HTTPError as exc:
                            status,reason='offline','TLS- of verbindingsfout' if isinstance(exc,httpx.ConnectError) else 'Verbindingsfout'
                        now=dt.datetime.now(dt.timezone.utc).isoformat()
                        old=self.results.get(domain,{})
                        reachable=status in ('online','protected')
                        return domain,{'domain':domain,'url':'https://'+domain,'status':status,'http_status':code,'reason':reason,'response_ms':round((time.monotonic()-started)*1000),'checked_at':now,'last_online':now if reachable else old.get('last_online'),'unavailable_since':None if reachable else old.get('unavailable_since') or now}
                self.results=dict(await asyncio.gather(*(one(domain) for domain in self.domains)))
            self.last_check=time.monotonic()
            return self.payload()

    def payload(self):return {'sites':[self.results.get(domain,{'domain':domain,'url':'https://'+domain,'status':'unknown'}) for domain in self.domains]}

    async def run(self):
        while True:
            try:await self.check()
            except Exception:pass
            await asyncio.sleep(60)
