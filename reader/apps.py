from django.apps import AppConfig


class ReaderConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reader'
    verbose_name = "ReadSite"
    def ready(self):
        import reader.signals
