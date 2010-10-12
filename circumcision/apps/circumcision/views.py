'''
Created on Mar 31, 2010

@author: Drew Roos
'''

from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from rapidsms.utils import render_to_response
from circumcision.apps.circumcision.models import Registration, SentNotif
from circumcision.apps.circumcision.app import split_contact_time
import circumcision.apps.circumcision.config as config
from datetime import date
from django.forms import ModelForm, HiddenInput
from rapidsms.utils import paginated
import csv
import itertools
from datetime import datetime, timedelta
import util

def patient_list (request):

    #handle submission for updating a patient (from /patient/xxx/)
    patient_id = None
    if request.method == 'POST' and 'patient_id' in request.POST:
        patient_id = request.POST['patient_id']
    save_msg = None
    if patient_id != None:
        form = PatientForm(request.POST, instance=Registration.objects.get(patient_id=patient_id))
        if form.is_valid():
            form.save()
            save_msg = 'Successfully updated patient %s' % patient_id
        else:
            save_msg = 'Unable to update patient %s! %s' % (patient_id, form.errors)
    
    regs = load_patients()
    return render_to_response(request, 'circumcision/overview.html',
            {'days': config.notification_days, 'patients': paginated(request, regs), 'save_msg': save_msg})
    
def patient_update (request, patid):
    patient = get_object_or_404(Registration, patient_id=patid)
    form = PatientForm(instance=patient)
    
    sent = SentNotif.objects.filter(patient_id=patient)
    patient.notifications = ', '.join(str(d) for d in sorted([s.day for s in sent])) if len(sent) > 0 else 'none sent yet'
    annotate_patient(patient)

    return render_to_response(request, 'circumcision/patient.html',
            {'px': patient, 'pat_form': form})
    
class PatientForm(ModelForm):
    class Meta:
        model = Registration
        fields = ['patient_id', 'followup_visit', 'final_visit']
        
    def __init__(self, *args, **kwargs):
        ModelForm.__init__(self, *args, **kwargs)
        self.fields['patient_id'].widget = HiddenInput()

def export (request):
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=circumcision_patients_%s.csv' % datetime.now().strftime('%Y_%m_%d')
    to_csv(response)
    return response

def csvbool (b):
    return 'X' if b else ''

#note: escaping text in this way (to preserve leading zeros) only works when viewing in excel
def csvtext (s):
    return '="%s"' % s

def to_csv (f):
    regs = load_patients()    

    headers = list(itertools.chain(['Patient ID', 'Site', 'Days Post-op', 'Registered on', 'Phone #', 'Language'],
                                   ['Day %d' % i for i in config.notification_days],
                                   ['Follow-up Visit', 'Final Visit', 'Status']))

    writer = csv.writer(f)
    writer.writerow(headers)
    for r in regs:
        status_txt = {'late-final': 'Late for final', 'late-followup': 'Late for follow-up'}[r.status] if r.status else None
        phone_txt = r.connection.identity if r.connection else None
        if r.no_notif:
            phone_txt = phone_txt + ' (no notifications)' if phone_txt else '(no notifications)'
        else:
            phone_txt = csvtext(phone_txt)

        line = list(itertools.chain([csvtext(r.patient_id), r.site, r.post_op, r.registered_on.strftime('%Y-%m-%d'), phone_txt, r.language],
                                    [csvbool(n) for n in r.notifications],
                                    [csvbool(r.followup_visit), csvbool(r.final_visit), status_txt]))
        writer.writerow(line)

def load_patients ():
    regs = Registration.objects.all().order_by('-registered_on')
    sentlog = SentNotif.objects.all()

    sent = {}
    for s in sentlog:
        if s.patient_id not in sent:
            sent[s.patient_id] = set()
        days = sent[s.patient_id]
        days.add(s.day)
    
    for r in regs:
        days = sent[r] if r in sent else set()
        r.notifications = [(i in days) for i in config.notification_days]
        
        annotate_patient(r)

    return regs

def annotate_patient (p):
    p.post_op = (date.today() - p.registered_on).days
    p.no_notif = (p.contact_time == None)
    if not p.no_notif:
        p.contact_time = '%02d:%02d' % split_contact_time(p.contact_time)
    p.site = '%s-%s' % (p.location.slug.upper(), p.location.name)

    p.late_final = p.post_op > 42 and not p.final_visit
    p.late_fu = p.post_op > 7 and not p.followup_visit
    if p.late_final:
        p.status = 'late-final'
    elif p.late_fu:
        p.status = 'late-followup'
    else:
        p.status = None

def msglog (request):
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=circumcision_patients_%s.csv' % datetime.now().strftime('%Y_%m_%d')

    messages = util.sending_report()
    messages.sort(key=lambda m: (m['sched'], m['day'], m['pat']))

    writer = csv.writer(response)
    writer.writerow(['Patient ID', 'Day #', 'Scheduled', 'Sent on', 'Status'])

    for m in messages:
        sched = m['sched'].strftime('%Y-%m-%d %H:%M:%S') if m['sched'] else None
        sent_on = m['sent'].strftime('%Y-%m-%d %H:%M:%S') if m['sent'] else None

        if not sched:
            status = 'error'
        elif not sent_on:
            status = 'not sent yet'
        elif m['sent'] < m['sched'] - timedelta(seconds=15):
            status = 'strange: sent before scheduled'
        elif m['sent'] > m['sched'] + timedelta(seconds=90):
            diff = m['sent'] - m['sched']
            status = 'LATE: ' + format_timediff(diff)
        else:
            status = 'sent on time'

        writer.writerow([csvtext(m['pat']), m['day'], sched, sent_on, status])

    return response

def fdelta(d):
    return 86400.*d.days + d.seconds + 1.e-6*d.microseconds

def format_timediff(diff):
    t = int(fdelta(diff))

    s = t % 60
    m = (t / 60) % 60
    h = (t / 3600) % 24
    d = t / 86400

    if d > 0:
        return '%dd %02dh %02dm %02ds' % (d, h, m, s)
    elif h > 0:
        return '%dh %02dm %02ds' % (h, m, s)
    elif m > 0:
        return '%dm %02ds' % (m, s)
    else:
        return '%ds' % (s,)

