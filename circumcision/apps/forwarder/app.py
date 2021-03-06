import urllib2

import rapidsms
from django.conf import settings
from circumcision.apps.forwarder.models import ForwardLocation

class App (rapidsms.App):
    """The forwarder app allows you to check other rapidsms installations
       for message handling logic.  You define a configured list of servers
       to forward to, and this app will forward the message to all of them.
       
       It recommended that if you are doing any additional processing on your
       own server that this app be put _last_ in your list of apps, so that
       any messages that are handled by any of the other installed apps are
       not extraneously forwarded.
    """

    def handle (self, message):
        """Forward the messages to any configured URLs"""
        forward_urls = ForwardLocation.objects.filter(is_active=True)
        forwarded = forward_urls.count() > 0
        
        self.debug("Forwarder app catches %s" % message)
        for url in forward_urls:
            
            formatted_url = url.url % {"message": urllib2.quote(message.text),
                                       "identity": urllib2.quote(message.peer) }
            response = urllib2.urlopen(formatted_url)
            if url.should_respond:
                message.respond(response.read())
        
        if forwarded and \
           settings.FORWARDER_DELETE_FROM_MESSAGE_LOG and hasattr(message, "logger_msg"):
            self.debug("Forwarder app deleting message log: %s" % message.logger_msg)
            message.logger_msg.delete()
        
        if forwarded:
            return True
        

    