import sys
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        import core.signals  # noqa: F401

        # Prevent execution during management commands like migrate/collectstatic
        non_server_cmds = {'migrate', 'makemigrations', 'collectstatic', 'check', 'createsuperuser', 'shell', 'test'}
        if not any(arg in non_server_cmds for arg in sys.argv):
            from .keepalive import start_keepalive
            start_keepalive()

