#!/usr/bin/env python3
"""
Generate demo GPS coverage data for EdgePulse visualization.

Simulates two mobile Jetson hosts (jetbot-01, jetbot-02) moving along
routes with varying connection quality and disconnect events.

Usage:
    # Write directly to file (fastest):
    python3 generate_demo_data.py --mode file

    # Post via API (works with any deployment):
    python3 generate_demo_data.py --mode api --url http://localhost:5000

    # Post via API using center_server_url from config.json:
    python3 generate_demo_data.py --mode api
"""

import json
import math
import random
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Demo Route Definitions
# ---------------------------------------------------------------------------
# Route coordinates simulate two robots doing survey runs in an outdoor area.
# Based loosely on an open field / campus environment.
# Each waypoint: (lat, lon, avg_ms_r1, avg_ms_r2, r1_connected, r2_connected)

JETBOT_01_ROUTE = [
    # Start — good connection, low latency
    (35.6812, 139.7671, 12.3, 18.4, True,  True),   # Start point
    (35.6815, 139.7675, 14.1, 20.2, True,  True),
    (35.6818, 139.7680, 11.8, 17.9, True,  True),
    (35.6821, 139.7685, 15.6, 22.1, True,  True),
    # Entering degraded zone — latency rises
    (35.6824, 139.7690, 58.2, 72.4, True,  True),
    (35.6826, 139.7694, 89.1, 95.3, True,  True),
    (35.6828, 139.7698, 112.4, 130.7, True, True),
    # DISCONNECT EVENT — signal lost
    (35.6830, 139.7702, None, None, False, False),
    (35.6831, 139.7705, None, None, False, False),
    # Signal recovered
    (35.6832, 139.7708, 145.2, 162.1, True, True),
    (35.6830, 139.7712, 88.4,  95.7,  True, True),
    (35.6828, 139.7716, 45.1,  52.3,  True, True),
    # Route continues back — improving signal
    (35.6825, 139.7720, 22.8, 30.1, True, True),
    (35.6822, 139.7718, 18.3, 25.6, True, True),
    (35.6819, 139.7714, 13.7, 19.2, True, True),
    (35.6816, 139.7710, 11.1, 16.8, True, True),
    # End point
    (35.6813, 139.7706, 10.5, 15.3, True, True),
]

JETBOT_02_ROUTE = [
    # Start — good connection
    (35.6802, 139.7690, 16.4, 14.2, True, True),
    (35.6800, 139.7696, 18.7, 16.8, True, True),
    (35.6798, 139.7702, 21.3, 19.4, True, True),
    (35.6796, 139.7708, 24.6, 22.7, True, True),
    (35.6794, 139.7714, 27.8, 26.1, True, True),
    # One router struggles (R2 up, R1 weak)
    (35.6792, 139.7720, 78.3, 24.3, True, True),
    (35.6790, 139.7726, 112.5, 21.8, True, True),
    # DISCONNECT EVENT for R1, R2 still ok
    (35.6788, 139.7730, None, 19.4, False, True),
    (35.6786, 139.7733, None, 18.1, False, True),
    # Turning back
    (35.6785, 139.7736, 44.2, 17.3, True,  True),
    (35.6787, 139.7731, 28.6, 16.4, True,  True),
    (35.6789, 139.7725, 19.3, 15.7, True,  True),
    (35.6791, 139.7719, 15.6, 14.9, True,  True),
    (35.6793, 139.7713, 13.2, 13.8, True,  True),
    # End — strong signal
    (35.6795, 139.7707, 11.8, 13.1, True,  True),
]


def make_point(client_id: str, ts: datetime, lat: float, lon: float,
               avg_ms_r1, avg_ms_r2, r1_connected: bool, r2_connected: bool,
               source: str = 'ros') -> dict:
    """Build a coverage_data.jsonl record."""

    # Add small random jitter to make it look like real GPS readings
    lat += random.uniform(-0.00003, 0.00003)
    lon += random.uniform(-0.00003, 0.00003)

    # Add noise to latency
    def jitter(v):
        if v is None:
            return None
        return round(max(1.0, v + random.uniform(-v * 0.1, v * 0.1)), 1)

    loss_r1 = None if avg_ms_r1 is None else round(
        random.uniform(0, 3.0) if r1_connected else 100.0, 1)
    loss_r2 = None if avg_ms_r2 is None else round(
        random.uniform(0, 3.0) if r2_connected else 100.0, 1)

    return {
        'timestamp': ts.isoformat(),
        'client_id': client_id,
        'lat': round(lat, 7),
        'lon': round(lon, 7),
        'altitude': round(random.uniform(40, 55), 1),
        'speed': round(random.uniform(0.5, 2.5), 1),
        'source': source,
        'from_heartbeat': False,
        'avg_ms_r1': jitter(avg_ms_r1),
        'avg_ms_r2': jitter(avg_ms_r2),
        'loss_r1': loss_r1,
        'loss_r2': loss_r2,
        'r1_connected': r1_connected,
        'r2_connected': r2_connected,
    }


