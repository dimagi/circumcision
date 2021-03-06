'''
Created on Mar 31, 2010

@author: Drew Roos
'''

from django.db import models
from rapidsms.models import Connection
from rapidsms.contrib.locations.models import Location

class Registration(models.Model):
    patient_id = models.CharField(max_length=20, primary_key=True)
    contact_time = models.IntegerField(blank=True, null=True)
    connection = models.ForeignKey(Connection, unique=True, blank=True, null=True)
    location = models.ForeignKey(Location)
    registered_on = models.DateField(auto_now_add=True)
    language = models.CharField(max_length=20, default="en")
    
    followup_visit = models.BooleanField(default=False)
    final_visit = models.BooleanField(default=False)
    
    def __unicode__ (self):
        return 'registration: %s %d %s %s %s' % (self.patient_id, self.contact_time,
            str(self.connection), str(self.registered_on), self.language)
        
class SentNotif(models.Model):
    patient_id = models.ForeignKey(Registration)
    day = models.IntegerField()
