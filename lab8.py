"""
Полное сетевое приложение с шифрованием
Выполнил: Баранов Степан ТРПО24-1
"""

import socket
import threading
import time
import json
import os
import sys
from datetime import datetime

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    from cryptography.hazmat.primitives.asymmetric import dh
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
    print("[✓] Библиотека cryptography загружена")
except ImportError:
    CRYPTO_AVAILABLE = False
    print("[!] ВНИМАНИЕ: Библиотека cryptography не установлена!")
    print("    Установите: pip install cryptography")
    print("    Шифрование будет отключено\n")


# Часть 1: Базовый TCP сервер и клиент

class BasicTCPServer:
    """Базовый TCP сервер - основа для всех остальных"""
    
    def __init__(self, host='localhost', port=9090):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
    
    def start(self):
        """Запуск сервера"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True
        
        self._print_header("TCP сервер (базовый)")
        print(f"  Хост: {self.host}")
        print(f"  Порт: {self.port}")
        print(f"  Статус: Ожидание подключения...")
        print(f"{'─'*50}")
        
        try:
            client_socket, client_addr = self.server_socket.accept()
            print(f"\nКлиент подключен: {client_addr}")
            
            data = client_socket.recv(1024)
            if data:
                message = data.decode('utf-8')
                print(f"Получено: {message}")
                
                client_socket.sendall(data)
                print(f"Отправлено эхо: {message}")
            
            client_socket.close()
            print(f"Клиент отключен")
            
        except Exception as e:
            print(f"Ошибка: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Остановка сервера"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print(f"\nСервер остановлен")
    
    def _print_header(self, title):
        """Вывод заголовка"""
        print(f"\n╔{'═'*50}╗")
        print(f"║{title:^50}║")
        print(f"╚{'═'*50}╝")


class BasicTCPClient:
    """Базовый TCP клиент"""
    
    def __init__(self, host='localhost', port=9090):
        self.host = host
        self.port = port
    
    def send_message(self, message="Привет, сервер!"):
        """Отправка сообщения серверу"""
        self._print_header("TCP клиент (базовый)")
        print(f"  Сервер: {self.host}:{self.port}")
        print(f"{'─'*50}")
        
        client_socket = None
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            print(f"Подключение...")
            
            client_socket.connect((self.host, self.port))
            print(f"Подключено!")
            
            print(f"Отправка: {message}")
            client_socket.sendall(message.encode('utf-8'))
            
            response = client_socket.recv(1024)
            print(f"Ответ: {response.decode('utf-8')}")
            
        except ConnectionRefusedError:
            print(f"Ошибка: Сервер не запущен!")
            print(f"    Сначала запустите сервер")
        except Exception as e:
            print(f"Ошибка: {e}")
        finally:
            if client_socket:
                client_socket.close()
                print(f"Соединение закрыто")
    
    def _print_header(self, title):
        """Вывод заголовка"""
        print(f"\n╔{'═'*50}╗")
        print(f"║{title:^50}║")
        print(f"╚{'═'*50}╝")


# Часть 2, Многопоточный чат-сервер

class ChatServer:
    """Многопоточный чат-сервер"""
    
    def __init__(self, host='localhost', port=9090):
        self.host = host
        self.port = port
        self.clients = {}  # {client_id: (socket, address)}
        self.lock = threading.Lock()
        self.running = False
    
    def broadcast(self, message, sender=None):
        """Отправка сообщения всем клиентам"""
        with self.lock:
            for client_id, (client_socket, _) in self.clients.items():
                if client_id != sender:
                    try:
                        client_socket.sendall(message.encode('utf-8'))
                    except:
                        pass
    
    def handle_client(self, client_socket, client_addr, client_id):
        """Обработка клиента в отдельном потоке"""
        print(f"Клиент {client_id} подключен")
        
        try:
            welcome = f"Добро пожаловать в чат! Ваш ID: {client_id}"
            client_socket.sendall(welcome.encode('utf-8'))
            
            while self.running:
                data = client_socket.recv(1024)
                if not data:
                    break
                
                message = data.decode('utf-8')
                print(f"[{client_id}] {message}")
                
                if message == '/quit':
                    client_socket.sendall(b'Goodbye!')
                    break
                elif message.startswith('/whisper '):
                    parts = message[9:].split(' ', 1)
                    if len(parts) == 2:
                        target, msg = parts
                        with self.lock:
                            if target in self.clients:
                                sock, _ = self.clients[target]
                                sock.sendall(f"[Лично от {client_id}] {msg}".encode('utf-8'))
                                client_socket.sendall(f"Личное сообщение отправлено {target}".encode('utf-8'))
                            else:
                                client_socket.sendall(f"Клиент {target} не найден".encode('utf-8'))
                elif message.startswith('/users'):
                    with self.lock:
                        users = list(self.clients.keys())
                        client_socket.sendall(f"Пользователи в чате: {', '.join(users)}".encode('utf-8'))
                else:
                    self.broadcast(f"[{client_id}] {message}", sender=client_id)
                    
        except Exception as e:
            print(f"Ошибка при обработке {client_id}: {e}")
        finally:
            with self.lock:
                if client_id in self.clients:
                    del self.clients[client_id]
            client_socket.close()
            print(f"Клиент {client_id} отключен")
            self.broadcast(f"[Система] Пользователь {client_id} покинул чат")
    
    def start(self):
        """Запуск чат-сервера"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(10)
        self.running = True
        
        self._print_header("Многопоточный чат-сервер")
        print(f"  Хост: {self.host}")
        print(f"  Порт: {self.port}")
        print(f"  Статус: Ожидание клиентов...")
        print(f"{'─'*50}")
        
        try:
            while self.running:
                client_socket, client_addr = server_socket.accept()
                client_id = f"User{len(self.clients)+1}"
                
                with self.lock:
                    self.clients[client_id] = (client_socket, client_addr)
                
                thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_addr, client_id)
                )
                thread.daemon = True
                thread.start()
                
                print(f"Новый клиент: {client_id} ({client_addr})")
                self.broadcast(f"[Система] Пользователь {client_id} присоединился к чату")
                
        except KeyboardInterrupt:
            print("\nстановка сервера...")
        finally:
            self.running = False
            server_socket.close()
    
    def _print_header(self, title):
        """Вывод заголовка"""
        print(f"\n╔{'═'*50}╗")
        print(f"║{title:^50}║")
        print(f"╚{'═'*50}╝")


