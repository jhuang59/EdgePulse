#!/usr/bin/env python3
from __future__ import annotations
"""
GPS Geolocation Provider for EdgePulse Router Benchmark

Supports two GPS sources:
1. ROS - reads from a ROS topic (sensor_msgs/NavSatFix) running in a Docker container
2. SIM7600 - reads from a SIM7600G-H 4G/GNSS module via AT commands over serial

Configure via config.json:
{
  "geolocation": {
    "source": "ros",  // or "sim7600" or "disabled"
    "ros": {
      "container_name": "ros_container",
      "topic": "/gps/fix"
    },
    "sim7600": {
      "serial_port": "/dev/ttyUSB2",
      "baud_rate": 115200,
      "auto_enable": true  // automatically enable GPS on startup
    }
  }
}
"""

import subprocess
import re
import threading
import time
from datetime import datetime
from typing import Optional

# Cache settings
GPS_CACHE_TTL_SECONDS = 5  # Return cached location if less than 5 seconds old
GPS_UPDATE_INTERVAL = 3    # Background thread update interval


class GeolocationReader:
    """
    GPS location provider supporting multiple sources.

    Usage:
        geo = GeolocationReader(config['geolocation'])
        location = geo.get_location()
        # Returns dict or None
    """

    def __init__(self, config: dict):
        """
        Initialize the geolocation reader.

        Args:
            config: The 'geolocation' block from config.json
        """
        self.config = config
        self.source = config.get('source', 'disabled')

        # ROS configuration
        self.ros_container = config.get('ros', {}).get('container_name', 'ros_container')
        self.ros_topic = config.get('ros', {}).get('topic', '/gps/fix')

        # SIM7600 configuration
        self.sim_port = config.get('sim7600', {}).get('serial_port', '/dev/ttyUSB2')
        self.sim_baud = config.get('sim7600', {}).get('baud_rate', 115200)
        self.sim_auto_enable = config.get('sim7600', {}).get('auto_enable', True)

        # Cached location (non-blocking reads)
        self._cached_location: Optional[dict] = None
        self._cache_timestamp: float = 0
        self._cache_lock = threading.Lock()

        # Background update thread
        self._running = False
        self._update_thread: Optional[threading.Thread] = None

        print(f"[Geolocation] Initialized with source: {self.source}")
        if self.source == 'ros':
            print(f"[Geolocation] ROS container: {self.ros_container}, topic: {self.ros_topic}")
        elif self.source == 'sim7600':
            print(f"[Geolocation] SIM7600 port: {self.sim_port}, baud: {self.sim_baud}")
            # Auto-enable GPS if configured
            if self.sim_auto_enable:
                self._enable_sim7600_gps()

    def start_background_updates(self):
        """Start background thread for non-blocking GPS updates."""
        if self._running:
            return
        self._running = True
        self._update_thread = threading.Thread(target=self._background_worker, daemon=True)
        self._update_thread.start()
        print("[Geolocation] Background update thread started")

    def stop_background_updates(self):
        """Stop the background update thread."""
        self._running = False
        if self._update_thread:
            self._update_thread.join(timeout=2)
            self._update_thread = None

    def _background_worker(self):
        """Background worker that periodically updates GPS cache."""
        while self._running:
            try:
                location = self._read_location_blocking()
                with self._cache_lock:
                    self._cached_location = location
                    self._cache_timestamp = time.time()
            except Exception as e:
                print(f"[Geolocation] Background update error: {e}")
            time.sleep(GPS_UPDATE_INTERVAL)

    def _read_location_blocking(self) -> dict | None:
        """Internal blocking read (used by background thread)."""
        if self.source == 'ros':
            return self._read_ros()
        elif self.source == 'sim7600':
            return self._read_sim7600()
        else:
            return None

    def get_location(self) -> dict | None:
        """
        Get current GPS location (non-blocking if background thread is running).

        If background updates are running, returns cached location immediately.
        Otherwise, performs a blocking read.

        Returns:
            dict with keys: lat, lon, altitude, speed, source, fix
            None if no valid fix or on error
        """
        # If background thread is running, return cached value
        if self._running:
            with self._cache_lock:
                # Return cache if fresh enough
                if self._cached_location and (time.time() - self._cache_timestamp) < GPS_CACHE_TTL_SECONDS:
                    return self._cached_location.copy()
                # Cache is stale but return it anyway (non-blocking behavior)
                if self._cached_location:
                    return self._cached_location.copy()
                return None

        # No background thread - fall back to blocking read
        return self._read_location_blocking()

    def _enable_sim7600_gps(self):
        """Enable GPS on SIM7600 module (AT+CGPS=1)."""
        try:
            import serial
        except ImportError:
            print("[Geolocation] SIM7600: pyserial not installed, skipping auto-enable")
            return

        try:
            with serial.Serial(self.sim_port, self.sim_baud, timeout=3) as ser:
                ser.reset_input_buffer()

                # First check if GPS is already enabled
                ser.write(b'AT+CGPS?\r\n')
                time.sleep(0.5)
                response = ser.read(256).decode('utf-8', errors='ignore')

                if '+CGPS: 1' in response:
                    print("[Geolocation] SIM7600: GPS already enabled")
                    return

                # Enable GPS
                ser.write(b'AT+CGPS=1\r\n')
                time.sleep(1)
                response = ser.read(256).decode('utf-8', errors='ignore')

                if 'OK' in response:
                    print("[Geolocation] SIM7600: GPS enabled successfully")
                elif 'ERROR' in response:
                    print("[Geolocation] SIM7600: Failed to enable GPS")
                else:
                    print(f"[Geolocation] SIM7600: Unexpected response: {response.strip()}")

        except Exception as e:
            print(f"[Geolocation] SIM7600: Error enabling GPS: {e}")

    def _read_ros(self) -> dict | None:
        """
        Read GPS from ROS topic inside a Docker container.

        Uses: docker exec <container> rostopic echo -n 1 <topic>

        Expected output format (sensor_msgs/NavSatFix):
            header:
              seq: 123
              stamp:
                secs: 1234567890
                nsecs: 0
              frame_id: "gps"
            status:
              status: 0
              service: 1
            latitude: 37.7749295
            longitude: -122.4194155
            altitude: 10.5
            ...
        """
        try:
            result = subprocess.run(
                ['docker', 'exec', self.ros_container,
                 'rostopic', 'echo', '-n', '1', self.ros_topic],
                capture_output=True,
                text=True,
                timeout=15
            )

            if result.returncode != 0:
                print(f"[Geolocation] ROS command failed: {result.stderr.strip()}")
                return None

            stdout = result.stdout

            # Parse YAML-like output with regex
            lat_match = re.search(r'latitude:\s*([-\d.]+)', stdout)
            lon_match = re.search(r'longitude:\s*([-\d.]+)', stdout)
            alt_match = re.search(r'altitude:\s*([-\d.]+)', stdout)

            if not lat_match or not lon_match:
                print(f"[Geolocation] ROS: Could not parse lat/lon from output")
                return None

            lat = float(lat_match.group(1))
            lon = float(lon_match.group(1))
            alt = float(alt_match.group(1)) if alt_match else 0.0

            # Validate coordinates
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                print(f"[Geolocation] ROS: Invalid coordinates: lat={lat}, lon={lon}")
                return None

            # Check for null island (0,0) which usually indicates no fix
            if abs(lat) < 0.001 and abs(lon) < 0.001:
                print(f"[Geolocation] ROS: Coordinates at null island, likely no fix")
                return None

            return {
                'lat': round(lat, 7),
                'lon': round(lon, 7),
                'altitude': round(alt, 1),
                'speed': 0.0,  # ROS NavSatFix doesn't include speed
                'source': 'ros',
                'fix': True
            }

        except subprocess.TimeoutExpired:
            print(f"[Geolocation] ROS: Timeout waiting for topic {self.ros_topic}")
            return None
        except Exception as e:
            print(f"[Geolocation] ROS error: {e}")
            return None

    def _read_sim7600(self) -> dict | None:
        """
        Read GPS from SIM7600G-H module via AT command.

        Uses AT+CGPSINFO command.
        Response format:
            +CGPSINFO: 3743.9467,N,12224.5581,W,130521,210832.0,88.8,0.0,0

        Fields:
            0: Latitude in DDMMmm.mmmm format
            1: N/S indicator
            2: Longitude in DDDMMmm.mmmm format
            3: E/W indicator
            4: Date (DDMMYY)
            5: Time (HHMMSS.S)
            6: Altitude in meters
            7: Speed over ground in km/h
            8: Course over ground in degrees

        Empty response "+CGPSINFO: ,,,,,,,," means no GPS fix.
        """
        try:
            import serial
        except ImportError:
            print("[Geolocation] SIM7600: pyserial not installed. Install with: pip install pyserial")
            return None

        try:
            with serial.Serial(self.sim_port, self.sim_baud, timeout=5) as ser:
                # Clear any pending data
                ser.reset_input_buffer()

                # Send AT command
                ser.write(b'AT+CGPSINFO\r\n')

                # Read response
                response = b''
                while True:
                    chunk = ser.read(256)
                    if not chunk:
                        break
                    response += chunk
                    if b'OK' in response or b'ERROR' in response:
                        break

                response_str = response.decode('utf-8', errors='ignore')

            # Check for error
            if 'ERROR' in response_str:
                print(f"[Geolocation] SIM7600: AT command error")
                return None

            # Parse +CGPSINFO response
            # Pattern: +CGPSINFO: lat,N/S,lon,E/W,date,time,alt,speed,course
            match = re.search(
                r'\+CGPSINFO:\s*([\d.]+),(N|S),([\d.]+),(E|W),(\d+),([\d.]+),([-\d.]*),([\d.]*),([\d.]*)',
                response_str
            )

            if not match:
                # Check if it's an empty response (no fix)
                if '+CGPSINFO: ,,,,,,,,' in response_str or '+CGPSINFO:' in response_str:
                    print(f"[Geolocation] SIM7600: No GPS fix")
                else:
                    print(f"[Geolocation] SIM7600: Could not parse response")
                return None

            lat_ddmm = match.group(1)
            lat_dir = match.group(2)
            lon_ddmm = match.group(3)
            lon_dir = match.group(4)
            alt_str = match.group(7)
            speed_str = match.group(8)

            # Convert DDMMmm.mmmm to decimal degrees
            lat = self._ddmm_to_decimal(lat_ddmm, lat_dir)
            lon = self._ddmm_to_decimal(lon_ddmm, lon_dir)

            # Parse altitude and speed
            alt = float(alt_str) if alt_str else 0.0
            speed = float(speed_str) if speed_str else 0.0

            # Validate coordinates
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                print(f"[Geolocation] SIM7600: Invalid coordinates: lat={lat}, lon={lon}")
                return None

            return {
                'lat': round(lat, 7),
                'lon': round(lon, 7),
                'altitude': round(alt, 1),
                'speed': round(speed, 1),  # km/h
                'source': 'sim7600',
                'fix': True
            }

        except serial.SerialException as e:
            print(f"[Geolocation] SIM7600: Serial error: {e}")
            return None
        except Exception as e:
            print(f"[Geolocation] SIM7600 error: {e}")
            return None

    def _ddmm_to_decimal(self, ddmm_str: str, direction: str) -> float:
        """
        Convert DDMMmm.mmmm format to decimal degrees.

        Args:
            ddmm_str: Coordinate in DDMM.mmmm or DDDMM.mmmm format
            direction: 'N', 'S', 'E', or 'W'

        Returns:
            Decimal degrees (negative for S/W)

        Example:
            3743.9467, N -> 37.732445
            12224.5581, W -> -122.409302
        """
        ddmm = float(ddmm_str)
        degrees = int(ddmm / 100)
        minutes = ddmm - (degrees * 100)
        decimal = degrees + (minutes / 60.0)

        if direction in ('S', 'W'):
            decimal = -decimal

        return decimal


# For testing
if __name__ == '__main__':
    import json

    # Test with ROS config
    test_config = {
        'source': 'ros',
        'ros': {
            'container_name': 'ros_test',
            'topic': '/gps/fix'
        },
        'sim7600': {
            'serial_port': '/dev/ttyUSB2',
            'baud_rate': 115200
        }
    }

    geo = GeolocationReader(test_config)
    print("\nTesting get_location():")
    result = geo.get_location()
    if result:
        print(f"Location: {json.dumps(result, indent=2)}")
    else:
        print("No location available")

    # Test DDMM conversion
    print("\nTesting DDMM conversion:")
    print(f"  3743.9467, N -> {geo._ddmm_to_decimal('3743.9467', 'N')}")
    print(f"  12224.5581, W -> {geo._ddmm_to_decimal('12224.5581', 'W')}")
