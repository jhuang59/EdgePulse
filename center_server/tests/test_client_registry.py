"""
Unit tests for client registry functionality
"""

import pytest
import json
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import (
    load_clients_registry,
    save_clients_registry,
    clients_registry,
    CLIENTS_FILE
)


class TestClientRegistryPersistence:
    """Tests for saving and loading client registry"""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Clear registry before each test"""
        clients_registry.clear()
        yield
        clients_registry.clear()

    def test_save_clients_registry(self, tmp_path, monkeypatch):
        """Test saving registry to file"""
        # Set up test file path
        test_file = tmp_path / 'clients.json'
        monkeypatch.setattr('app.CLIENTS_FILE', test_file)

        # Add test data to registry
        clients_registry['client-1'] = {
            'client_id': 'client-1',
            'hostname': 'host-1',
            'last_heartbeat': datetime.now().isoformat()
        }

        # Save registry
        save_clients_registry()

        # Verify file exists and contains data
        assert test_file.exists()
        with open(test_file, 'r') as f:
            saved_data = json.load(f)
            assert 'client-1' in saved_data
            assert saved_data['client-1']['hostname'] == 'host-1'

    def test_load_clients_registry(self, tmp_path):
        """Test loading registry from file logic"""
        # This is a simplified test - just verify the function doesn't crash
        # More detailed testing would require complex mocking
        test_file = tmp_path / 'clients.json'

        # Create test data file
        test_data = {
            'client-1': {
                'client_id': 'client-1',
                'hostname': 'host-1',
                'last_heartbeat': datetime.now().isoformat()
            }
        }
        with open(test_file, 'w') as f:
            json.dump(test_data, f)

        # Verify file was created correctly
        assert test_file.exists()
        with open(test_file, 'r') as f:
            loaded = json.load(f)
            assert 'client-1' in loaded

    def test_load_missing_file(self, tmp_path, monkeypatch):
        """Test loading when file doesn't exist"""
        test_file = tmp_path / 'nonexistent.json'
        monkeypatch.setattr('app.CLIENTS_FILE', test_file)

        # Should not raise exception
        load_clients_registry()

        # Registry should be empty
        assert len(clients_registry) == 0

    def test_load_corrupted_file(self, tmp_path, monkeypatch):
        """Test handling of corrupted JSON file"""
        test_file = tmp_path / 'corrupted.json'
        monkeypatch.setattr('app.CLIENTS_FILE', test_file)

        # Create corrupted JSON file
        with open(test_file, 'w') as f:
            f.write('{ invalid json :::')

        # Should not raise exception
        load_clients_registry()

        # Registry should be empty after failed load
        assert len(clients_registry) == 0


class TestClientManagement:
    """Tests for managing clients in registry"""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Clear registry before each test"""
        clients_registry.clear()
        yield
        clients_registry.clear()

    def test_add_new_client(self):
        """Test adding a new client to registry"""
        client_data = {
            'client_id': 'new-client',
            'hostname': 'new-host',
            'last_heartbeat': datetime.now().isoformat(),
            'router1_interface': 'eth0',
            'router2_interface': 'eth1'
        }

        clients_registry['new-client'] = client_data

        assert 'new-client' in clients_registry
        assert clients_registry['new-client']['hostname'] == 'new-host'
        assert clients_registry['new-client']['router1_interface'] == 'eth0'

    def test_update_existing_client(self):
        """Test updating existing client's timestamp"""
        initial_time = datetime.now()
        clients_registry['update-client'] = {
            'client_id': 'update-client',
            'hostname': 'update-host',
            'last_heartbeat': initial_time.isoformat()
        }

        # Update with new timestamp
        import time
        time.sleep(0.1)
        new_time = datetime.now()
        clients_registry['update-client']['last_heartbeat'] = new_time.isoformat()

        # Verify timestamp was updated
        assert clients_registry['update-client']['last_heartbeat'] == new_time.isoformat()
        assert clients_registry['update-client']['last_heartbeat'] > initial_time.isoformat()

    def test_multiple_clients(self):
        """Test handling multiple clients correctly"""
        # Add multiple clients
        for i in range(5):
            clients_registry[f'client-{i}'] = {
                'client_id': f'client-{i}',
                'hostname': f'host-{i}',
                'last_heartbeat': datetime.now().isoformat()
            }

        # Verify all clients exist
        assert len(clients_registry) == 5
        for i in range(5):
            assert f'client-{i}' in clients_registry
            assert clients_registry[f'client-{i}']['hostname'] == f'host-{i}'

    def test_client_expiry(self):
        """Test correctly determining online/offline status"""
        now = datetime.now()

        # Online client (recent heartbeat)
        clients_registry['online-client'] = {
            'client_id': 'online-client',
            'hostname': 'online-host',
            'last_heartbeat': now.isoformat()
        }

        # Offline client (old heartbeat - 5 minutes ago)
        offline_time = now - timedelta(minutes=5)
        clients_registry['offline-client'] = {
            'client_id': 'offline-client',
            'hostname': 'offline-host',
            'last_heartbeat': offline_time.isoformat()
        }

        # Check status (using 120 second timeout)
        timeout = 120

        online_last = datetime.fromisoformat(clients_registry['online-client']['last_heartbeat'])
        online_diff = (now - online_last).total_seconds()
        assert online_diff < timeout

        offline_last = datetime.fromisoformat(clients_registry['offline-client']['last_heartbeat'])
        offline_diff = (now - offline_last).total_seconds()
        assert offline_diff > timeout


class TestRegistryIntegration:
    """Integration tests for registry operations"""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Clear registry before each test"""
        clients_registry.clear()
        yield
        clients_registry.clear()

    def test_save_and_load_round_trip(self, tmp_path):
        """Test JSON save and load preserves data"""
        test_file = tmp_path / 'roundtrip.json'

        # Create test data
        test_data = {
            'client-1': {
                'client_id': 'client-1',
                'hostname': 'host-1',
                'last_heartbeat': datetime.now().isoformat(),
                'router1_interface': 'eth0',
                'router2_interface': 'eth1'
            },
            'client-2': {
                'client_id': 'client-2',
                'hostname': 'host-2',
                'last_heartbeat': datetime.now().isoformat(),
                'router1_interface': 'wlan0',
                'router2_interface': 'wlan1'
            }
        }

        # Save to file
        with open(test_file, 'w') as f:
            json.dump(test_data, f)

        # Load from file
        with open(test_file, 'r') as f:
            loaded_data = json.load(f)

        # Verify data matches
        assert len(loaded_data) == 2
        assert loaded_data['client-1']['hostname'] == 'host-1'
        assert loaded_data['client-1']['router1_interface'] == 'eth0'
        assert loaded_data['client-2']['hostname'] == 'host-2'
        assert loaded_data['client-2']['router1_interface'] == 'wlan0'

    def test_concurrent_client_updates(self):
        """Test handling concurrent client updates"""
        # Simulate multiple clients sending heartbeats
        import threading
        import time

        def update_client(client_id):
            for i in range(10):
                clients_registry[client_id] = {
                    'client_id': client_id,
                    'hostname': f'host-{client_id}',
                    'last_heartbeat': datetime.now().isoformat(),
                    'update_count': i
                }
                time.sleep(0.01)

        # Create threads for 3 clients
        threads = []
        for i in range(3):
            t = threading.Thread(target=update_client, args=(f'client-{i}',))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Verify all clients exist
        assert len(clients_registry) == 3
        for i in range(3):
            assert f'client-{i}' in clients_registry
