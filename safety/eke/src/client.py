from typing import Callable
from eke import Client
from config import Config
import requests, base64
import hashlib

class WebClient(Client):
    def __init__(self, username: str, password: str,
                 url: str = f'http://localhost:{Config.PORT}'):
        password_hash = hashlib.sha256(password.encode()).digest()[:32]
        password_hash = base64.urlsafe_b64encode(password_hash).decode()
        super().__init__(username, password_hash)
        self.url = url
    
    def request_register(self):
        data = {
            'username': self.username,
            'password': self.password
        }
        return requests.post(f'{self.url}/register', data=data).text
    
    def connect(self):
        data = self.negotiate_1()
        response = requests.post(f'{self.url}/negotiate12', data={
            'username': self.username,
            'data': base64.urlsafe_b64encode(data).decode()
        }).text
        data = base64.urlsafe_b64decode(response.encode())
        data = self.negotiate_23(data)
        response = requests.post(f'{self.url}/negotiate34', data={
            'username': self.username,
            'data': base64.urlsafe_b64encode(data).decode()
        }).text
        data = base64.urlsafe_b64decode(response.encode())
        data = self.negotiate_45(data)
        response = requests.post(f'{self.url}/negotiate56', data={
            'username': self.username,
            'data': base64.urlsafe_b64encode(data).decode()
        }).text
        data = base64.urlsafe_b64decode(response.encode())
        self.negotiate_6(data)
    
    def send_message(self, message: str):
        data = self.key_S.encrypt(message.encode())
        response = requests.post(f'{self.url}/send', data={
            'username': self.username,
            'data': base64.urlsafe_b64encode(data).decode()
        }).text
        response = base64.urlsafe_b64decode(response.encode())
        response = self.key_S.decrypt(response)
        print(f"Server says: {response.decode()}")

def main():
    username = "alice"
    password = "123456"
    client = WebClient(username, password)
    response = client.request_register()
    print(f"Register got: {response}")

    client.connect()
    while True:
        message = input("Enter message: ")
        client.send_message(message)
    



if __name__ == '__main__':
    main()
