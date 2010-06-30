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
    patient.post_op = (date.today() - patient.registered_on).days
    patient.contact_time = '%02d:%02d' % split_contact_time(patient.contact_time)
    
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
    response['Content-Disposition'] = 'attachment; filename=circumcision_patients.csv'
    to_csv(response)
    return response

def to_csv (f):
    regs = load_patients()    

    headers = list(itertools.chain(['Patient ID', 'Days Post-op', 'Registered on', 'Phone #'],
                                   ['Day %d' % i for i in config.notification_days],
                                   ['Follow-up Visit', 'Final Visit']))

    def csvbool (b):
        return 'X' if b else ''

    def csvtext (s):
        return "'" + s
#        return '="%s"' % s

    writer = csv.writer(f)
    writer.writerow(headers)
    for r in regs:
        line = list(itertools.chain([csvtext(r.patient_id), r.post_op, r.registered_on.strftime('%Y-%m-%d'), csvtext(r.connection.identity)],
                                    [csvbool(n) for n in r.notifications],
                                    [csvbool(r.followup_visit), csvbool(r.final_visit)]))
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
        r.post_op = (date.today() - r.registered_on).days

    return regs

