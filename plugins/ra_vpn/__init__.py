try:
    from netbox.plugins import PluginConfig
except ModuleNotFoundError:
    # Allow local CLI and scripts to import this module without NetBox
    class PluginConfig:
        pass

class RA_VPNConfig(PluginConfig):
    name = 'ra_vpn'
    verbose_name = 'RA VPN'
    description = 'Remote Access VPN Management'
    version = '2.4'
    author = 'Mansur Kasumov'
    author_email = 'mkmklsfml@gmail.com'
    base_url = 'ra_vpn'
    required_settings = []
    default_settings = {
        'templates_path': 'ra_vpn/templates',
    }
    permissions = (
        ('add_vpngroup', "Can add VPN group"),
        ('change_vpngroup', "Can change VPN group"),
        ('delete_vpngroup', "Can delete VPN group"),
        ('add_vpnuser', "Can add VPN user"),
        ('change_vpnuser', "Can change VPN user"),
    )
    api_urls = 'ra_vpn.api.urls'

config = RA_VPNConfig
# plugins/ra_vpn/__init__.py
default_app_config = 'plugins.ra_vpn.apps.RaVpnAppConfig'
