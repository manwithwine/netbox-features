import paramiko
import hashlib
import time

def get_device_config(ip, username, password, vendor):
    commands = {
        'huawei': ['screen-length 0 temporary', 'display current-configuration'],
        'mellanox': ['en', 'terminal length 999', 'show run'],
        'default': ['terminal length 0', 'show run']
    }

    vendor_key = 'huawei' if 'hua' in vendor.lower() else 'mellanox' if 'mellanox' in vendor.lower() else 'default'
    cmd_set = commands[vendor_key]

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ip, username=username, password=password, look_for_keys=False, allow_agent=False)

    shell = client.invoke_shell()
    time.sleep(1)
    shell.recv(1000)

    output = ""
    for cmd in cmd_set:
        shell.send(cmd + "\n")
        time.sleep(2)
        output += shell.recv(99999).decode(errors='ignore')

    client.close()

    config = output.split(cmd_set[-1])[-1]
    config_hash = hashlib.sha256(config.encode()).hexdigest()

    return config.strip(), config_hash
