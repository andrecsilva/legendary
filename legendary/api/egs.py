# !/usr/bin/env python
# coding: utf-8

import requests
import logging

from requests.auth import HTTPBasicAuth

from legendary.models.exceptions import InvalidCredentialsError


class EPCAPI:
    _user_agent = 'UELauncher/10.13.1-11497744+++Portal+Release-Live Windows/10.0.18363.1.256.64bit'
    # required for the oauth request
    _user_basic = '34a02cf8f4414e29b15921876da36f9a'
    _pw_basic = 'daafbccc737745039dffe53d94fc76cf'

    _oauth_host = 'account-public-service-prod03.ol.epicgames.com'
    _launcher_host = 'launcher-public-service-prod06.ol.epicgames.com'
    _entitlements_host = 'entitlement-public-service-prod08.ol.epicgames.com'
    _catalog_host = 'catalog-public-service-prod06.ol.epicgames.com'

    def __init__(self):
        self.session = requests.session()
        self.log = logging.getLogger('EPCAPI')
        self.unauth_session = requests.session()
        self.session.headers['User-Agent'] = self._user_agent
        self.unauth_session.headers['User-Agent'] = self._user_agent
        self._oauth_basic = HTTPBasicAuth(self._user_basic, self._pw_basic)

        self.access_token = None
        self.user = None

    def resume_session(self, session):
        self.user = session
        self.session.headers['Authorization'] = f'bearer {self.user["access_token"]}'
        return self.user

    def start_session(self, refresh_token: str = None, exchange_token: str = None) -> dict:
        if refresh_token:
            params = dict(grant_type='refresh_token',
                          refresh_token=refresh_token,
                          token_type='eg1')
        elif exchange_token:
            params = dict(grant_type='exchange_code',
                          exchange_code=exchange_token,
                          token_type='eg1')
        else:
            raise ValueError('At least one token type must be specified!')

        r = self.session.post(f'https://{self._oauth_host}/account/api/oauth/token',
                              data=params, auth=self._oauth_basic)
        # Only raise HTTP exceptions on server errors
        if r.status_code >= 500:
            r.raise_for_status()

        j = r.json()
        if 'error' in j:
            self.log.warning(f'Login to EGS API failed with errorCode: {j["errorCode"]}')
            raise InvalidCredentialsError(j['errorCode'])

        self.user = j
        self.session.headers['Authorization'] = f'bearer {self.user["access_token"]}'
        return self.user

    def invalidate_session(self):  # unused
        r = self.session.delete(f'https://{self._oauth_host}/account/api/oauth/sessions/kill/{self.access_token}')

    def get_game_token(self):
        r = self.session.get(f'https://{self._oauth_host}/account/api/oauth/exchange')
        r.raise_for_status()
        return r.json()

    def get_game_assets(self):
        r = self.session.get(f'https://{self._launcher_host}/launcher/api/public/assets/Windows',
                             params=dict(label='Live'))
        r.raise_for_status()
        return r.json()

    def get_game_manifest(self, namespace, catalog_item_id, app_name):
        r = self.session.get(f'https://{self._launcher_host}/launcher/api/public/assets/v2/platform'
                             f'/Windows/namespace/{namespace}/catalogItem/{catalog_item_id}/app'
                             f'/{app_name}/label/Live')
        r.raise_for_status()
        return r.json()

    def get_user_entitlements(self):
        user_id = self.user.get('account_id')
        r = self.session.get(f'https://{self._entitlements_host}/entitlement/api/account/{user_id}/entitlements',
                             params=dict(start=0, count=5000))
        r.raise_for_status()
        return r.json()

    def get_game_info(self, namespace, catalog_item_id):
        r = self.session.get(f'https://{self._catalog_host}/catalog/api/shared/namespace/{namespace}/bulk/items',
                             params=dict(id=catalog_item_id, includeDLCDetails=True, includeMainGameDetails=True,
                                         country='US', locale='en'))
        r.raise_for_status()
        return r.json().get(catalog_item_id, None)