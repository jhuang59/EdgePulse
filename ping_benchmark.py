#!/usr/bin/env python3
"""
Router Ping Benchmark Tool
Pings internet through two different routers and summarizes performance
Includes remote command execution and web shell for remote terminal access
"""

import subprocess
import json
import time
import statistics
from datetime import datetime, timedelta
import os
import re
import urllib.request
import urllib.error
import threading
import socket
import pty
import select
import struct
import fcntl
import termios
import signal

# Try to import socketio for web shell
try:
    import socketio
    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    print("Warning: python-socketio not installed, web shell disabled")

class PingBenchmark:
    def __init__(self, config_file='config.json'):
        with open(config_file, 'r') as f:
            self.config = json.load(f)
        
        self.router1_gw = self.config['router1']['gateway']
        self.router1_iface = self.config['router1']['interface']
        self.router2_gw = self.config['router2']['gateway']
        self.router2_iface = self.config['router2']['interface']
        self.ping_target = self.config.get('ping_target', '8.8.8.8')
        self.ping_count = self.config.get('ping_count', 20)
        self.test_interval = self.config.get('test_interval_seconds', 300)
        self.results_dir = self.config.get('results_dir', '/app/results')
        self.center_server_url = self.config.get('center_server_url', '')
        self.heartbeat_interval = self.config.get('heartbeat_interval_seconds', 60)
        # Use hostname if client_id is empty or not specified
        self.client_id = self.config.get('client_id') or socket.gethostname()

        # Authentication settings
        self.secret_key = self.config.get('secret_key', '')
        self.command_poll_interval = self.config.get('command_poll_interval_seconds', 10)
        self.command_enabled = self.config.get('remote_commands_enabled', True)

        # Heartbeat thread control
        self.heartbeat_running = False
        self.heartbeat_thread = None

        # Command polling thread control
        self.command_polling_running = False
        self.command_polling_thread = None

        # Web shell settings
        self.shell_enabled = self.config.get('web_shell_enabled', True)
        self.shell_connected = False
        self.sio = None
        self.shell_sessions = {}  # session_id -> {'fd': master_fd, 'pid': pid}

        # Geolocation settings
        geo_config = self.config.get('geolocation', {})
        geo_source = geo_config.get('source', 'disabled')
        if geo_source and geo_source != 'disabled':
            try:
                from geolocation import GeolocationReader
                self.geo = GeolocationReader(geo_config)
            except ImportError as e:
                print(f"Warning: Could not import geolocation module: {e}")
                self.geo = None
        else:
            self.geo = None

        # Create results directory
        os.makedirs(self.results_dir, exist_ok=True)

    def get_location_payload(self):
        """
        Get current GPS location for inclusion in payloads.
        Returns dict with location data or None if unavailable.
        """
        if not self.geo:
            return None
        try:
            return self.geo.get_location()
        except Exception as e:
            print(f"Warning: Error getting location: {e}")
            return None

    def ping_through_router(self, gateway, interface, name):
        """
        Ping through a specific router using source interface
        Returns dict with latency statistics and packet loss
        """
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Testing {name}...")
        print(f"  Gateway: {gateway}, Interface: {interface}")
        
        cmd = [
            'ping',
            '-I', interface,
            '-c', str(self.ping_count),
            '-W', '2',  # 2 second timeout
            self.ping_target
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.ping_count * 3
            )
            
            output = result.stdout
            
            # Parse packet loss
            loss_match = re.search(r'(\d+)% packet loss', output)
            packet_loss = float(loss_match.group(1)) if loss_match else 100.0
            
            # Parse latency stats
            latencies = []
            for line in output.split('\n'):
                if 'time=' in line:
                    time_match = re.search(r'time=([\d.]+)', line)
                    if time_match:
                        latencies.append(float(time_match.group(1)))
            
            stats = {
                'timestamp': datetime.now().isoformat(),
                'router': name,
                'gateway': gateway,
                'interface': interface,
                'target': self.ping_target,
                'packet_loss_pct': packet_loss,
                'packets_sent': self.ping_count,
                'packets_received': len(latencies),
                'success': packet_loss < 100
            }
            
            if latencies:
                stats.update({
                    'min_ms': min(latencies),
                    'max_ms': max(latencies),
                    'avg_ms': statistics.mean(latencies),
                    'median_ms': statistics.median(latencies),
                    'stdev_ms': statistics.stdev(latencies) if len(latencies) > 1 else 0
                })
            else:
                stats.update({
                    'min_ms': None,
                    'max_ms': None,
                    'avg_ms': None,
                    'median_ms': None,
                    'stdev_ms': None
                })
            
            return stats
            
        except subprocess.TimeoutExpired:
            print(f"  ERROR: Ping timeout for {name}")
            return {
                'timestamp': datetime.now().isoformat(),
                'router': name,
                'gateway': gateway,
                'interface': interface,
                'target': self.ping_target,
                'packet_loss_pct': 100.0,
                'packets_sent': self.ping_count,
                'packets_received': 0,
                'success': False,
                'error': 'timeout'
            }
        except Exception as e:
            print(f"  ERROR: {str(e)}")
            return {
                'timestamp': datetime.now().isoformat(),
                'router': name,
                'gateway': gateway,
                'interface': interface,
                'target': self.ping_target,
                'success': False,
                'error': str(e)
            }
    
    def run_benchmark(self):
        """Run ping benchmark on both routers"""
        print(f"\n{'='*60}")
        print(f"Starting Ping Benchmark - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        # Test both routers
        router1_result = self.ping_through_router(
            self.router1_gw, 
            self.router1_iface, 
            'Router 1'
        )
        
        router2_result = self.ping_through_router(
            self.router2_gw, 
            self.router2_iface, 
            'Router 2'
        )
        
        # Combine results
        benchmark_result = {
            'timestamp': datetime.now().isoformat(),
            'client_id': self.client_id,
            'hostname': socket.gethostname(),
            'router1': router1_result,
            'router2': router2_result,
            'location': self.get_location_payload()
        }
        
        # Print summary
        self.print_summary(benchmark_result)

        # Save results
        self.save_results(benchmark_result)

        # Send to center server
        self.send_to_center_server(benchmark_result)

        return benchmark_result
    
    def print_summary(self, result):
        """Print formatted summary of benchmark results"""
        print(f"\n{'='*60}")
        print("BENCHMARK SUMMARY")
        print(f"{'='*60}")
        
        for router_key in ['router1', 'router2']:
            r = result[router_key]
            print(f"\n{r['router']}:")
            print(f"  Interface: {r['interface']}")
            print(f"  Gateway: {r['gateway']}")
            print(f"  Packet Loss: {r['packet_loss_pct']:.1f}%")
            
            if r['success'] and r.get('avg_ms') is not None:
                print(f"  Latency:")
                print(f"    Min:    {r['min_ms']:.2f} ms")
                print(f"    Avg:    {r['avg_ms']:.2f} ms")
                print(f"    Median: {r['median_ms']:.2f} ms")
                print(f"    Max:    {r['max_ms']:.2f} ms")
                print(f"    StdDev: {r['stdev_ms']:.2f} ms")
            else:
                print(f"  Status: FAILED - {r.get('error', 'No response')}")
        
        # Compare routers
        print(f"\n{'='*60}")
        print("COMPARISON:")
        print(f"{'='*60}")
        
        r1 = result['router1']
        r2 = result['router2']
        
        if r1['success'] and r2['success']:
            if r1.get('avg_ms') and r2.get('avg_ms'):
                diff = r1['avg_ms'] - r2['avg_ms']
                if abs(diff) < 1:
                    print("Both routers have similar performance")
                elif diff < 0:
                    print(f"Router 1 is FASTER by {abs(diff):.2f} ms average")
                else:
                    print(f"Router 2 is FASTER by {diff:.2f} ms average")
            
            loss_diff = r1['packet_loss_pct'] - r2['packet_loss_pct']
            if loss_diff > 0:
                print(f"Router 2 has BETTER packet loss by {loss_diff:.1f}%")
            elif loss_diff < 0:
                print(f"Router 1 has BETTER packet loss by {abs(loss_diff):.1f}%")
        else:
            if not r1['success']:
                print("Router 1: FAILED")
            if not r2['success']:
                print("Router 2: FAILED")
        
        print(f"{'='*60}\n")
    
    def save_results(self, result):
        """Save results to JSON file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{self.results_dir}/benchmark_{timestamp}.json"

        with open(filename, 'w') as f:
            json.dump(result, f, indent=2)

        print(f"Results saved to: {filename}")

        # Also append to a cumulative log
        log_file = f"{self.results_dir}/benchmark_log.jsonl"
        with open(log_file, 'a') as f:
            f.write(json.dumps(result) + '\n')

    def send_to_center_server(self, result):
        """Send results to center server"""
        if not self.center_server_url:
            return

        try:
            url = f"{self.center_server_url}/api/logs"
            data = json.dumps(result).encode('utf-8')

            req = urllib.request.Request(
                url,
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    print(f"Successfully sent data to center server: {url}")
                else:
                    print(f"Warning: Center server returned status {response.status}")

        except urllib.error.URLError as e:
            print(f"Warning: Failed to send data to center server: {e}")
        except Exception as e:
            print(f"Warning: Error sending to center server: {e}")

    def send_heartbeat(self):
        """Send heartbeat signal to center server"""
        if not self.center_server_url:
            return

        try:
            url = f"{self.center_server_url}/api/heartbeat"
            heartbeat_data = {
                'client_id': self.client_id,
                'hostname': socket.gethostname(),
                'router1_interface': self.router1_iface,
                'router2_interface': self.router2_iface,
                'location': self.get_location_payload(),
            }
            data = json.dumps(heartbeat_data).encode('utf-8')

            req = urllib.request.Request(
                url,
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )

            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Heartbeat sent to center server")

        except Exception as e:
            print(f"Warning: Heartbeat failed: {e}")

    def heartbeat_worker(self):
        """Background worker that sends periodic heartbeats"""
        print(f"Heartbeat worker started (interval: {self.heartbeat_interval}s)")

        while self.heartbeat_running:
            self.send_heartbeat()
            time.sleep(self.heartbeat_interval)

    def start_heartbeat(self):
        """Start the heartbeat background thread"""
        if not self.center_server_url:
            print("No center server configured, heartbeat disabled")
            return

        if self.heartbeat_running:
            return

        self.heartbeat_running = True
        self.heartbeat_thread = threading.Thread(target=self.heartbeat_worker, daemon=True)
        self.heartbeat_thread.start()
        print(f"Heartbeat started for client: {self.client_id}")

    def stop_heartbeat(self):
        """Stop the heartbeat background thread"""
        if self.heartbeat_running:
            self.heartbeat_running = False
            if self.heartbeat_thread:
                self.heartbeat_thread.join(timeout=2)

    # =========================================================================
    # Remote Command Execution (simplified auth - API key only)
    # =========================================================================

    def execute_command(self, command_data):
        """
        Execute a verified command and return the result
        """
        command_string = command_data.get('command_string', '')
        timeout = command_data.get('timeout', 60)
        command_uuid = command_data.get('command_uuid', '')
        command_id = command_data.get('command_id', '')

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Executing command: {command_id}")
        print(f"  Command: {command_string}")

        start_time = time.time()

        try:
            result = subprocess.run(
                command_string,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            duration = time.time() - start_time

            return {
                'command_uuid': command_uuid,
                'command_id': command_id,
                'exit_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'executed_at': datetime.now().isoformat(),
                'duration_seconds': round(duration, 3)
            }

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return {
                'command_uuid': command_uuid,
                'command_id': command_id,
                'exit_code': -1,
                'stdout': '',
                'stderr': f'Command timed out after {timeout} seconds',
                'executed_at': datetime.now().isoformat(),
                'duration_seconds': round(duration, 3),
                'error': 'timeout'
            }

        except Exception as e:
            duration = time.time() - start_time
            return {
                'command_uuid': command_uuid,
                'command_id': command_id,
                'exit_code': -1,
                'stdout': '',
                'stderr': str(e),
                'executed_at': datetime.now().isoformat(),
                'duration_seconds': round(duration, 3),
                'error': str(e)
            }

    def submit_command_result(self, result):
        """Submit command execution result to center server"""
        if not self.center_server_url:
            return

        try:
            url = f"{self.center_server_url}/api/commands/result"
            data = json.dumps(result).encode('utf-8')

            req = urllib.request.Request(
                url,
                data=data,
                headers={
                    'Content-Type': 'application/json',
                    'X-Client-ID': self.client_id,
                    'X-Client-API-Key': self.secret_key
                },
                method='POST'
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Command result submitted")
                else:
                    print(f"Warning: Failed to submit result, status {response.status}")

        except Exception as e:
            print(f"Warning: Failed to submit command result: {e}")

    def poll_for_commands(self):
        """Poll the center server for pending commands"""
        if not self.center_server_url or not self.secret_key:
            return None

        try:
            url = f"{self.center_server_url}/api/commands/poll"

            req = urllib.request.Request(
                url,
                headers={
                    'X-Client-ID': self.client_id,
                    'X-Client-API-Key': self.secret_key
                },
                method='GET'
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    if data.get('has_command'):
                        return data.get('command')
                return None

        except urllib.error.HTTPError as e:
            if e.code == 401:
                print(f"Warning: Authentication failed - check secret_key configuration")
            return None
        except Exception as e:
            # Silently fail - server might be temporarily unavailable
            return None

    def command_polling_worker(self):
        """Background worker that polls for and executes commands"""
        print(f"Command polling worker started (interval: {self.command_poll_interval}s)")

        while self.command_polling_running:
            try:
                # Poll for command
                command = self.poll_for_commands()

                if command:
                    # Execute the command (simplified auth - no signature verification)
                    result = self.execute_command(command)

                    # Submit result
                    self.submit_command_result(result)

                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Command completed: exit_code={result['exit_code']}")

            except Exception as e:
                print(f"Warning: Error in command polling: {e}")

            time.sleep(self.command_poll_interval)

    def start_command_polling(self):
        """Start the command polling background thread"""
        if not self.center_server_url:
            print("No center server configured, command polling disabled")
            return

        if not self.secret_key:
            print("No secret key configured, command polling disabled")
            return

        if not self.command_enabled:
            print("Remote commands disabled in config")
            return

        if self.command_polling_running:
            return

        self.command_polling_running = True
        self.command_polling_thread = threading.Thread(
            target=self.command_polling_worker,
            daemon=True
        )
        self.command_polling_thread.start()
        print(f"Command polling started for client: {self.client_id}")

    def stop_command_polling(self):
        """Stop the command polling background thread"""
        if self.command_polling_running:
            self.command_polling_running = False
            if self.command_polling_thread:
                self.command_polling_thread.join(timeout=2)

    # =========================================================================
    # Web Shell (via WebSocket)
    # =========================================================================

    def start_shell_client(self):
        """Start the WebSocket shell client"""
        if not SOCKETIO_AVAILABLE:
            print("Web shell disabled: python-socketio not installed")
            return

        if not self.center_server_url:
            print("Web shell disabled: no center server configured")
            return

        if not self.secret_key:
            print("Web shell disabled: no secret key configured")
            return

        if not self.shell_enabled:
            print("Web shell disabled in config")
            return

        # Create Socket.IO client
        self.sio = socketio.Client(reconnection=True, reconnection_attempts=0)

        # Set up event handlers
        @self.sio.event
        def connect():
            print(f"[WebSocket] Connected to server for shell")
            self.shell_connected = True
            # Register for shell capability
            self.sio.emit('shell_register_client', {
                'client_id': self.client_id,
                'api_key': self.secret_key
            })

        @self.sio.event
        def disconnect():
            print(f"[WebSocket] Disconnected from server")
            self.shell_connected = False
            # Close all shell sessions
            for session_id in list(self.shell_sessions.keys()):
                self._close_shell_session(session_id)

        @self.sio.on('shell_registered')
        def on_shell_registered(data):
            print(f"[WebSocket] Shell registered: {data.get('client_id')}")

        @self.sio.on('shell_error')
        def on_shell_error(data):
            print(f"[WebSocket] Shell error: {data.get('error')}")

        @self.sio.on('shell_open')
        def on_shell_open(data):
            session_id = data.get('session_id')
            rows = data.get('rows', 24)
            cols = data.get('cols', 80)
            print(f"[WebSocket] Shell open request: {session_id[:8]}...")
            self._open_shell_session(session_id, rows, cols)

        @self.sio.on('shell_input')
        def on_shell_input(data):
            session_id = data.get('session_id')
            input_data = data.get('input', '')
            self._handle_shell_input(session_id, input_data)

        @self.sio.on('shell_resize')
        def on_shell_resize(data):
            session_id = data.get('session_id')
            rows = data.get('rows', 24)
            cols = data.get('cols', 80)
            self._resize_shell(session_id, rows, cols)

        @self.sio.on('shell_close')
        def on_shell_close(data):
            session_id = data.get('session_id')
            print(f"[WebSocket] Shell close request: {session_id[:8]}...")
            self._close_shell_session(session_id)

        # Connect to server
        try:
            # Convert http:// to ws:// for WebSocket
            ws_url = self.center_server_url.replace('http://', 'ws://').replace('https://', 'wss://')
            # But socketio client uses http/https
            self.sio.connect(self.center_server_url, transports=['websocket'])
            print(f"[WebSocket] Shell client started")
        except Exception as e:
            print(f"[WebSocket] Failed to connect: {e}")
            self.sio = None

    def stop_shell_client(self):
        """Stop the WebSocket shell client"""
        if self.sio:
            try:
                # Close all shell sessions
                for session_id in list(self.shell_sessions.keys()):
                    self._close_shell_session(session_id)
                self.sio.disconnect()
            except Exception as e:
                print(f"[WebSocket] Error disconnecting: {e}")
            self.sio = None
            self.shell_connected = False

    def _open_shell_session(self, session_id, rows, cols):
        """Open a new shell session"""
        try:
            # Fork a PTY
            pid, fd = pty.fork()

            if pid == 0:
                # Child process - exec shell
                env = os.environ.copy()
                env['TERM'] = 'xterm-256color'
                env['COLUMNS'] = str(cols)
                env['LINES'] = str(rows)

                # Try to get the user's shell, fallback to /bin/bash
                shell = os.environ.get('SHELL', '/bin/bash')
                if not os.path.exists(shell):
                    shell = '/bin/bash'
                if not os.path.exists(shell):
                    shell = '/bin/sh'

                os.execvpe(shell, [shell, '-l'], env)
            else:
                # Parent process
                # Set non-blocking
                flags = fcntl.fcntl(fd, fcntl.F_GETFL)
                fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

                # Set terminal size
                self._set_pty_size(fd, rows, cols)

                # Store session info
                self.shell_sessions[session_id] = {
                    'fd': fd,
                    'pid': pid,
                    'rows': rows,
                    'cols': cols
                }

                # Notify server that shell is ready
                self.sio.emit('shell_ready', {
                    'session_id': session_id,
                    'client_id': self.client_id
                })

                # Start reading thread for this session
                read_thread = threading.Thread(
                    target=self._shell_read_worker,
                    args=(session_id,),
                    daemon=True
                )
                read_thread.start()

                print(f"[Shell] Session started: {session_id[:8]}... (pid={pid})")

        except Exception as e:
            print(f"[Shell] Failed to open session: {e}")
            self.sio.emit('shell_client_exit', {
                'session_id': session_id,
                'exit_code': -1
            })

    def _shell_read_worker(self, session_id):
        """Background thread to read from shell and send output"""
        session = self.shell_sessions.get(session_id)
        if not session:
            return

        fd = session['fd']
        pid = session['pid']

        try:
            while session_id in self.shell_sessions:
                # Check if process is still alive
                try:
                    wpid, status = os.waitpid(pid, os.WNOHANG)
                    if wpid != 0:
                        # Process exited
                        exit_code = os.WEXITSTATUS(status) if os.WIFEXITED(status) else -1
                        print(f"[Shell] Process exited: {session_id[:8]}... (code={exit_code})")
                        if self.sio and self.shell_connected:
                            self.sio.emit('shell_client_exit', {
                                'session_id': session_id,
                                'exit_code': exit_code
                            })
                        self._close_shell_session(session_id)
                        return
                except ChildProcessError:
                    # Process already reaped
                    self._close_shell_session(session_id)
                    return

                # Read from PTY
                try:
                    ready, _, _ = select.select([fd], [], [], 0.1)
                    if ready:
                        data = os.read(fd, 4096)
                        if data:
                            if self.sio and self.shell_connected:
                                # Send as base64 to handle binary data
                                import base64
                                self.sio.emit('shell_output', {
                                    'session_id': session_id,
                                    'output': base64.b64encode(data).decode('ascii')
                                })
                except OSError:
                    # FD closed
                    break

        except Exception as e:
            print(f"[Shell] Read worker error: {e}")
        finally:
            self._close_shell_session(session_id)

    def _handle_shell_input(self, session_id, input_data):
        """Handle input from admin, write to shell"""
        session = self.shell_sessions.get(session_id)
        if not session:
            return

        try:
            # Decode from base64
            import base64
            data = base64.b64decode(input_data)
            os.write(session['fd'], data)
        except Exception as e:
            print(f"[Shell] Write error: {e}")

    def _resize_shell(self, session_id, rows, cols):
        """Resize the shell terminal"""
        session = self.shell_sessions.get(session_id)
        if not session:
            return

        session['rows'] = rows
        session['cols'] = cols
        self._set_pty_size(session['fd'], rows, cols)

    def _set_pty_size(self, fd, rows, cols):
        """Set PTY window size"""
        try:
            winsize = struct.pack('HHHH', rows, cols, 0, 0)
            fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)
        except Exception as e:
            print(f"[Shell] Failed to set PTY size: {e}")

    def _close_shell_session(self, session_id):
        """Close a shell session"""
        session = self.shell_sessions.pop(session_id, None)
        if not session:
            return

        try:
            # Close FD
            os.close(session['fd'])
        except:
            pass

        try:
            # Kill process
            os.kill(session['pid'], signal.SIGTERM)
            # Give it a moment, then force kill
            time.sleep(0.1)
            try:
                os.kill(session['pid'], signal.SIGKILL)
            except:
                pass
            # Reap the process
            try:
                os.waitpid(session['pid'], os.WNOHANG)
            except:
                pass
        except:
            pass

        print(f"[Shell] Session closed: {session_id[:8]}...")

    def run_continuous(self):
        """Run benchmark continuously at specified interval"""
        print(f"Starting continuous benchmarking...")
        print(f"Client ID: {self.client_id}")
        print(f"Test interval: {self.test_interval} seconds")
        if self.center_server_url:
            print(f"Heartbeat interval: {self.heartbeat_interval} seconds")
        if self.secret_key and self.command_enabled:
            print(f"Remote commands: ENABLED (poll interval: {self.command_poll_interval}s)")
        else:
            print(f"Remote commands: DISABLED")
        if self.secret_key and self.shell_enabled and SOCKETIO_AVAILABLE:
            print(f"Web shell: ENABLED")
        else:
            print(f"Web shell: DISABLED")
        print(f"Press Ctrl+C to stop\n")

        # Start heartbeat in background
        self.start_heartbeat()

        # Start command polling in background
        self.start_command_polling()

        # Start shell client in background
        shell_thread = threading.Thread(target=self.start_shell_client, daemon=True)
        shell_thread.start()

        try:
            while True:
                self.run_benchmark()
                print(f"\nNext test in {self.test_interval} seconds...")
                time.sleep(self.test_interval)
        except KeyboardInterrupt:
            print("\n\nBenchmarking stopped by user")
            self.stop_shell_client()
            self.stop_command_polling()
            self.stop_heartbeat()

if __name__ == '__main__':
    benchmark = PingBenchmark()
    benchmark.run_continuous()
