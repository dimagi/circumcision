import smtplib
from StringIO import StringIO
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from circumcision.apps.circumcision.models import Registration
from rapidsms.contrib.locations.models import Location
from rapidsms.contrib.scheduler.models import EventSchedule
from circumcision.apps.circumcision.views import to_csv, load_patients
import circumcision.apps.circumcision.util as util
from django.http import HttpResponse
from django.template.loader import render_to_string

def email_report (router, recipients):
    try:
        email_config = router.backends['email']
    except KeyError:
        email_config = None
    if email_config == None:
        raise Exception('no email back-end present!')

    subject = 'Circumcision Follow-up: Snapshot Report [%s]' % datetime.now().strftime('%Y-%m-%d')
    body_text = email_report_body()

    msg = MIMEMultipart('mixed')
    msg.attach(MIMEText(body_text, 'html'))

    buff = StringIO()
    to_csv(buff)
    attachment = MIMEText(buff.getvalue(), 'csv')
    attachment['Content-Disposition'] = 'attachment; filename="%s"' % ('report_%s.csv' % datetime.now().strftime('%Y_%m_%d'))
    msg.attach(attachment)
    buff.close()

    send_email(email_config, recipients, subject, msg)

def email_report_body():
    content = []

    regs = load_patients()
    stats = util.reg_totals(regs)
    stats['header'] = 'All sites'
    content.append(stats)

    for loc in Location.objects.filter(type__slug='study-sites').order_by('slug'):
        stats = util.reg_totals(regs.filter(location=loc))
        stats['header'] = '%s-%s' % (loc.slug.upper(), loc.name)
        content.append(stats)        

    return render_to_string('circumcision/emailreport.html', {'c': content})

def send_email (send_config, to, subj, mime_body):
    #'to' can be list of addresses, or single string of comma-separated addresses
    if not hasattr(to, '__iter__'):
        to = [t.strip() for t in to.split(',')]

    mime_body['Subject'] = subj
    mime_body['From'] = send_config.username 
    mime_body['To'] = ', '.join(to)

    conn = smtplib.SMTP(host=send_config.smtp_host, port=send_config.smtp_port)
    conn.ehlo()
    conn.starttls()
    conn.ehlo()
    conn.login(send_config.username, send_config.password)
    conn.sendmail(send_config.username, to, mime_body.as_string())
    conn.quit()

def schedule(recipients, hour, minute, day_of_week=None, remove_old=True):
    if not hasattr(recipients, '__iter__'):
        raise ValueError('recipients must be list')

    daysofweek = {'sun': 6, 'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5}
    if day_of_week:
        matches = [d for d in daysofweek if d.startswith(day_of_week)]
        if len(matches) == 0:
            raise ValueError('unknown day of week [%s]' % day_of_week)
        elif len(matches) > 1:
            raise ValueError('ambiguous day of week [%s]' % day_of_week)
        dow = [daysofweek[matches[0]]]
    else:
        dow = None

    callback = 'circumcision.apps.circumcision.emailutil.email_report'

    if remove_old:
        EventSchedule.objects.filter(callback=callback).delete()

    EventSchedule(
        callback=callback,
        hours=[hour], minutes=[minute], days_of_week=dow,
        callback_args=recipients
    ).save()

"""
schedule([
  'droos@dimagi.com',
  'czue@dimagi.com',
  'odeny@u.washington.edu',
], 10, 0, 'f')
"""

def debug_email_report(request):
    return HttpResponse(email_report_body())
