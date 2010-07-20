#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4

import re
from circumcision.apps.circumcision import config
from rapidsms.contrib.handlers import KeywordHandler
from circumcision.apps.circumcision.text import get_text, split_contact_time
from circumcision.apps.circumcision.models import Registration
from circumcision.apps.circumcision.schedule import schedule_notifications
from rapidsms.contrib.locations.models import Location
from rapidsms.contrib.messaging.utils import send_message
from rapidsms.models import Connection

class RegistrationHandler(KeywordHandler):
    """
    """

    keyword = "mc"

    def help(self):
        self.respond(get_text('reg-help', config.default_language)) #TODO: include help on 'enroll' keyword

    def handle(self, text):
        try:
            (location, patient_id, patient_conn, contact_time, lang) = parse_message(text, self.msg.connection)
        except ValueError, response:
            self.msg.respond(str(response))
            return True
        
        reg = Registration(patient_id=patient_id, contact_time=contact_time, 
                           connection=patient_conn, location=location, 
                           language=lang)
        reg.save()
    
        if contact_time != None: #signed up to receive notifications
            schedule_notifications(reg, self.msg.date)
            send_message(patient_conn, get_text('reg-success', lang) % ('%02d:%02d' % split_contact_time(contact_time)))
        else:
            self.msg.respond(get_text('rec-success', lang) % patient_id)

        return True

def parse_message (text, conn):
    pieces = text.split()

    if len(pieces) == 5 and pieces[0] == get_text('reg-keyword', config.default_language):
        return parse_message_pieces(conn, True, pieces[1], pieces[2], None, pieces[3], pieces[4])
    elif len(pieces) == 6 and pieces[0] == get_text('enroll-keyword', config.default_language):
        return parse_message_pieces(conn, True, pieces[1], pieces[2], pieces[3], pieces[4], pieces[5])
    elif len(pieces) in (3, 4) and pieces[0] == get_text('record-keyword', config.default_language):
        return parse_message_pieces(conn, False, pieces[1], pieces[2], pieces[3] if len(pieces) > 3 else None, None, None)
    else:
        if text.startswith('enroll'):
            raise ValueError(get_text('cannot-parse-enroll', config.default_language))
        elif text.startswith('record'):
            raise ValueError(get_text('cannot-parse-record', config.default_language))
        else:
            raise ValueError(get_text('cannot-parse-reg', config.default_language))

def parse_message_pieces (conn_recvd_from, subscribing, site_id, patient_id, patient_phone_str, contact_time_str, lang):
    """parse the sms message, either raising a variety of exceptions, or returning patient id,
    contact time as integer minutes since midnight, and language code to use for future notifications"""

    #language code
    if subscribing:
        validated_language = get_validated_language(lang) 
        if not validated_language:
            raise ValueError(get_text('language-unrecognized', config.default_language))
        else:
            lang = validated_language
    else:
        lang = config.default_language

    #site
    location = get_validated_site(site_id)
    if not location:
        raise ValueError(get_text('site-unrecognized', lang))
    
    #patient ID
    if not validate_patient_id_format(patient_id):
        raise ValueError(get_text('patid-unrecognized', lang))
    
    #patient phone # (optional -- use incoming connection if missing)
    if patient_phone_str:
        phone = parse_phone(patient_phone_str)
        if phone == None:
            raise ValueError(get_text('cannot-parse-phone', lang))
        try:
            patient_conn = Connection.objects.get(backend=conn_recvd_from.backend, identity=phone)
        except Connection.DoesNotExist:
            patient_conn = Connection(backend=conn_recvd_from.backend, identity=phone)
            patient_conn.save()
    else:
        if subscribing:
            patient_conn = conn_recvd_from
        else:
            patient_conn = None

    #check if patient has already been registered
    try:
        reg = Registration.objects.get(patient_id=patient_id)
        patid_already_registered = True
    except Registration.DoesNotExist:
        patid_already_registered = False
        
    #check if phone number has already been registered
    phone_already_registered = False
    if patient_conn:
        try:
            Registration.objects.get(connection=patient_conn)
            phone_already_registered = True
        except Registration.DoesNotExist:
            pass
    
    #todo: change behavior if existing registration is completed/expired
    if patid_already_registered:
        if phone_already_registered or not subscribing:
            raise ValueError(get_text('already-registered', lang) % reg.registered_on.strftime('%d-%m-%Y'))
        else:
            raise ValueError(get_text('patid-already-registered', lang))
    elif phone_already_registered:
        raise ValueError(get_text('phone-already-registered', lang))
    
    if subscribing:
        contact_time = parse_contact_time(contact_time_str)
        if contact_time == None:
            raise ValueError(get_text('cannot-parse-time', lang))
    else:
        contact_time = None
    
    return (location, patient_id, patient_conn, contact_time, lang)

def get_validated_language(language):
    """validate and normalize the language, returning a reference to
    the cleaned string, or None if not found."""
        #todo: should do better cleanup of param
    if language.lower() in config.itext:
        return language.lower()
    
def get_validated_site(site_id):
    """validate and normalize the site id, returning a reference to
    the location object, or None if not found."""
        #todo: should do better cleanup of param
    try:
        return Location.objects.get(slug=site_id)
    except Location.DoesNotExist:
        return None
    
#todo: should normalize patient id here too, if applicable
def validate_patient_id_format(patient_id):
    """validate and normalize the patient id"""
    return True

def parse_contact_time (contact_time_str):
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

def parse_phone (sphone):
    phone = None

    if len(sphone) == 10 and sphone.startswith('0'):
        phone = sphone
    elif len(sphone) == 13 and sphone.startswith('+' + config.country_code):
        phone = '0' + sphone[4:]
    elif len(sphone) == 12 and sphone.startswith(config.country_code):
        phone = '0' + sphone[3:]

    if phone and not re.match('^[0-9]{10}$', phone):
        phone = None

    if phone and config.backend_phone_format == 'intl':
        phone = '+' + config.country_code + phone[1:]
    return phone



