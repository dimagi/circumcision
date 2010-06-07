# inherit everything from rapidsms, as default
# (this is optional. you can provide your own.)
from rapidsms.djangoproject.settings import *


# then add your django settings:
SEND_LIVE_LABRESULTS = True

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'circumcision.middleware.LoginRequired',
)

INSTALLED_APPS = [
    "django.contrib.sessions",
    "django.contrib.contenttypes",
    "django.contrib.auth",

    "rapidsms",
    "rapidsms.contrib.ajax", 
    "rapidsms.contrib.httptester", 
    "rapidsms.contrib.handlers", 
    "rapidsms.contrib.locations",
    "rapidsms.contrib.messagelog",
    "rapidsms.contrib.messaging",
    "rapidsms.contrib.scheduler",

    # enable the django admin using a little shim app (which includes
    # the required urlpatterns)
    "rapidsms.contrib.djangoadmin",
    "django.contrib.admin",
    
    "circumcision.apps.circumcision",
    "circumcision.apps.forwarder",
    
    "rapidsms.contrib.default",
]

# These apps should not be started by rapidsms in your tests
# However the models + bootstrap will still be available through
# django
TEST_EXCLUDED_APPS = (
    "django.contrib.sessions",
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "rapidsms",
    "rapidsms.contrib.ajax",
    "rapidsms.contrib.httptester",
    "rapidsms.contrib.scheduler",
)

ADMIN_MEDIA_PREFIX = '/admin-media/'

TIME_ZONE = "EST"

# TODO: make a better default response, include other apps, and maybe 
# this dynamic?
DEFAULT_RESPONSE = "Invalid Keyword. Valid keywords are JOIN, AGENT, CHECK, RESULT, SENT, ALL, CBA, BIRTH and CLINIC. Respond with any keyword or HELP for more information."

INSTALLED_BACKENDS = {
    "message_tester" : {"ENGINE": "rapidsms.backends.bucket" } 
}

TABS = [
    ('circumcision.apps.circumcision.views.patient_list', 'Dashboard'),
    ('rapidsms.contrib.httptester.views.generate_identity', 'Message Tester'),
    ('rapidsms.contrib.locations.views.dashboard', 'Map'),
    ('rapidsms.contrib.messagelog.views.message_log', 'Message Log'),
    ('rapidsms.contrib.messaging.views.messaging', 'Messaging'),
    ('rapidsms.contrib.scheduler.views.index', 'Event Scheduler'),

]


PROJECT_NAME = "RapidSMS - Circumcision"
PAGINATOR_OBJECTS_PER_PAGE = 20
PAGINATOR_MAX_PAGE_LINKS = 5

# Override the default log settings
LOG_LEVEL = "DEBUG"
LOG_FILE = "logs/rapidsms.route.log"
# DJANGO_LOG_FILE = "/var/log/rapidsms/rapidsms.django.log"
LOG_FORMAT = "[%(asctime)s] [%(name)s] [%(levelname)s]: %(message)s"
LOG_SIZE = 1000000 # in bytes
LOG_BACKUPS = 256     # number of logs to keep around
