from rapidsms.contrib.scheduler.models import EventSchedule
from circumcision.apps.circumcision import config
from datetime import datetime, timedelta, time
import pytz
from circumcision.apps.circumcision.models import Registration, SentNotif
from rapidsms.contrib.messaging.utils import send_message
from circumcision.apps.circumcision.text import get_notification, split_contact_time

def send_notification (router, patient_pk, day):
    """send the notification for day N"""
    reg = Registration.objects.get(pk=patient_pk)
    send_message(reg.connection, get_notification(day, reg.language))
    #check for success?
    
    log = SentNotif(patient_id=reg, day=day)
    log.save()

def schedule_notifications (reg, reg_time):
    """schedule all future notificaitons to be sent for this patient"""
    for day in config.notification_days:
        send_at = calc_send_time(reg_time, reg.contact_time, day)
        #scheduler works in local server time instead of UTC
        local_send_at = send_at.astimezone(pytz.timezone(config.server_tz)).replace(tzinfo=None)
        
        schedule = EventSchedule(callback="circumcision.apps.circumcision.schedule.send_notification", \
                                 start_time=local_send_at, count=1, minutes='*',
                                 callback_args=[reg.pk, day],
                                 description='patient %s; day %d' % (reg.patient_id, day))
        schedule.save()

def calc_send_time (reg_time, contact_time, day):
    """Given the date/time of registration, and the daily contact time, return the
    UTC timestamp to send the notification for day N
    
    reg_time: timestamp of registration; naked datetime, UTC
    contact_time: time of day to send; int minutes from midnight
    day: number of days after day of registration that message is being sent
    """
    
    local_tz = pytz.timezone(config.incoming_tz)
    reg_time = pytz.utc.localize(reg_time)
    reg_time_local = reg_time.astimezone(local_tz)
    reg_date = reg_time_local.date()
    send_date = reg_date + timedelta(days=day)
    send_time = time(*split_contact_time(contact_time))
    send_time_local = datetime.combine(send_date, send_time)
    send_at = local_tz.localize(send_time_local).astimezone(pytz.utc)
    return send_at

