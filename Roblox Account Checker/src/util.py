import sys, os
from datetime import datetime
from string import digits, ascii_letters
from random import choice, randint
from json import load

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

with open("input/proxies.txt", "r", encoding="utf-8") as file:
    proxies = file.readlines()

with open("input/config.json", "r", encoding="utf-8") as file:
    config = load(file)

with open("input/accounts.txt", "r", encoding="utf-8", errors='replace') as file:
    accounts = file.readlines()

class Util:
    @staticmethod
    def encode_data(data) -> str:
        encoded_data = []
        for c in data:
            if ord(c) > 127 or c in " %$&+,/:;=?@<>%{}":
                encoded_data.append(f'%{ord(c):02X}')
            else:
                encoded_data.append(c)
        
        return ''.join(encoded_data)
    
    @staticmethod
    def get_random_proxy() -> str:
        return choice(proxies).strip("\n")
    
    @staticmethod
    def get_config() -> dict:
        return config
    
    @staticmethod
    def get_accounts() -> list:
        return accounts
    
    @staticmethod
    def get_random_string() -> str:
        return ''.join([choice(ascii_letters + digits) for _ in range(randint(12, 20))])
    
    @staticmethod
    def get_date_formatted() -> str:
        current_time = datetime.now()
        formatted_time = current_time.strftime("%m/%d/%Y %H:%M:%S")

        return formatted_time