'''
Created on Mar 31, 2010

@author: Drew Roos
'''

import circumcision.apps.circumcision.views as views
import circumcision.apps.circumcision.emailutil as emailutil
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^circumcision/$', views.patient_list),
    url(r'^circumcision/patient/(.+)/$', views.patient_update),
    url(r'^circumcision/export/$', views.export),
    url(r'^circumcision/msglog/$', views.msglog),
    url(r'^circumcision/diagnostics/$', views.diagnostics),
    url(r'^circumcision/debug/emailreport/$', emailutil.debug_email_report),
)
