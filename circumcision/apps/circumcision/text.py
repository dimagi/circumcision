import circumcision.apps.circumcision.config as config

def get_text (key, lang):
    """return a localized text string for a given text key and language code"""
    if lang not in config.itext:
        raise ValueError('no language [%s] defined' % lang)
    elif key not in config.itext[lang]:
        raise ValueError('no translation for key [%s] in language [%s]' % (key, lang))
    else:
        return config.itext[lang][key]

def get_notification (day, lang):
    """return the notification text for day N"""
    return get_text('notif%d' % day, lang)

def split_contact_time (minutes_since_midnight):
    """split the 'minutes since midnight' contact time into hour and minute components"""
    m = int(minutes_since_midnight)
    return (m / 60, m % 60)

    