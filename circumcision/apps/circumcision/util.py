from circumcision.apps.circumcision.models import Registration, SentNotif
from rapidsms.contrib.scheduler.models import EventSchedule
from rapidsms.contrib.messagelog.models import Message
import circumcision.apps.circumcision.config as config
from circumcision.apps.circumcision.text import get_notification
import pytz

def validate_message_uniqueness():
    for lang in config.itext:
        msgs = [get_notification(d, lang) for d in config.notification_days]
        if len(set(msgs)) != len(config.notification_days):
            raise ValueError('messages for language [%s] are not unique!' % lang)

def normalize_datetime(dt):
    if not dt.tzinfo:
        dt = pytz.timezone(config.server_tz).localize(dt)
    return dt.astimezone(pytz.timezone(config.incoming_tz))

def sending_report():
    #if each day's message is not unique within a given language, we won't be able to
    #reliably tell when a particular day's message was sent
    validate_message_uniqueness()

    sendlog = []

    patients = Registration.objects.filter(contact_time__isnull=False)
    messages = Message.objects.filter(direction='O')
    scheduled_msgs = EventSchedule.objects.all()

    for p in patients:
        for d in config.notification_days:
            try:
                event = scheduled_msgs.get(description='patient %s; day %d' % (p.patient_id, d))
                scheduled_send = normalize_datetime(event.start_time)
            except EventSchedule.DoesNotExist:
                scheduled_send = None

            text = get_notification(d, p.language)
            try:
                outgoing = messages.get(text=text, connection=p.connection)
                sent_on = normalize_datetime(outgoing.date)
            except Message.DoesNotExist:
                sent_on = None

            sendlog.append({'pat': p.patient_id, 'day': d, 'sched': scheduled_send, 'sent': sent_on})

    return sendlog
