"""Local Tibber detail view. Read-only; credentials never enter the browser."""
from datetime import date
from pathlib import Path
from fastapi import APIRouter, HTTPException
from backend_updates import dashboard_page
import tibber_data as data

router = APIRouter()

@router.get('/tibber')
def tibber_page():
    return dashboard_page(Path(__file__).parent/'static/tibber/index.html')

@router.get('/api/tibber/status')
def status():
    return {'configured': bool(data.TOKEN), 'version': 2}

@router.get('/api/tibber/homes')
def homes():
    try:
        return {'homes': data.homes()}
    except data.ApiError as exc:
        raise HTTPException(exc.status, str(exc)) from None

def read_period(day, home, period='day'):
    try:
        date.fromisoformat(day)
    except ValueError:
        raise HTTPException(400, 'Kies een geldige datum.') from None
    try:
        return data.day_data(day, home) if period == 'day' else data.period_data(day, period, home)
    except data.ApiError as exc:
        raise HTTPException(exc.status, str(exc)) from None

@router.get('/api/tibber/day')
def day(date: str, home: str):
    return read_period(date, home)

@router.get('/api/tibber/period')
def period(date: str, home: str, period: str):
    if period not in ('week', 'month', 'year'):
        raise HTTPException(400, 'Kies week, maand of jaar.')
    return read_period(date, home, period)
