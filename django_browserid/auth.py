try:
    import json
except ImportError:
    import simplejson as json

import logging
import urllib

import httplib2

from django.conf import settings
from django.contrib.auth.models import User

log = logging.getLogger(__name__)

DEFAULT_HTTP_PORT = '80'
DEFAULT_VERIFICATION_URL = 'https://browserid.org/verify'
OKAY_RESPONSE = 'okay'


class BrowserIDBackend(object):
    supports_anonymous_user = False
    supports_object_permissions = False

    def _construct_audience(self, host, port):
        if port and port != DEFAULT_HTTP_PORT:
            return u'%s:%s' % (host, port)
        return host

    def _verify(self, assertion, audience):
        """Verify assertion using an external verification service."""
        verify_url = getattr(settings, 'BROWSERID_VERIFICATION_URL',
                             DEFAULT_VERIFICATION_URL)
        client = httplib2.Http()
        response, content = client.request('%s?%s' % (verify_url,
            urllib.urlencode(dict(assertion=assertion, audience=audience))),
            'POST')
        result = json.loads(content)
        if result['status'] == OKAY_RESPONSE:
            return result
        return False

    def authenticate(self, assertion=None, host=None, port=None):
        result = self._verify(assertion, self._construct_audience(host, port))
        if result is None:
            return None
        email = result['email']
        # in the rare case that two user accounts have the same email address,
        # log and bail. randomly selecting one seems really wrong.
        users = User.objects.filter(email=email)
        if len(users) > 1:
            log.warn('%d users with email address %s.' % (len(users), email))
            return None
        if len(users) == 1:
            return users[0]
        # todo - support creation of accounts
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None