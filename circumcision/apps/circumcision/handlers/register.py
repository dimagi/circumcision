#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4


from circumcision.apps.circumcision import config
from circumcision.apps.circumcision.text import get_text, split_contact_time
from rapidsms.contrib.handlers import KeywordHandler
from rapidsms.models import Contact
from circumcision.apps.circumcision.models import Registration
from circumcision.apps.circumcision.schedule import schedule_notifications
from rapidsms.contrib.locations.models import Location


class RegisterHandler(KeywordHandler):
    """
    """

    keyword = "mc"

    def help(self):
        self.respond(get_text('reg-help', config.default_language))

    def handle(self, text):
        try:
            (location, patient_id, contact_time, lang) = self.parse_message(text)
        except ValueError, response:
            self.respond(str(response))
            return True
        connection = self.msg.connection
        
        reg = Registration(patient_id=patient_id, contact_time=contact_time, 
                           connection=connection, location=location, 
                           language=lang)
                           
        reg.save()
        
        schedule_notifications(reg, self.msg.date)
        
        self.respond(get_text('reg-success', lang) % ('%02d:%02d' % split_contact_time(contact_time)))
        return True

    def parse_message (self, text):
        """parse the sms message, either raising a variety of exceptions, or returning patient id,
        contact time as integer minutes since midnight, and language code to use for future notifications"""
        pieces = text.split()
        
        #discriminate language based on 'register' keyword?
        if len(pieces) != 5 or pieces[0] != get_text('reg-keyword', config.default_language):
            raise ValueError(get_text('cannot-parse', config.default_language))
        site_id = pieces[1]
        patient_id = pieces[2]
        contact_time_str = pieces[3]
        lang = pieces[4]
        
        validated_language = self.get_validated_language(lang) 
        if not validated_language:
            raise ValueError(get_text('language-unrecognized', config.default_language))
        else:
            lang = validated_language
        
        location = self.get_validated_site(site_id)
        if not location:
            raise ValueError(get_text('site-unrecognized', lang))
        
        if not self.validate_patient_id_format(patient_id):
            raise ValueError(get_text('patid-unrecognized', lang))
        
        #check if patient has already been registered
        try:
            reg = Registration.objects.get(patient_id=patient_id)
            patid_already_registered = True
        except Registration.DoesNotExist:
            patid_already_registered = False
        
        #check if phone number has already been registered
        try:
            Registration.objects.get(connection=self.msg.connection)
            phone_already_registered = True
        except Registration.DoesNotExist:
            phone_already_registered = False
    
        #todo: change behavior if existing registration is completed/expired
        if patid_already_registered:
            if phone_already_registered:
                raise ValueError(get_text('already-registered', lang) % reg.registered_on.strftime('%d-%m-%Y'))
            else:
                raise ValueError(get_text('patid-already-registered', lang))
        elif phone_already_registered:
            raise ValueError(get_text('phone-already-registered', lang))
        
        contact_time = self.parse_contact_time(contact_time_str)
        if contact_time == None:
            raise ValueError(get_text('cannot-parse-time', lang))
        
        
        return (location, patient_id, contact_time, lang)

    def get_validated_language(self, language):
        """validate and normalize the language, returning a reference to
           the cleaned string, or None if not found."""
        #todo: should do better cleanup of param
        if language.lower() in config.itext:
            return language.lower()
        
    def get_validated_site(self, site_id):
        """validate and normalize the site id, returning a reference to
           the location object, or None if not found."""
        #todo: should do better cleanup of param
        try:
            return Location.objects.get(slug=site_id)
        except Location.DoesNotExist:
            return None
        
    #todo: should normalize patient id here too, if applicable
    def validate_patient_id_format(self, patient_id):
        """validate and normalize the patient id"""
        return True
        
    def parse_contact_time (self, contact_time_str):
        """parse the contact time and return a normalized value of minutes since midnight"""
        if len(contact_time_str) != 4:
            return None
        
        try:
            hour = int(contact_time_str[0:2])
            minute = int(contact_time_str[2:4])
        except ValueError:
            return None
        
        if hour < 0 or hour >= 24 or minute < 0 or minute >= 60:
            return None
        
        return hour * 60 + minute
    
    