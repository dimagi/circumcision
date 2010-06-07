'''
Created on Mar 31, 2010

@author: Drew Roos
'''

import rapidsms
from circumcision.apps.circumcision.models import Registration, SentNotif
import circumcision.apps.circumcision.config as config
from rapidsms.contrib.scheduler.models import EventSchedule
from datetime import datetime, timedelta, time
import pytz
from rapidsms.contrib.messaging.utils import send_message
from circumcision.apps.circumcision.text import get_text, get_notification,\
    split_contact_time


class App (rapidsms.App):

    def start (self):
        """Configure your app in the start phase."""
        self.verify_config()

    def parse (self, message):
        """Parse and annotate messages in the parse phase."""
        pass

    def cleanup (self, message):
        """Perform any clean up after all handlers have run in the
           cleanup phase."""
        pass

    def outgoing (self, message):
        """Handle outgoing message notifications."""
        pass

    def stop (self):
        """Perform global app cleanup when the application is stopped."""
        pass
        
    def verify_config (self):
        """perform some basic validation for the config, namely that notifications for all days are
        defined in all languages"""
        if config.default_language not in config.itext:
            raise ValueError('default language [%s] not defined' % config.default_language)
        
        for lang in config.itext.keys():
            for day in config.notification_days:
                try:
                    get_notification(day, lang)
                except ValueError:
                    raise ValueError('no notification set for day %d in language [%s]' % (day, lang))
        

