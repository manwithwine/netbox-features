from netbox.plugins import PluginMenu, PluginMenuItem

menu = PluginMenu(
    label='RA-VPN',
    groups=(
        ('RA-VPN', (
            PluginMenuItem(
                link='plugins:ra_vpn:vpngroup_list',
                link_text='Groups',
            ),
            PluginMenuItem(
                link='plugins:ra_vpn:vpnuser_list',
                link_text='Users',
            ),
        )),
    ),
    icon_class='mdi mdi-vpn',
)
