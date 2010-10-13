import urllib2
import logging
import logging.handlers
import json
import smtplib

DIAG_URL = 'http://173.203.120.166/circumcision/diagnostics/'

RECIPIENTS = [
    'droos@dimagi.com',
    '7815584462@tmomail.net',
    'czue@dimagi.com',
    '6174160544@tmomail.net',
]

SMTP_PASS = FILLMEIN

class TLSSMTPHandler(logging.handlers.SMTPHandler):
    def emit(self, record):
        headers = []

        headers.append(('From', self.fromaddr))
        headers.append(('To', ', '.join(self.toaddrs)))
        headers.append(('Subject', self.getSubject(record)))
        headers.append(('Date', self.date_time()))
        headers.append(('Mime-Version', '1.0'))
        headers.append(('Content-Type', '%s; charset="%s";' % ('text/plain', 'ISO-8859-1')))
        headers.append(('Content-Transfer-Encoding', '7bit'))

        header = '\r\n'.join('%s: %s' % h for h in headers)
        content = self.format(record)

        server = smtplib.SMTP(self.mailhost, self.mailport)
        server.set_debuglevel(0)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(self.username, self.password)
        server.sendmail(self.fromaddr, self.toaddrs, '%s\r\n\r\n%s' % (header, content))
        server.quit()

def init_logging():
    root = logging.getLogger()
    root.setLevel(logging.ERROR)
    handler = TLSSMTPHandler(
        ('smtp.gmail.com', 587),
        'Uptime Monitor <uptime@dimagi.com>',
        RECIPIENTS,
        'circumcision server error',
        ('hgmon@dimagi.com', SMTP_PASS)
    )
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(message)s'))
    root.addHandler(handler)
init_logging()

try:
    f = urllib2.urlopen(DIAG_URL, timeout=180)
    data = json.loads(f.read())
    errors = data['errors']

    if errors:
        logging.error('errors on server:\n\n' + '\n'.join(errors))
except Exception, e:
    logging.error('could not contact rapidsms server: %s %s' % (type(e), str(e)))
