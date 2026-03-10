from primp import Client

def retry(func):
    def wrapper(*func_args, **func_kwargs):
        attempt = 0
        while attempt < 3:
            try:
                return func(*func_args, **func_kwargs)
            except:
                attempt += 1
                if attempt == 3:
                    raise
    return wrapper

@retry
def get_rap(session: Client, UserID: int) -> int:
    """
    Returns the total offical roblox RAP value for a user

    Please be aware this function can take some time to run depending on internet speed and how many limiteds a user owns
    """
    ErroredRAP = 0
    TotalValue = 0
    Cursor = ""
    Done = False
    while(Done == False):
        try:
            response = session.get(f"https://inventory.roblox.com/v1/users/{UserID}/assets/collectibles?sortOrder=Asc&limit=100&cursor={Cursor}")
            Items = response.json()
            if((response.json()['nextPageCursor'] == "null") or response.json()['nextPageCursor'] == None):
                Done = True
            else:
                Done = False
                Cursor = response.json()['nextPageCursor']
            for Item in Items["data"]:
                try:
                    RAP = int((Item['recentAveragePrice']))
                    TotalValue = TotalValue + RAP
                except:
                    TotalValue = TotalValue
            if(response.json()['nextPageCursor'] == 'None'):
                Done = True
            
        except Exception as ex:
            Done = True
    return(TotalValue)

@retry
def get_robux(session: Client, user_id):
    return session.get(f"https://economy.roblox.com/v1/users/{user_id}/currency").json()["robux"]

@retry
def is_premium(session: Client, user_id):
    response = session.get(f"https://premiumfeatures.roblox.com/v1/users/{user_id}/validate-membership").text

    if response == "true":
        return True
    elif response == "false":
        return False
    
    raise ValueError("Failed to get result")

@retry
def get_pending_and_summary(session: Client, user_id):
    response = session.get(f"https://economy.roblox.com/v2/users/{user_id}/transaction-totals?timeFrame=Year&transactionType=summary").json()

    return [response["pendingRobuxTotal"], response["incomingRobuxTotal"]]

@retry
def has_payment_info(session: Client):
    response = session.get("https://apis.roblox.com/payments-gateway/v1/payment-profiles")

    if len(response.json()) != 0 and response.status_code == 200:
        return True
    
    return False

class AccountInfo:
    @staticmethod
    def get_account_info(session: Client, user_id) -> dict:
        try:
            robux = get_robux(session, user_id)
        except:
            robux = "_unknown"

        try:
            payment_info = has_payment_info(session)
        except:
            payment_info = "_unknown"
        
        try:
            premium = is_premium(session, user_id)
        except:
            premium = "_unknown"

        try:
            rap = get_rap(session, user_id)
        except:
            rap = "_unknown"

        try:
            pending_and_summary = get_pending_and_summary(session, user_id)
            pending = pending_and_summary[0]
            summary = pending_and_summary[1]
        except:
            pending = "_unknown"
            summary = "_unknown"

        return {
            "robux": robux,
            "premium": premium,
            "payment_info": payment_info,
            "rap": rap,
            "pending": pending,
            "summary": summary
        }