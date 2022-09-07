import requests
import json
import logging

from pprint import pprint
from typing import Union

from utilities import Utilities
from config import CONFIG



#logging.basicConfig(filename='api.log', level=logging.DEBUG)

class ActiveCampaign():

    def __init__(self):
        self.base_url = "https://bestrong-fitness90613.api-us1.com/api/3"
        self.api_key = CONFIG["activeCampaign"]["api_key"]
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "api-token": self.api_key
        }
        self.standard_fields = ["firstname", "lastname", "email", "phone"]
        self.custom_fields = {
            "hs_lead_status": "1",
            "hs_id": "2",
            "form_complete_dataset": "4",
            "Geschlecht": "6",
            "Ziel": "7",
            "whatsapp-opt-in": "9",
            "campaign_last_click": "10",
            "at_id": "11"
        }
        self.field_map = {
            "firstname": "firstName",
            "lastname": "lastName"
        }
        self.default_values = {
            "hs_lead_status": "OPEN"
        }
        self.lists = {
            "Gratis Session": "2"
        }





    def __prepareDataForRequest(self, data: object, use_standard_values=True) -> object:
        """
        Prepare incoming data for Webhook to Active campaign
        @param data <json>: Key-Value map of incoming form data
        @param data <json>: Use standard-hubspot values for e.g. lead-status? default:True

        @return ac_data <json>: {
            "contact": {
                "normalValue": "bla",
                "fieldValues": [
                    {"field": "1", "value": "customField1"},
                    ...         
                ]
            }
        }
        """
        ac_data = {
                    "contact": {
                        "fieldValues": []
                    }
                }

        # Enrich data with default values, if needed
        if use_standard_values:
            for attr, value in self.default_values.items():
                data[attr] = self.default_values[attr]

        for attr, value in data.items():
            
            # Standard properties just get added and maybe mapped, if needed
            if attr in self.standard_fields:
                if attr in self.field_map:
                    ac_data["contact"][self.field_map[attr]] = data[attr]
                else:
                    ac_data["contact"][attr] = data[attr]
            
            else:
                if attr in self.custom_fields:
                    ac_data["contact"]["fieldValues"].append({
                        "field": self.custom_fields[attr],
                        "value": Utilities().fixDataType(data[attr])
                    })

        return ac_data




    def createContact(self, data: json) -> Union[str, bool]:
        """
        Create AC Contact
        @param data <json>: Key-Value json of incoming form data

        @return contact_id <str> if successfull / False if failed attempt
        """    
        ac_data = self.__prepareDataForRequest(data)

        url = "%s/contacts" % (self.base_url)
        r = requests.post(url, data=json.dumps(ac_data), headers=self.headers)
        r_json = r.json()
        
        pprint("AC RESPONSE")

        if r.ok and "contact" in r_json:
            pprint("AC Contact Creation successfull")
            return r_json["contact"]["id"]

        elif 'errors' in r_json and r_json["errors"][0]["code"] == 'duplicate':
            existing_contact = self.searchForContact(ac_data["contact"]["email"])
            
            if existing_contact:
                pprint("AC Contact existed already.")
                return self.updateContact(existing_contact["id"], ac_data)

        else:
            pprint(r_json)
        
        return False





    def updateContact(self, contact_id: str, data: json, use_standard_values=True) -> Union[str, bool]:
        """
        Update AC Contact
        @param contact_id <str>: AC Contact ID
        @param use_standard_values <boolean>: Set properties like lead_status to standard values as defined in self.standard_values?

        @return contact_id <str> / False if failed attempt
        """
        ac_data = self.__prepareDataForRequest(data, use_standard_values=use_standard_values)

        url = "%s/contacts/%s" % (self.base_url, contact_id)
       
        r = requests.put(url, data=json.dumps(ac_data), headers=self.headers)
        r_json = r.json()

        if r.ok and "contact" in r_json:
            pprint("AC Contact updated successfully.")
            return r_json["contact"]["id"]

        pprint(r_json)
        return False






    def searchForContact(self, email: str) -> Union[str, bool]:
        """
        Search for AC Contact
        @param email <str>: email to look for in AC

        @return contact <json> if successfull / False if failed attempt
        """
        url = "%s/contacts?email=%s" % (self.base_url, email)

        r = requests.get(url, headers=self.headers)
        r_json = r.json()

        if r.ok and "contacts" in r_json and len(r_json["contacts"]) > 0:
            pprint("AC Contact found.")
            return r_json["contacts"][0]
        
        pprint("AC Contat not found.")
        return False





    def addContactToList(self, contact_id: str, list_name: str) -> Union[str, bool]:
        """
        Add a contact to a list
        @param contact_id <str>: AC Contact ID
        @param list_name <str>: AC List ID

        @return False
        """
        url = "%s/contactLists" % (self.base_url)

        data = {
            "contactList": {
                "list": self.lists[list_name],
                "contact": contact_id,
                "status": "1" # 1: subscribed, 2: unsubscribed
            }
        }

        r = requests.post(url, headers=self.headers, data=json.dumps(data))
        r_json = r.json()

        if r.ok and "contactList" in r_json and "contacts" in r_json and len(r_json["contacts"]) > 0:
            pprint("AC List update successfull.")
            return r_json["contacts"][0]["id"]
        
        pprint("AC List update failed.")
        return False