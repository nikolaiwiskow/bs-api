import requests
import json

from pprint import pprint
from typing import Union

from utilities import Utilities
from config import CONFIG





class MessageBird():


    def __init__(self):
        self.api_key = CONFIG["messagebird"]["api_key"]
        self.base_url = "https://conversations.messagebird.com/v1"
        self.mb_namespace = "BeStrong Personal Training"
        self.headers = {
            "Authorization": "AccessKey " + self.api_key,
            "Accept": "application/json"
        }




    def replyToConversation(self, conversation_id: str, message_type: str, payload: object) -> object:
        """
        Reply to an incoming message via its conversation id
        @param conversation_id <str>: Messagebird Conversation ID
        @param message_type <str>: 'text' or 'hsm' for template
        @param payload <obj>: 
        
        {
            "type": "hsm",
            "content": {
                "hsm": {
                    "namespace": "da870d61_52cc_46ad_8627_abc2a5f47386",
                    "templateName": "erstberatung_no_show",
                    "language": {
                        "code": "de"
                    },
                    "params": [{"default": "Niko"}, {"default": "Wadim"}]
                }
            }
        }

        OR

        {
            "type": "text",
            "content": {
                "text": "This is the message you want to send."
            }
        }

        @return r_json <obj>: Messagebird response object
        """
        url = "%s/conversations/%s/messages" % (self.base_url, conversation_id)

        r = requests.post(url, headers=self.headers, data=json.dumps(payload))
        r_json = r.json()
        pprint(r_json)

        if r.ok and "status" in r_json:         
            return r_json

        return "Failure"