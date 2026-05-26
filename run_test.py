"""
Автоматический тест для проверки работы всех компонентов
Запускает сервер и клиента автоматически
"""

import subprocess
import threading
import time
import sys

def test_basic_communication():
    """Тест базового обмена сообщениями"""
    print("\n" + "="*60)
    print("Тест: Базовый обмен сообщениями")
    print("="*60)

    server_process = subprocess.Popen(
        [sys.executable, 'lab8.py'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    time.sleep(1)

    server_process.stdin.write('1\n')
    server_process.stdin.flush()
    
    time.sleep(1)

    client_process = subprocess.Popen(
        [sys.executable, 'lab8.py'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    time.sleep(1)

    client_process.stdin.write('2\n')
    client_process.stdin.flush()
    time.sleep(0.5)
    client_process.stdin.write('Тестовое сообщение\n')
    client_process.stdin.flush()
    
    time.sleep(2)

    server_process.terminate()
    client_process.terminate()
    
    print("Тест базового обмена завершен")

if __name__ == "__main__":
    test_basic_communication()