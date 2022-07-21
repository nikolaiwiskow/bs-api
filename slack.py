import requests
import pprint
import json



class Slack():

    def __init__(self):
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        self.channels = {
            "fitness-leads": "https://hooks.slack.com/services/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",
            "benachrichtigungen": "https://hooks.slack.com/services/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",
            "fitness-dev-notifications": "https://hooks.slack.com/services/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"
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

