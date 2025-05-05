from django.template.loaders.filesystem import Loader as FilesystemLoader
from django.template.loaders.app_directories import Loader as AppLoader

class PluginLoader(FilesystemLoader):
    def get_dirs(self):
        # Add NetBox's template directory
        dirs = super().get_dirs()
        dirs.append('/opt/netbox/netbox/templates')
        return dirs