class ChatClient:
    """Клиент для чата"""
    
    def __init__(self, host='localhost', port=9090):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
    
    def receive_messages(self):
        """Поток для получения сообщений"""
        while self.running:
            try:
                data = self.socket.recv(1024)
                if data:
                    print(f"\n{data.decode('utf-8')}")
                    print("> ", end='', flush=True)
            except:
                break
    
    def start(self):
        """Запуск клиента"""
        self._print_header("ЧАТ-КЛИЕНТ")
        print(f"  Сервер: {self.host}:{self.port}")
        print(f"{'─'*50}")
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            print("Подключено к серверу!")
            
            self.running = True
            
            receive_thread = threading.Thread(target=self.receive_messages)
            receive_thread.daemon = True
            receive_thread.start()
            
            print("\nДоступные команды:")
            print("  /quit - выход из чата")
            print("  /users - список пользователей")
            print("  /whisper <ник> <сообщение> - личное сообщение")
            print(f"{'─'*50}\n")
            
            while self.running:
                message = input("> ")
                
                if not message:
                    continue
                
                self.socket.sendall(message.encode('utf-8'))
                
                if message == '/quit':
                    break
            
        except ConnectionRefusedError:
            print("Ошибка: Сервер не запущен")
        except Exception as e:
            print(f"Ошибка: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Остановка клиента"""
        self.running = False
        if self.socket:
            self.socket.close()
        print("Соединение закрыто")
    
    def _print_header(self, title):
        """Вывод заголовка"""
        print(f"\n╔{'═'*50}╗")
        print(f"║{title:^50}║")
        print(f"╚{'═'*50}╝")


# Часть 3, UDP сервер и клиент

class UDPServer:
    """UDP сервер"""
    
    def __init__(self, host='localhost', port=9091):
        self.host = host
        self.port = port
        self.socket = None
    
    def start(self):
        """Запуск UDP сервера"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.host, self.port))
        
        self._print_header("UDP СЕРВЕР")
        print(f"  Хост: {self.host}")
        print(f"  Порт: {self.port}")
        print(f"  Статус: Ожидание сообщений...")
        print(f"{'─'*50}")
        
        try:
            while True:
                self.socket.settimeout(1)
                try:
                    data, client_addr = self.socket.recvfrom(4096)
                    message = data.decode('utf-8')
                    
                    print(f"\nОт {client_addr}: {message}")
                    
                    if message == '/quit':
                        print("Завершение работы...")
                        break
                    
                    response = f"Эхо: {message}"
                    self.socket.sendto(response.encode('utf-8'), client_addr)
                    print(f"Отправлено: {response}")
                    
                except socket.timeout:
                    continue
                    
        except KeyboardInterrupt:
            print("\nОстановка сервера...")
        finally:
            self.stop()
    
    def stop(self):
        """Остановка сервера"""
        if self.socket:
            self.socket.close()
        print("Сервер остановлен")
    
    def _print_header(self, title):
        print(f"\n╔{'═'*50}╗")
        print(f"║{title:^50}║")
        print(f"╚{'═'*50}╝")


class UDPClient:
    """UDP клиент"""
    
    def __init__(self, host='localhost', port=9091):
        self.host = host
        self.port = port
        self.socket = None
    
    def start(self):
        """Запуск UDP клиента"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(2)
        
        self._print_header("UDP КЛИЕНТ")
        print(f"  Сервер: {self.host}:{self.port}")
        print(f"  Введите '/quit' для выхода")
        print(f"{'─'*50}")
        
        try:
            while True:
                message = input("\nСообщение: ")
                
                if not message:
                    continue
                
                self.socket.sendto(message.encode('utf-8'), (self.host, self.port))
                
                if message == '/quit':
                    break
                
                try:
                    response, _ = self.socket.recvfrom(4096)
                    print(f"Ответ: {response.decode('utf-8')}")
                except socket.timeout:
                    print("Таймаут: сервер не ответил")
                    
        except Exception as e:
            print(f"Ошибка: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Остановка клиента"""
        if self.socket:
            self.socket.close()
        print("[Клиент остановлен")
    
    def _print_header(self, title):
        print(f"\n╔{'═'*50}╗")
        print(f"║{title:^50}║")
        print(f"╚{'═'*50}╝")


# Часть 4, Сервер с селекторами

try:
    import selectors
    
    class SelectorServer:
        """Сервер с использованием селекторов"""
        
        def __init__(self, host='localhost', port=9092):
            self.host = host
            self.port = port
            self.selector = selectors.DefaultSelector()
            self.running = False
        
        def accept(self, sock):
            """Принятие нового соединения"""
            client_sock, client_addr = sock.accept()
            client_sock.setblocking(False)
            print(f"Клиент подключен: {client_addr}")
            self.selector.register(client_sock, selectors.EVENT_READ, self.read)
        
        def read(self, sock):
            """Чтение данных от клиента"""
            try:
                data = sock.recv(1024)
                if data:
                    message = data.decode('utf-8')
                    print(f"Получено: {message}")
                    
                    if message == '/quit':
                        sock.sendall(b'Goodbye!')
                        self.selector.unregister(sock)
                        sock.close()
                    else:
                        sock.sendall(data)
                        print(f"Отправлено эхо")
                else:
                    self.selector.unregister(sock)
                    sock.close()
                    print("Клиент отключен")
            except:
                self.selector.unregister(sock)
                sock.close()
        
        def start(self):
            """Запуск сервера"""
            server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_sock.bind((self.host, self.port))
            server_sock.listen(100)
            server_sock.setblocking(False)
            
            self.selector.register(server_sock, selectors.EVENT_READ, self.accept)
            self.running = True
            
            self._print_header("СЕРВЕР С СЕЛЕКТОРАМИ")
            print(f"  Хост: {self.host}")
            print(f"  Порт: {self.port}")
            print(f"  Статус: Ожидание подключений...")
            print(f"{'─'*50}")
            
            try:
                while self.running:
                    events = self.selector.select(timeout=1)
                    for key, _ in events:
                        callback = key.data
                        callback(key.fileobj)
            except KeyboardInterrupt:
                print("\nОстановка сервера...")
            finally:
                self.stop()
        
        def stop(self):
            """Остановка сервера"""
            self.running = False
            for key in self.selector.get_map().values():
                try:
                    key.fileobj.close()
                except:
                    pass
            self.selector.close()
            print("Сервер остановлен")
        
        def _print_header(self, title):
            print(f"\n╔{'═'*50}╗")
            print(f"║{title:^50}║")
            print(f"╚{'═'*50}╝")
            
    SELECTORS_AVAILABLE = True
except ImportError:
    SELECTORS_AVAILABLE = False
    print("Модуль selectors не доступен")


# Часть 5, Защищенный чат (с шифрованием)

if CRYPTO_AVAILABLE:
    
    class SecureChatServer:
        """Защищенный чат-сервер с шифрованием"""
        
        def __init__(self, host='localhost', port=9093):
            self.host = host
            self.port = port
            self.dh_parameters = dh.generate_parameters(generator=2, key_size=2048, backend=default_backend())
        
        def start(self):
            """Запуск защищенного сервера"""
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((self.host, self.port))
            server_socket.listen(5)
            
            self._print_header("ЗАЩИЩЕННЫЙ ЧАТ-СЕРВЕР (TLS + AES)")
            print(f"  Хост: {self.host}")
            print(f"  Порт: {self.port}")
            print(f"  Шифрование: Диффи-Хеллман + AES-256")
            print(f"{'─'*50}")
            
            print("\nОжидание защищенного подключения...")
            
            client_socket, client_addr = server_socket.accept()
            print(f"Клиент подключен: {client_addr}")
            
            try:
                param_numbers = self.dh_parameters.parameter_numbers()
                dh_params = json.dumps({'p': param_numbers.p, 'g': param_numbers.g})
                client_socket.sendall(dh_params.encode('utf-8'))

                client_public_bytes = client_socket.recv(4096)
                client_public_key = serialization.load_pem_public_key(
                    client_public_bytes, backend=default_backend()
                )

                private_key = self.dh_parameters.generate_private_key()
                public_key = private_key.public_key()

                public_bytes = public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )
                client_socket.sendall(public_bytes)

                shared_secret = private_key.exchange(client_public_key)
                hkdf = HKDF(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=None,
                    info=b'secure_chat',
                    backend=default_backend()
                )
                session_key = hkdf.derive(shared_secret)
                
                print("Защищенное соединение установлено!")
                print(f"{'─'*50}")
                print("Защищенный чат запущен. Введите 'shutdown' для выхода")
                print(f"{'─'*50}")

                while True:
                    encrypted_data = client_socket.recv(4096)
                    if not encrypted_data:
                        break

                    iv = encrypted_data[:16]
                    ciphertext = encrypted_data[16:]
                    cipher = Cipher(algorithms.AES(session_key), modes.CBC(iv), backend=default_backend())
                    decryptor = cipher.decryptor()
                    plaintext_padded = decryptor.update(ciphertext) + decryptor.finalize()

                    padding_length = plaintext_padded[-1]
                    plaintext = plaintext_padded[:-padding_length]
                    message = plaintext.decode('utf-8')
                    
                    print(f"[Клиент] {message}")
                    
                    if message == 'shutdown':
                        break

                    response = f"Эхо: {message}"
                    iv = os.urandom(16)
                    padding_length = 16 - (len(response) % 16)
                    padded_response = response.encode('utf-8') + bytes([padding_length]) * padding_length
                    cipher = Cipher(algorithms.AES(session_key), modes.CBC(iv), backend=default_backend())
                    encryptor = cipher.encryptor()
                    ciphertext = encryptor.update(padded_response) + encryptor.finalize()
                    
                    client_socket.sendall(iv + ciphertext)
                    
            except Exception as e:
                print(f"Ошибка: {e}")
            finally:
                client_socket.close()
                server_socket.close()
        
        def _print_header(self, title):
            print(f"\n╔{'═'*50}╗")
            print(f"║{title:^50}║")
            print(f"╚{'═'50}╝")
    
    class SecureChatClient:
        """Защищенный чат-клиент"""
        
        def __init__(self, host='localhost', port=9093):
            self.host = host
            self.port = port
        
        def start(self):
            """Запуск защищенного клиента"""
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            self._print_header("ЗАЩИЩЕННЫЙ ЧАТ-КЛИЕНТ")
            print(f"  Сервер: {self.host}:{self.port}")
            print(f"{'─'*50}")
            
            try:
                client_socket.connect((self.host, self.port))
                print("Подключено к серверу")

                dh_params_data = client_socket.recv(4096)
                dh_params = json.loads(dh_params_data.decode('utf-8'))

                param_numbers = dh.DHParameterNumbers(p=dh_params['p'], g=dh_params['g'])
                parameters = param_numbers.parameters(default_backend())

                private_key = parameters.generate_private_key()
                public_key = private_key.public_key()

                public_bytes = public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )
                client_socket.sendall(public_bytes)

                server_public_bytes = client_socket.recv(4096)
                server_public_key = serialization.load_pem_public_key(
                    server_public_bytes, backend=default_backend()
                )

                shared_secret = private_key.exchange(server_public_key)
                hkdf = HKDF(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=None,
                    info=b'secure_chat',
                    backend=default_backend()
                )
                session_key = hkdf.derive(shared_secret)
                
                print("Защищенное соединение установлено!")
                print(f"{'─'*50}")
                print("Защищенный чат запущен. Введите 'quit' для выхода")
                print(f"{'─'*50}")

                while True:
                    message = input("Вы: ")
                    
                    if message == 'quit':
                        break

                    iv = os.urandom(16)
                    padding_length = 16 - (len(message) % 16)
                    padded_message = message.encode('utf-8') + bytes([padding_length]) * padding_length
                    cipher = Cipher(algorithms.AES(session_key), modes.CBC(iv), backend=default_backend())
                    encryptor = cipher.encryptor()
                    ciphertext = encryptor.update(padded_message) + encryptor.finalize()
                    
                    client_socket.sendall(iv + ciphertext)

                    encrypted_data = client_socket.recv(4096)
                    if not encrypted_data:
                        break

                    iv = encrypted_data[:16]
                    ciphertext = encrypted_data[16:]
                    cipher = Cipher(algorithms.AES(session_key), modes.CBC(iv), backend=default_backend())
                    decryptor = cipher.decryptor()
                    plaintext_padded = decryptor.update(ciphertext) + decryptor.finalize()
                    
                    padding_length = plaintext_padded[-1]
                    plaintext = plaintext_padded[:-padding_length]
                    print(f"Сервер: {plaintext.decode('utf-8')}\n")
                    
            except Exception as e:
                print(f"Ошибка: {e}")
            finally:
                client_socket.close()
        
        def _print_header(self, title):
            print(f"\n╔{'═'*50}╗")
            print(f"║{title:^50}║")
            print(f"╚{'═'*50}╝")


