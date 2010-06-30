import smtplib
from StringIO import StringIO
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from circumcision.apps.circumcision.models import Registration, SentNotif
from circumcision.apps.circumcision.views import to_csv

def email_report (router, recipients):
    try:
        email_config = router.backends['email']
    except KeyError:
        email_config = None
    if email_config == None:
        raise Exception('no email back-end present!')

    subject = 'Circumcision Follow-up: Snapshot Report [%s]' % datetime.now().strftime('%Y-%m-%d')
    body_text = 'Attached you will find the latest dashboard snapshot.'

    msg = MIMEMultipart('mixed')
    msg.attach(MIMEText(body_text, 'plain'))

    buff = StringIO()
    to_csv(buff)
    attachment = MIMEText(buff.getvalue(), 'csv')
    attachment['Content-Disposition'] = 'attachment; filename="%s"' % 'report.csv'
    msg.attach(attachment)
    buff.close()

    send_email(email_config, recipients, subject, msg)

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

"""
to schedule from django shell:

from rapidsms.contrib.scheduler.models import EventSchedule
EventSchedule(callback='circumcision.apps.circumcision.emailutil.email_report',
              hours='17', minutes='0',
              callback_args=['address1@email.com, address2@email.com, address3@email.com']).save()

remember to delete old schedule entries
"""
