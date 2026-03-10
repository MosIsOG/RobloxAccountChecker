from primp import Client
from typing import Union, List
from util import Util

class Session:
    @staticmethod
    def session() -> List[Union[Client, str, str, str]]:
        proxy = Util.get_random_proxy()

        browsers = [
            ("chrome_133", '"Not/A)Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"', "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36")
        ]

        impersonate, sec_ch_ua, user_agent = browsers[0]

        session = Client(impersonate=impersonate, impersonate_os="windows", proxy=proxy, verify=False)

        return (session, sec_ch_ua, user_agent, proxy)