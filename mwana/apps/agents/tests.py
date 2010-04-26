from rapidsms.contrib.handlers.app import App as handler_app
from rapidsms.models import Contact
from rapidsms.tests.scripted import TestScript
from rapidsms.contrib.locations.models import Location, LocationType

from mwana.apps.reminders.app import App
from mwana.apps.reminders import models as reminders


class TestApp(TestScript):
    apps = (handler_app, App,)
    
    def testAgentRegistration(self):
        self.assertEqual(0, Contact.objects.count())
        ctr = LocationType.objects.create()
        kdh = Location.objects.create(name="Kafue District Hospital",
                                      slug="kdh", type=ctr)
        reminders.Event.objects.create(name="Birth", slug="birth")
        self.assertEqual(reminders.Event.objects.count(), 1)
        script = """
            lost   > agent
            lost   < To register as a RemindMi agent, send AGENT <CLINIC CODE> <ZONE #> <YOUR NAME>
            rb     > agent kdh 01 rupiah banda
            rb     < Thank you Rupiah Banda! You have successfully registered as a RemindMi Agent for Kafue District Hospital. Please notify us next time there is a birth in your zone.
            rb     > agent kdh 01 rupiah banda
            rb     < Hello Rupiah Banda! You are already registered as a RemindMi Agent for Kafue District Hospital. 
            kk     > agent whoops 01 kenneth kaunda
            kk     < Sorry, I don't know about a location with code whoops. Please check your code and try again.
            noname > agent abc
            noname < Sorry, I didn't understand that. Make sure you send your clinic, zone #, and name like: AGENT <CLINIC CODE> <ZONE #> <YOUR NAME>
        """
        self.runScript(script)
        self.assertEqual(1, Contact.objects.count(), "Registration didn't create a new contact!")
        rb = Contact.objects.all()[0]
        self.assertEqual(rb.zone_code, 1)
        self.assertEqual("Rupiah Banda", rb.name, "Name was not set correctly after registration!")
        self.assertEqual(kdh, rb.location, "Location was not set correctly after registration!")
        self.assertEqual(rb.types.count(), 1)
        self.assertEqual(rb.types.all()[0].slug, 'cba')