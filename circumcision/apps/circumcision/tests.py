from rapidsms.tests.scripted import TestScript
from circumcision.apps.circumcision.models import Registration
from rapidsms.contrib.locations.models import Location, LocationType

class TestApp (TestScript):
    
    testHelp = """
        someperson > mc
        someperson < To register, send message as: register [patient id] [desired contact time (HHMM)]
    """
    
    testRegistrationLanguages = """
        someperson > mc register 11 1234 1800 EN
        someperson < You have been registered. You will receive your notifications at 18:00
        some_swahili_person > mc register 11 1235 1800 sw
        some_swahili_person < [sw] You have been registered. You will receive your notifications at 18:00
        some_luo_person > mc register 11 1236 1800 luo
        some_luo_person < [luo] You have been registered. You will receive your notifications at 18:00
    """
        
        
    def setUp(self):
        super(TestApp, self).setUp()
        type = LocationType.objects.create(singular="test", plural="tests", slug="tests")
        self.location = Location.objects.create(name="Test Site", slug="11", type=type)
    
    def tearDown(self):
        super(TestApp, self).tearDown()
        # because these get created in a separate thread we have to delete them 
        # by hand
        # Registration.objects.all().delete()
        
    
    def testBasicRegistration(self):
        text = """
            someperson > mc register 11 1234 1800 EN
            someperson < You have been registered. You will receive your notifications at 18:00
        """
        self.assertEqual(0, Registration.objects.count())
        self.runScript(text)
        self.assertEqual(1, Registration.objects.count())
        reg = Registration.objects.all()[0]
        self.assertEqual("1234", reg.patient_id)
        self.assertEqual(self.location, reg.location)
        self.assertEqual("en", reg.language)
        # contact time is stored as minutes since midnightx 
        # for some strange reason
        self.assertEqual(18 * 60, reg.contact_time) 