def generate_all_points(hours_ago: float = 2.0) -> list:
    """Generate all demo coverage points for both hosts."""
    points = []
    now = datetime.now()

    # jetbot-01: ran a survey about 2 hours ago
    start_01 = now - timedelta(hours=hours_ago)
    interval_01 = timedelta(minutes=6)  # ~6 min between points
    for i, waypoint in enumerate(JETBOT_01_ROUTE):
        lat, lon, r1ms, r2ms, r1_ok, r2_ok = waypoint
        ts = start_01 + interval_01 * i
        points.append(make_point('jetbot-01', ts, lat, lon, r1ms, r2ms, r1_ok, r2_ok, source='ros'))

    # jetbot-02: started 30 min later
    start_02 = now - timedelta(hours=hours_ago - 0.5)
    interval_02 = timedelta(minutes=7)
    for i, waypoint in enumerate(JETBOT_02_ROUTE):
        lat, lon, r1ms, r2ms, r1_ok, r2_ok = waypoint
        ts = start_02 + interval_02 * i
        points.append(make_point('jetbot-02', ts, lat, lon, r1ms, r2ms, r1_ok, r2_ok, source='sim7600'))

    return points


def write_to_file(points: list, output_path: str):
    """Write points directly to coverage_data.jsonl."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'a') as f:
        for pt in points:
            f.write(json.dumps(pt) + '\n')

    print(f"[Demo] Wrote {len(points)} points to {path}")


def post_via_api(points: list, center_url: str):
    """Post points via /api/logs endpoint (triggers coverage extraction server-side)."""
    import urllib.request
    import urllib.error

    success = 0
    errors = 0
    for pt in points:
        # Build a fake benchmark payload that includes location
        # The server extracts location from it and writes to coverage_data.jsonl
        payload = {
            'timestamp': pt['timestamp'],
            'client_id': pt['client_id'],
            'hostname': pt['client_id'],
            'location': {
                'lat': pt['lat'],
                'lon': pt['lon'],
                'altitude': pt['altitude'],
                'speed': pt['speed'],
                'source': pt['source'],
                'fix': True,
            },
            'router1': {
                'avg_ms': pt['avg_ms_r1'],
                'packet_loss_pct': pt['loss_r1'],
                'success': pt['r1_connected'],
                'router': 'Router 1',
                'interface': 'eth0',
                'gateway': '192.168.1.1',
                'min_ms': None,
                'max_ms': None,
                'median_ms': None,
                'stdev_ms': None,
            },
            'router2': {
                'avg_ms': pt['avg_ms_r2'],
                'packet_loss_pct': pt['loss_r2'],
                'success': pt['r2_connected'],
                'router': 'Router 2',
                'interface': 'wlan0',
                'gateway': '192.168.30.1',
                'min_ms': None,
                'max_ms': None,
                'median_ms': None,
                'stdev_ms': None,
            },
        }
        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                f"{center_url.rstrip('/')}/api/logs",
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    success += 1
                else:
                    errors += 1
        except Exception as e:
            print(f"  Warning: failed to post point: {e}")
            errors += 1

    print(f"[Demo] Posted {success} points successfully, {errors} errors")


def main():
    parser = argparse.ArgumentParser(description='Generate EdgePulse demo coverage data')
    parser.add_argument('--mode', choices=['file', 'api'], default='file',
                        help='Write directly to file or post via API (default: file)')
    parser.add_argument('--url', default='',
                        help='Center server URL for API mode (e.g. http://localhost:5000)')
    parser.add_argument('--output', default='',
                        help='Output file path for file mode (default: auto-detect)')
    parser.add_argument('--hours-ago', type=float, default=2.0,
                        help='Start time for demo data in hours ago (default: 2.0)')
    args = parser.parse_args()

    random.seed(42)  # Reproducible jitter

    print(f"[Demo] Generating GPS coverage data for jetbot-01 and jetbot-02...")
    points = generate_all_points(hours_ago=args.hours_ago)
    print(f"[Demo] Generated {len(points)} points "
          f"({len(JETBOT_01_ROUTE)} for jetbot-01, {len(JETBOT_02_ROUTE)} for jetbot-02)")

    if args.mode == 'file':
        # Determine output path
        if args.output:
            output_path = args.output
        else:
            # Try to auto-detect based on common locations
            candidates = [
                'center_server/data/coverage_data.jsonl',  # Host path (docker-compose volume)
                '/app/data/coverage_data.jsonl',            # Inside container
                'data/coverage_data.jsonl',                 # Relative fallback
            ]
            output_path = candidates[0]
            print(f"[Demo] Auto-selected output: {output_path}")
            print(f"[Demo] Override with --output <path> if needed")

        write_to_file(points, output_path)

    else:
        # API mode — read URL from config.json if not provided
        url = args.url
        if not url:
            try:
                with open('config.json') as f:
                    cfg = json.load(f)
                url = cfg.get('center_server_url', '')
                print(f"[Demo] Using center_server_url from config.json: {url}")
            except Exception:
                pass
        if not url:
            print("Error: provide --url or set center_server_url in config.json")
            sys.exit(1)

        print(f"[Demo] Posting to {url}/api/logs ...")
        post_via_api(points, url)

    print(f"[Demo] Done. Open the Coverage Map tab and click Refresh to see the data.")


if __name__ == '__main__':
    main()
