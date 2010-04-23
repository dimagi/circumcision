import datetime
import time

from rapidsms.contrib.handlers.app import App as handler_app
from rapidsms.models import Contact, Connection
from rapidsms.tests.scripted import TestScript
from rapidsms.contrib.locations.models import Location, LocationType

from mwana.apps.contactsplus.models import ContactType
from mwana.apps.reminders.app import App
from mwana.apps.reminders import models as reminders
from mwana.apps.reminders import tasks


class TestApp(TestScript):
    apps = (handler_app, App,)
    
    def _register(self):
        ctr = LocationType.objects.create()
        Location.objects.create(name="Kafue District Hospital", slug="kdh",
                                type=ctr)
        script = """
            kk     > agent kdh 01 rupiah banda
            kk     < Thank you rupiah banda! You have successfully registered at as a RemindMi Agent for Kafue District Hospital.
            """
        self.runScript(script)
    
    def testMalformedMessage(self):
        self._register()
        reminders.Event.objects.create(name="Birth", slug="birth")
        script = """
            kk     > birth
            kk     < Sorry, I didn't understand that. To add an event, send <EVENT CODE> <DATE> <NAME>.  The date is optional and is logged as TODAY if left out.
        """
        self.runScript(script)
        patients = Contact.objects.filter(types__slug='patient')
        self.assertEqual(0, patients.count())

    def testBadDate(self):
        self._register()
        reminders.Event.objects.create(name="Birth", slug="birth")
        script = """
            kk     > birth 34553 maria
            kk     < Sorry, I couldn't understand that date. Please enter the date like so: DAY MONTH YEAR, for example: 23 04 2010
        """
        self.runScript(script)
        patients = Contact.objects.filter(types__slug='patient')
        self.assertEqual(0, patients.count())

    def Test(self):
        self._register()
        reminders.Event.objects.create(name="Birth", slug="birth")
        script = """
            kk     > birth 4/3/2010 maria
            kk     < You have successfully registered a birth for maria on 04/03/2010. You will be notified when it is time for his or her next appointment at the clinic.
            kk     > birth 4 3 2010 laura
            kk     < You have successfully registered a birth for laura on 04/03/2010. You will be notified when it is time for his or her next appointment at the clinic.
            kk     > birth 4-3-2010 anna
            kk     < You have successfully registered a birth for anna on 04/03/2010. You will be notified when it is time for his or her next appointment at the clinic.
            kk     > birth 4/3 maria
            kk     < You have successfully registered a birth for maria on 04/03/%(year)s. You will be notified when it is time for his or her next appointment at the clinic.
            kk     > birth 4 3 laura
            kk     < You have successfully registered a birth for laura on 04/03/%(year)s. You will be notified when it is time for his or her next appointment at the clinic.
            kk     > birth 4-3 anna
            kk     < You have successfully registered a birth for anna on 04/03/%(year)s. You will be notified when it is time for his or her next appointment at the clinic.
        """ % {'year': datetime.datetime.now().year}
        self.runScript(script)
        patients = Contact.objects.filter(types__slug='patient')
        self.assertEqual(3, patients.count())
        for patient in patients:
            self.assertEqual(1, patient.patient_events.count())
            patient_event = patient.patient_events.get()
            self.assertEqual(patient_event.date, datetime.date(2010, 3, 4))
            self.assertEqual(patient_event.event.slug, "birth")

    def testCorrectMessageWithGender(self):
        self._register()
        reminders.Event.objects.create(name="Birth", slug="birth", gender='f')
        script = """
            kk     > birth 4/3/2010 maria
            kk     < You have successfully registered a birth for maria on 04/03/2010. You will be notified when it is time for her next appointment at the clinic.
        """
        self.runScript(script)
        patients = Contact.objects.filter(types__slug='patient')
        self.assertEqual(1, patients.count())
        
    def testCorrectMessageWithoutDate(self):
        self._register()
        reminders.Event.objects.create(name="Birth", slug="birth")
        script = """
            kk     > birth maria
            kk     < You have successfully registered a birth for maria on %s. You will be notified when it is time for his or her next appointment at the clinic.
        """ % datetime.date.today().strftime('%d/%m/%Y')
        self.runScript(script)
        patients = Contact.objects.filter(types__slug='patient')
        self.assertEqual(1, patients.count())
        patient = patients.get()
        self.assertEqual(1, patient.patient_events.count())
        patient_event = patient.patient_events.get()
        self.assertEqual(patient_event.date, datetime.date.today())
        self.assertEqual(patient_event.event.slug, "birth")
        
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
            rb     < Thank you rupiah banda! You have successfully registered at as a RemindMi Agent for Kafue District Hospital. Please notify us next time there is a birth in your zone.
            kk     > agent whoops 01 kenneth kaunda
            kk     < Sorry, I don't know about a location with code whoops. Please check your code and try again.
            noname > agent abc
            noname < Sorry, I didn't understand that. Make sure you send your clinic, zone #, and name like: AGENT <CLINIC CODE> <ZONE #> <YOUR NAME>
        """
        self.runScript(script)
        self.assertEqual(1, Contact.objects.count(), "Registration didn't create a new contact!")
        rb = Contact.objects.all()[0]
        self.assertEqual(rb.zone_code, 1)
        self.assertEqual("rupiah banda", rb.name, "Name was not set correctly after registration!")
        self.assertEqual(kdh, rb.location, "Location was not set correctly after registration!")
        self.assertEqual(rb.types.count(), 1)
        self.assertEqual(rb.types.all()[0].slug, 'cba')
        
    def testSendReminders(self):
        birth = reminders.Event.objects.create(name="Birth", slug="birth",
                                               gender="f")
        birth.appointments.create(name='2 day', num_days=2)
        birth.appointments.create(name='3 day', num_days=3)
        birth.appointments.create(name='4 day', num_days=4)
        clinic = LocationType.objects.create(singular='Clinic',
                                             plural='Clinics', slug='clinic')
        central = Location.objects.create(name='Central Clinic', type=clinic)
        patient1 = Contact.objects.create(name='patient 1', location=central)
        patient2 = Contact.objects.create(name='patient 2', location=central)
        patient3 = Contact.objects.create(name='patient 3', location=central)
        
        # this gets the backend and connection in the db
        self.runScript("""
        cba1 > hello world
        cba2 > hello world
        """)
        # take a break to allow the router thread to catch up; otherwise we
        # get some bogus messages when they're retrieved below
        time.sleep(.1)
        cba1_conn = Connection.objects.get(identity="cba1")
        cba1 = Contact.objects.create(name='cba1')
        cba1_conn.contact = cba1
        cba1_conn.save()
        cba2_conn = Connection.objects.get(identity="cba2")
        cba2 = Contact.objects.create(name='cba2')
        cba2_conn.contact = cba2
        cba2_conn.save()
        birth.patient_events.create(patient=patient1, cba_conn=cba1_conn,
                                    date=datetime.datetime.today())
        birth.patient_events.create(patient=patient2, cba_conn=cba1_conn,
                                    date=datetime.datetime.today())
        birth.patient_events.create(patient=patient3, cba_conn=cba2_conn,
                                    date=datetime.datetime.today())
        self.startRouter()
        tasks.send_notifications(self.router)
        # just the 1 and two day notifications should go out;
        # 3 patients x 2 notifications = 6 messages
        messages = self.receiveAllMessages()
        expected_messages =\
            ['Hello cba1. patient 1 is due for her next clinic appointment. '
             'Please deliver a reminder to this person and ensure she '
             'visits Central Clinic within 3 days.',
             'Hello cba1. patient 2 is due for her next clinic appointment. '
             'Please deliver a reminder to this person and ensure she '
             'visits Central Clinic within 3 days.',
             'Hello cba2. patient 3 is due for her next clinic appointment. '
             'Please deliver a reminder to this person and ensure she '
             'visits Central Clinic within 3 days.']
        self.assertEqual(len(messages), len(expected_messages))
        for msg in messages:
            self.assertTrue(msg.text in expected_messages, msg)
        sent_notifications = reminders.SentNotification.objects.all()
        self.assertEqual(sent_notifications.count(), len(expected_messages))
        
    def testRemindersSentOnlyOnce(self):
        """
        tests that notification messages are sent only sent once
        """
        birth = reminders.Event.objects.create(name="Birth", slug="birth")
        birth.appointments.create(name='1 day', num_days=2)
        patient1 = Contact.objects.create(name='patient 1')
        
        # this gets the backend and connection in the db
        self.runScript("""cba > hello world""")
        # take a break to allow the router thread to catch up; otherwise we
        # get some bogus messages when they're retrieved below
        time.sleep(.1)
        cba_conn = Connection.objects.get(identity="cba")
        birth.patient_events.create(patient=patient1, cba_conn=cba_conn,
                                    date=datetime.datetime.today())
        self.startRouter()
        tasks.send_notifications(self.router)
        # just the 1 and two day notifications should go out;
        # 3 patients x 2 notifications = 6 messages
        messages = self.receiveAllMessages()
        self.assertEqual(len(messages), 1)
        sent_notifications = reminders.SentNotification.objects.all()
        self.assertEqual(sent_notifications.count(), 1)

        # make sure no new messages go out if the method is called again
        tasks.send_notifications(self.router)
        messages = self.receiveAllMessages()
        self.assertEqual(len(messages), 0)
        sent_notifications = reminders.SentNotification.objects.all()
        # number of sent notifications should still be 1 (not 2)
        self.assertEqual(sent_notifications.count(), 1)
        
        self.stopRouter()
        
    def testRemindersNoLocation(self):
        birth = reminders.Event.objects.create(name="Birth", slug="birth")
        birth.appointments.create(name='1 day', num_days=2)
        patient1 = Contact.objects.create(name='patient 1')
        
        # this gets the backend and connection in the db
        self.runScript("""cba > hello world""")
        # take a break to allow the router thread to catch up; otherwise we
        # get some bogus messages when they're retrieved below
        time.sleep(.1)
        cba_conn = Connection.objects.get(identity="cba")
        birth.patient_events.create(patient=patient1, cba_conn=cba_conn,
                                    date=datetime.datetime.today())
        self.startRouter()
        tasks.send_notifications(self.router)
        # just the 1 and two day notifications should go out;
        # 3 patients x 2 notifications = 6 messages
        messages = self.receiveAllMessages()
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].text, "Hello. patient 1 is due for his "
                         "or her next clinic appointment. Please deliver a "
                         "reminder to this person and ensure he or she visits "
                         "the clinic within 3 days.")
        sent_notifications = reminders.SentNotification.objects.all()
        self.assertEqual(sent_notifications.count(), 1)
        
    def testRemindersRegistered(self):
        birth = reminders.Event.objects.create(name="Birth", slug="birth")
        birth.appointments.create(name='1 day', num_days=2)
        clinic = LocationType.objects.create(singular='Clinic',
                                             plural='Clinics', slug='clinic')
        central = Location.objects.create(name='Central Clinic', type=clinic)
        patient1 = Contact.objects.create(name='patient 1', zone_code=1,
                                          location=central)
        
        # this gets the backend and connection in the db
        self.runScript("""cba > hello world""")
        # take a break to allow the router thread to catch up; otherwise we
        # get some bogus messages when they're retrieved below
        time.sleep(.1)
        cba_conn = Connection.objects.get(identity="cba")
        cba = Contact.objects.create(name='cba', zone_code=1, location=central)
        cba_type = ContactType.objects.create(name='CBA', slug='cba')
        cba.types.add(cba_type)
        cba_conn.contact = cba
        cba_conn.save()
        birth.patient_events.create(patient=patient1, cba_conn=cba_conn,
                                    date=datetime.datetime.today())
        self.startRouter()
        tasks.send_notifications(self.router)
        # just the 1 and two day notifications should go out;
        # 3 patients x 2 notifications = 6 messages
        messages = self.receiveAllMessages()
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].text, "Hello cba. patient 1 is due for "
                         "his or her next clinic appointment. Please deliver a "
                         "reminder to this person and ensure he or she visits "
                         "Central Clinic within 3 days.")
        sent_notifications = reminders.SentNotification.objects.all()
        self.assertEqual(sent_notifications.count(), 1)
        
