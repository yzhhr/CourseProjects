'''
A standard eke implementation, from the paper https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=213269
The demo is based on cryptography and Flask
'''

from cryptography.fernet import Fernet # symmetric encryption
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from base64 import urlsafe_b64encode, urlsafe_b64decode

class UserInfo:
    private_key: rsa.RSAPrivateKey
    public_key: rsa.RSAPublicKey
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.private_key = rsa.generate_private_key(65537, 2048)
        self.public_key = self.private_key.public_key()
        self.R = Fernet.generate_key()
        self.S = Fernet.generate_key()
        self.challenge_A = Fernet.generate_key()
        self.challenge_B = Fernet.generate_key()
    
    @property
    def key_P(self):
        return Fernet(self.password)
    
    @property
    def key_R(self):
        return Fernet(self.R)
    
    @property
    def key_S(self):
        return Fernet(self.S)
    
    def asymmetric_encrypt(self, data: bytes):
        return self.public_key.encrypt(
            data,
            padding=padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
    
    def asymmetric_decrypt(self, data: bytes):
        return self.private_key.decrypt(
            data,
            padding=padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

class Server:
    database: dict[str, UserInfo] # username -> allinfo
    def __init__(self):
        self.database = {}

    def negotiate_12(self, userinfo: UserInfo, data: bytes):
        data = userinfo.key_P.decrypt(data)
        public_key = serialization.load_pem_public_key(data)
        assert isinstance(public_key, rsa.RSAPublicKey)
        userinfo.public_key = public_key
        userinfo.R = Fernet.generate_key()
        return userinfo.key_P.encrypt(userinfo.asymmetric_encrypt(userinfo.R))
    
    def negotiate_34(self, userinfo: UserInfo, data: bytes):
        userinfo.challenge_A = userinfo.key_R.decrypt(data)
        userinfo.challenge_B = Fernet.generate_key()
        A_concat_B = userinfo.challenge_A + userinfo.challenge_B
        response = userinfo.key_R.encrypt(A_concat_B)
        return response

    def negotiate_56(self, userinfo: UserInfo, data: bytes):
        challenge_B = userinfo.key_R.decrypt(data)
        assert challenge_B == userinfo.challenge_B
        self.S = Fernet.generate_key()
        return userinfo.key_R.encrypt(userinfo.S)

class Client(UserInfo):
    def negotiate_1(self):
        self.private_key = rsa.generate_private_key(65537, 2048)
        self.public_key = self.private_key.public_key()
        return self.key_P.encrypt(self.public_key.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo
        ))
    
    def negotiate_23(self, data: bytes):
        self.R = self.asymmetric_decrypt(self.key_P.decrypt(data))
        self.challenge_A = Fernet.generate_key()
        return self.key_R.encrypt(self.challenge_A)

    def negotiate_45(self, data: bytes):
        A_concat_B = self.key_R.decrypt(data)
        challenge_A = A_concat_B[:44]
        challenge_B = A_concat_B[44:]
        assert challenge_A == self.challenge_A
        self.challenge_B = challenge_B
        return self.key_R.encrypt(self.challenge_B)
    
    def negotiate_6(self, data: bytes):
        self.S = self.key_R.decrypt(data)
