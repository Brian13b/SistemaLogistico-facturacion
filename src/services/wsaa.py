from src.core.auth import AfipAuthenticator
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class WSAAService:
    
    def __init__(self, cuit=None, cert_path=None, key_path=None, testing=None):
        self.authenticator = AfipAuthenticator(
            cuit=cuit,
            cert_path=cert_path,
            key_path=key_path,
            testing=testing
        )
    
    def get_auth(self, service="wsfe", force_new=False):
        return self.authenticator.authenticate(service, force_new)
    
    def get_auth_dict(self, service="wsfe", force_new=False):
        auth = self.get_auth(service, force_new)
        return {
            'Token': auth.token,
            'Sign': auth.sign,
            'Cuit': auth.cuit
        }