import paramiko
import time
import logging
import re
import socket
from datetime import datetime

logger = logging.getLogger(__name__)

def get_device_primary_ip(device):
    if device.primary_ip:
        return str(device.primary_ip.address.ip)
    if device.oob_ip:
        return str(device.oob_ip.address.ip)
    return None

def wait_for_prompt(chan, prompt_regex=r"[>#]\s*$", timeout=30):
    buffer = ""
    end_time = time.time() + timeout

    while time.time() < end_time:
        if chan.recv_ready():
            chunk = chan.recv(4096).decode('utf-8', errors='ignore')
            buffer += chunk
            # Check if last non-empty line matches prompt pattern
            lines = [line for line in buffer.split('\n') if line.strip()]
            if lines and re.search(prompt_regex, lines[-1]):
                break
        time.sleep(0.2)
    return buffer

def clean_config(config, vendor):
    """Remove unwanted characters and clean up config output"""
    # Remove ANSI escape sequences (for Mellanox/Depo)
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    config = ansi_escape.sub('', config)

    # Remove NUL bytes
    config = config.replace('\x00', '')

    lines = config.split('\n')
    clean_lines = []

    # Vendor rules
    for i, line in enumerate(lines):
        line = line.rstrip('\r\n')
        stripped = line.strip()
        if not stripped:
            # For Cisco/cisco-like: Add "!" for blank lines
            if 'cisco' in vendor:
                clean_lines.append('!')
            continue

        if 'huawei' in vendor:
            # Usual skip for commands/echoes, if needed (can expand)
            if any(stripped.startswith(prefix) for prefix in ['display', 'screen-length', '<']):
                continue

        elif 'mellanox' in vendor or 'depo' in vendor:
            if stripped.startswith('## Generated') or stripped.startswith('show running-config'):
                continue

        # Cisco/cisco-like ignore lines
        if 'cisco' in vendor:
            # Remove lines starting with ! Last configuration change* or !Time:*
            if stripped.startswith('! Last configuration change') or stripped.startswith('!Time:'):
                continue
            # Usual skip for commands/echoes, if needed (can expand)
            if any(stripped.startswith(prefix) for prefix in ['show', 'terminal', 'Building configuration', 'Current configuration']):
                continue

        clean_lines.append(stripped)

    # For other vendors, just join clean lines
    return '\n'.join(clean_lines)

def backup_device_config(device, username, password):
    ip = get_device_primary_ip(device)
    if not ip:
        return None, "No IP address configured for device"

    try:
        logger.info(f"🔌 Attempting SSH to {ip} as {username}")

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=username, password=password, timeout=15)

        vendor = device.device_type.manufacturer.name.lower()
        logger.info(f"📡 Detected vendor: {vendor}")

        chan = ssh.invoke_shell()
        time.sleep(2)  # Wait for shell to initialize
        initial_output = wait_for_prompt(chan)  # Clear initial banner

        if 'huawei' in vendor:
            chan.send('screen-length 0 temporary\n')
            time.sleep(1)
            wait_for_prompt(chan)

            chan.send('display current-configuration\n')
            config = ""
            start_time = time.time()
            while time.time() - start_time < 120:
                if chan.recv_ready():
                    chunk = chan.recv(65535).decode('utf-8', errors='ignore')
                    config += chunk
                    if re.search(r'<.*>', config.split('\n')[-1]):
                        break
                else:
                    time.sleep(0.5)

        elif 'mellanox' in vendor or 'depo' in vendor:
            chan.send('enable\n')
            wait_for_prompt(chan)
            chan.send('terminal length 999\n')
            wait_for_prompt(chan)
            chan.send('show running-config\n')
            config = wait_for_prompt(chan, timeout=120)

        else:  # Cisco and similar
            chan.send('terminal length 0\n')
            wait_for_prompt(chan)
            chan.send('show running-config\n')
            config = wait_for_prompt(chan, timeout=120)

        ssh.close()
        return clean_config(config, vendor), "Success"

    except socket.timeout:
        logger.error("⌛ Connection timed out")
        return None, "Connection timed out"
    except Exception as e:
        logger.error(f"❌ SSH failed: {str(e)}")
        return None, f"Connection failed: {str(e)}"
