#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4

from circumcision.apps.circumcision import config
from rapidsms.contrib.handlers import KeywordHandler
from reg_util import process_registration, parse_message_pieces

class RegisterHandler(KeywordHandler):
    """
    """

    keyword = "mc"

    def help(self):
        self.respond(get_text('reg-help', config.default_language))

    def handle(self, text):
        process_registration(self.msg, text, lambda text, conn: return parse_message(text, conn))
        return True

def parse_message (text, conn):
    pieces = text.split()
    
    if len(pieces) != 5 or pieces[0] != get_text('register-keyword', config.default_language):
        raise ValueError(get_text('cannot-parse', config.default_language))
    
    return parse_message_pieces(conn, pieces[1], pieces[2], None, pieces[3], pieces[4])

