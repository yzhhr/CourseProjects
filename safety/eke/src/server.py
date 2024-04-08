from typing import Callable
from eke import Server, UserInfo
from flask import Flask, request
import base64
from config import Config
from datetime import datetime

class WebServer(Server):
    def __init__(self):
        super().__init__()

    def template_request_handler(self, func: Callable[[UserInfo, bytes], bytes]):
        def wrapper():
            username = request.form['username']
            userinfo = self.database[username]
            data = request.form['data']
            data = base64.urlsafe_b64decode(data.encode())
            result = func(userinfo, data)
            return base64.urlsafe_b64encode(result).decode()
        wrapper.__name__ = func.__name__ # for Flask to recognize the function name
        return wrapper
    
    def add_user(self):
        username = request.form['username']
        password = request.form['password']
        self.database[username] = UserInfo(username, password)
        return f"User {username} added."
    
    def send_message(self, userinfo: UserInfo, data: bytes):
        data = userinfo.key_S.decrypt(data)
        message = data.decode()
        print(f"{userinfo.username} says: {message}")
        response_message = f"Message received at {datetime.now()}"
        return userinfo.key_S.encrypt(
            response_message.encode()
        )

    def register(self, app: Flask):
        app.route('/register', methods=['POST'])(self.add_user)

        reg_func = lambda func, rule: app.route(rule, methods=['POST'])(self.template_request_handler(func))
        reg_func(self.negotiate_12, '/negotiate12')
        reg_func(self.negotiate_34, '/negotiate34')
        reg_func(self.negotiate_56, '/negotiate56')
        reg_func(self.send_message, '/send')


app = Flask(__name__)

def main():
    server = WebServer()
    server.register(app)
    app.run(port=Config.PORT, debug=True)

if __name__ == '__main__':
    main()
