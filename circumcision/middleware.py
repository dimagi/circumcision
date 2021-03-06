import logging

from django.conf import settings

from django.contrib.auth.decorators import login_required


class LogExceptions(object):
    """
    Simple middleware to log Django exceptions through Python's standard
    logging module.
    """
    
    def process_exception(self, request, exception):
        logger = logging.getLogger('circumcision.middleware.LogExceptions')
        logger.exception(exception)


class LoginRequired(object):
    """
    Makes login required for all views except those that start with the matched
    URLs.
    """
    
    urls = ['/admin/', '/accounts/login/', '/accounts/logout/', settings.MEDIA_URL,
            '/circumcision/diagnostics/']
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        for url in self.urls:
            if request.get_full_path().startswith(url):
                return # allow normal processing to continue
        return login_required(view_func)(request, *view_args, **view_kwargs)