# Главное меню

def print_main_menu():
    """Вывод главного меню"""
    print("\n" + "="*60)
    print("        Сетевое приложение")
    print("="*60)
    print("\nВыберите режим работы:")
    print("-"*60)
    print("Базовая часть:")
    print("  1. TCP Сервер (базовый)")
    print("  2. TCP Клиент (базовый)")
    print("\nДополнительная часть:")
    print("  3. Многопоточный Чат-Сервер")
    print("  4. Чат-Клиент")
    print("  5. UDP Сервер")
    print("  6. UDP Клиент")
    if SELECTORS_AVAILABLE:
        print("  7. Сервер с Селекторами")
    if CRYPTO_AVAILABLE:
        print("  8. Защищенный Чат-Сервер (с шифрованием)")
        print("  9. Защищенный Чат-Клиент (с шифрованием)")
    print("\n  0. Выход")
    print("-"*60)


def main():
    """Главная функция"""
    while True:
        print_main_menu()
        choice = input("\nВаш выбор: ").strip()
        
        if choice == '1':
            server = BasicTCPServer()
            server.start()
            
        elif choice == '2':
            client = BasicTCPClient()
            message = input("Введите сообщение (Enter для стандартного): ").strip()
            if not message:
                message = "Привет, сервер!"
            client.send_message(message)
            
        elif choice == '3':
            server = ChatServer()
            server.start()
            
        elif choice == '4':
            client = ChatClient()
            client.start()
            
        elif choice == '5':
            server = UDPServer()
            server.start()
            
        elif choice == '6':
            client = UDPClient()
            client.start()
            
        elif choice == '7' and SELECTORS_AVAILABLE:
            server = SelectorServer()
            server.start()
            
        elif choice == '8' and CRYPTO_AVAILABLE:
            server = SecureChatServer()
            server.start()
            
        elif choice == '9' and CRYPTO_AVAILABLE:
            client = SecureChatClient()
            client.start()
            
        elif choice == '0':
            print("\nДо свидания")
            break
        
        else:
            print("\nНеверный выбор. Попробуйте снова.")
        
        input("\nНажмите Enter для продолжения...")


if __name__ == "__main__":
    main()