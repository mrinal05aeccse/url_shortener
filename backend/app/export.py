"""
Export utilities for generating CSV downloads from URL data.
"""

import csv
import io
from typing import List, Dict, Any
from datetime import datetime
from .models import URL, ClickEvent


def generate_url_summary_csv(url: URL, click_events: List[ClickEvent]) -> str:
    """
    Generate CSV summary for a single shortened URL.
    
    Returns: CSV content as string
    """
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        'alias', 'target', 'created_at', 'expires_at', 
        'total_clicks', 'first_click', 'last_click', 'unique_ips'
    ])
    writer.writeheader()
    
    first_click = min((e.timestamp for e in click_events), default=None)
    last_click = max((e.timestamp for e in click_events), default=None)
    unique_ips = len(set(e.ip for e in click_events if e.ip))
    
    writer.writerow({
        'alias': url.alias,
        'target': url.target,
        'created_at': url.created_at.isoformat(),
        'expires_at': url.expires_at.isoformat() if url.expires_at else '',
        'total_clicks': url.clicks,
        'first_click': first_click.isoformat() if first_click else '',
        'last_click': last_click.isoformat() if last_click else '',
        'unique_ips': unique_ips
    })
    
    return output.getvalue()


def generate_daily_analytics_csv(url: URL, click_events: List[ClickEvent]) -> str:
    """
    Generate CSV with daily click breakdown.
    
    Returns: CSV content as string
    """
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        'date', 'clicks', 'unique_ips', 'top_country'
    ])
    writer.writeheader()
    
    # Group events by day
    daily_stats: Dict[str, Dict[str, Any]] = {}
    for event in click_events:
        day = event.timestamp.date().isoformat()
        if day not in daily_stats:
            daily_stats[day] = {
                'clicks': 0,
                'ips': set(),
                'countries': {}
            }
        daily_stats[day]['clicks'] += 1
        if event.ip:
            daily_stats[day]['ips'].add(event.ip)
        if event.country:
            daily_stats[day]['countries'][event.country] = \
                daily_stats[day]['countries'].get(event.country, 0) + 1
    
    # Write rows
    for day in sorted(daily_stats.keys()):
        stats = daily_stats[day]
        top_country = max(stats['countries'].items(), 
                         key=lambda x: x[1])[0] if stats['countries'] else 'XX'
        
        writer.writerow({
            'date': day,
            'clicks': stats['clicks'],
            'unique_ips': len(stats['ips']),
            'top_country': top_country
        })
    
    return output.getvalue()


def generate_events_csv(click_events: List[ClickEvent]) -> str:
    """
    Generate CSV with raw click event details.
    
    Returns: CSV content as string
    """
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        'timestamp', 'country', 'ip', 'user_agent'
    ])
    writer.writeheader()
    
    for event in sorted(click_events, key=lambda e: e.timestamp):
        writer.writerow({
            'timestamp': event.timestamp.isoformat(),
            'country': event.country or 'XX',
            'ip': event.ip or '',
            'user_agent': event.ua or ''
        })
    
    return output.getvalue()
