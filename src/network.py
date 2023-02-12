"""
    Assigment for U6 A1: Seguridad y encriptado.

    Author: Eloy Uziel García Cisneros (eloy.garcia@edu.uag.mx)

    usage: import network
           from network import <class>

"""

import socket
import pickle
import logging
import threading
import rsa
import os
import hashlib
import getpass

LOGGER = logging.getLogger(__name__)
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

class AuthError(Exception):
    pass

class Crypto:

    ENCODING = 'UTF-8'

    def __init__(self) -> None:
        self.key_pub, self.key_priv = rsa.newkeys(512)

    def encrypt(self, data, key_pub):
        return rsa.encrypt(data.encode(self.ENCODING), key_pub)

    def decrypt(self, data):
        return rsa.decrypt(data, self.key_priv).decode(self.ENCODING)

class User:

    def __init__(self, user, pwd) -> None:
        self.user = user
        self.hash = hashlib.sha256(pwd.encode('utf-8')).hexdigest()

class Network:

    ADDR = ('localhost', 20001)

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

class Server(Network):

    def __init__(self):
        super().__init__()
        self.sock.bind(self.ADDR)
        self.sock.listen(10)
        self.user_db = {}
        self.clients = {}
    
    def _login(self, cred: User):
        if hash := self.user_db.get(cred.user):
            if cred.hash ==  hash: return True
            raise AuthError('Invalid credentials.')
        return self._singup(cred)
        
    
    def _singup(self, cred: User):
        if cred.user in self.user_db:
            raise AuthError('User already in db.')
        self.user_db[cred.user] = cred.hash
        return True
    
    def _remove_client(self, user):
        del self.clients[user]
        self._boardcast()


    def _boardcast(self):
        LOGGER.info('broadcast pub keys')
        
        user_list = {usr: key['enc_key'] for usr, key in self.clients.items()}
        for user, u_data in self.clients.items():
            data = {'comm': user_list}
            try:
                u_data['conn'].send(pickle.dumps(data))
            except:
                del self.clients[user]

    def threaded_client(self, conn: socket.socket, addr):
        LOGGER.info('Waiting for client credentials')
        data = pickle.loads(conn.recv(1024))
        resp = {}
        try:
            LOGGER.info('Validating creds')
            self._login(data['cred'])
        except AuthError as err:
            LOGGER.warning('Unable to accept client.')
            resp['error'] = str(err)
            resp = pickle.dumps(resp)
            conn.send(resp)
            conn.close()
            return

        MYSELF = data['cred'].user
        del data['cred']

        self.clients[MYSELF] = {'inbox': [], 'outbox': [], 'conn': conn, 'enc_key': data['enc_key']}
        data = {'msg': f"Welcome {MYSELF}"}
        data = pickle.dumps(data)

        LOGGER.info('client connected. Sending response.')
        conn.send(data)
        self._boardcast()

        while True:
            try:
                data = conn.recv(1024)
                decoded = pickle.loads(data)

                # Print decoded (NOT decrypted, can only be decripted by receiver.)
                LOGGER.info(decoded)

                # Send msg to receiver.
                self.clients[decoded['to']]['conn'].sendall(data)
            except (ConnectionResetError, EOFError):
                self._remove_client(MYSELF)
                break
            except KeyError:
                pass
    
    def console(self):
        while True:
            q = input('')

            func = {'db': self.user_db,
                    'active': self.clients.keys()}
            
            LOGGER.info(func.get(q, f'available cmds: {func.keys()}'))


    def start_server(self):
        LOGGER.info('Starting server console.')
        threading.Thread(target=self.console, daemon=True).start()

        LOGGER.info('Starting server, waiting for incomming conn.')
        while True:
            try:
                conn, addr = self.sock.accept()
                LOGGER.info('Client connected %s', addr)
                threading.Thread(target=self.threaded_client, args=(conn, addr), daemon=True).start()
            except KeyboardInterrupt:
                LOGGER.warning('Shutting down server.')
                self.sock.close()

class Client(Network):

    def __init__(self):
        super().__init__()
        self.keys = Crypto()
        self._init_user()
        self._login()
        self.active_users = {}

        # Start listener
        LOGGER.info('starting listener.')
        threading.Thread(target=self.receive, daemon=True).start()

        # Main Thread
        self.send()
    
    def _init_user(self):
        print('Sign-in/Sign-up.. Press ENTER when done.')
        user = input('USER: ')
        pwd = getpass.getpass('PWD: ')
        self.user_data = User(user, pwd)
    
    def _login(self):
        self.sock.connect(self.ADDR)
        LOGGER.info('Connected to server.')
    
        data = {'cred': self.user_data, 'enc_key': self.keys.key_pub}

        LOGGER.info('Sending cred data.')
        self.sock.sendall(pickle.dumps(data))

        LOGGER.info('Waiting for server response.')
        resp = pickle.loads(self.sock.recv(1024))
        if err := resp.get('error'):
            print(err)
            self.sock.close()
            quit()
        LOGGER.info(resp)
    
    def receive(self):
        while True:
            data = pickle.loads(self.sock.recv(1024))
            if comm := data.get('comm'):
                self.active_users = comm
                LOGGER.info('active users: %s', self.active_users.keys())
                continue
            LOGGER.info(self.keys.decrypt(data['msg']))
            

    def send(self):
        LOGGER.info('Send data in the format <USER:Message>')
        while True:
            data = input('')
            # Skip empty messages.
            if not data:
                continue
            if data == 'q!':
                LOGGER.info('Leaving chat!')
                os._exit(0)
            
            data = data.split(':')
            if len(data) < 2 or data[0] not in self.active_users:
                LOGGER.error("Coulnd't find user")
                continue

            data[1] = self.keys.encrypt(data[1], self.active_users[data[0]])
            data = {'to': data[0], 'msg': data[1]} 
            data = pickle.dumps(data)

            self.sock.sendall(data)
            
 
        


