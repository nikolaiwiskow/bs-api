import requests
import pprint
import json

from config import CONFIG

class Slack():

    def __init__(self):
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        self.channels = {
            "fitness-leads": CONFIG["slack"]["fitness-leads"],
            "benachrichtigungen": CONFIG["slack"]["benachrichtigungen"],
            "fitness-dev-notifications": CONFIG["slack"]["fitness-dev-notifications"]
        }


    
    """
    Post a message to slack
    """
    def sendMessage(self, channel_name: str, message: str) -> str:
        url = self.channels[channel_name]

        data = {
            "text": message
        }
        
        r = requests.post(url, data=json.dumps(data), headers=self.headers)

        return r.text

