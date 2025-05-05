from extras.plugins import PluginConfig

class RAVPNConfig(PluginConfig):
    name = "ra_vpn"
    verbose_name = "RA VPN"
    description = "VPN Group/User management"
    version = "0.1"

default_app_config = "ra_vpn.RAVPNConfig"
