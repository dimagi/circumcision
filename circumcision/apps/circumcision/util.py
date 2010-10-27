from circumcision.apps.circumcision.models import Registration, SentNotif
from rapidsms.contrib.scheduler.models import EventSchedule
from rapidsms.contrib.messagelog.models import Message
import circumcision.apps.circumcision.config as config
from circumcision.apps.circumcision.text import get_notification
import pytz
from datetime import datetime, date, timedelta

def validate_message_uniqueness():
    for lang in config.itext:
        msgs = [get_notification(d, lang) for d in config.notification_days]
        if len(set(msgs)) != len(config.notification_days):
            raise ValueError('messages for language [%s] are not unique!' % lang)

def normalize_datetime(dt):
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
                should_be_sent = event.start_time <= datetime.now()
            except EventSchedule.DoesNotExist:
                scheduled_send = None
                should_be_sent = False

            text = get_notification(d, p.language) % {}
            #messages in localization config are escaped, while those in message log are not

            try:
                outgoing = messages.get(text=text, connection=p.connection)
                sent_on = normalize_datetime(outgoing.date)
            except Message.DoesNotExist:
                sent_on = None

            sendlog.append({'pat': p.patient_id, 'day': d, 'sched': scheduled_send, 'sent': sent_on, 'should_be_sent': should_be_sent})

    return sendlog

def reg_totals(regs):
    total_days = config.notification_days[-1]

    active_cutoff = date.today() - timedelta(days=total_days)
    week_cutoff = date.today() - timedelta(days=6)

    active = regs.filter(registered_on__gte=active_cutoff)
    last_week = regs.filter(registered_on__gte=week_cutoff)

    total_enrolled = len(regs)
    total_active = len(active)
    total_week = len(last_week)

    enrolled_receiving = len(regs.filter(contact_time__isnull=False))
    active_receiving = len(active.filter(contact_time__isnull=False))

    def visit(regs, has_had_visit, num_days, late_cutoff=None):
        def single_visit(r):
            regd_ago = date.today() - r.registered_on
            past_cutoff = (late_cutoff != None and regd_ago >= timedelta(days=late_cutoff))

            expected = regd_ago >= timedelta(days=num_days) and not past_cutoff
            returned = has_had_visit(r)
            late = regd_ago > timedelta(days=num_days) and not past_cutoff and not returned

            return (expected, returned, late)

        return [len(filter(lambda e: e, k)) for k in zip(*[single_visit(r) for r in regs])] if regs else [0, 0, 0]

    expected_fu_visit, returned_fu_visit, late_fu_visit = visit(regs, lambda r: r.followup_visit, 7, total_days)
    expected_final_visit, returned_final_visit, late_final_visit = visit(regs, lambda r: r.final_visit, total_days, total_days + 30)

    return {
        'ttl': total_enrolled,
        'active': total_active,
        'this_week': total_week,
        'ttl_recv': enrolled_receiving,
        'active_recv': active_receiving,
        'ttl_norecv': total_enrolled - enrolled_receiving,
        'active_norecv': total_active - active_receiving,
        'exp_fu': expected_fu_visit,
        'ret_fu': returned_fu_visit,
        'late_fu': late_fu_visit,
        'exp_fin': expected_final_visit,
        'ret_fin': returned_final_visit,
        'late_fin': late_final_visit,
    }
