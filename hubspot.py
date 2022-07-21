import requests
import json
import re
import logging

from pprint import pprint
from typing import Union

from utilities import Utilities

#logging.basicConfig(filename='var/www/bestrong_api/bestrong_api.log', level=logging.DEBUG)

class Hubspot():

    def __init__(self):
        self.base_url = "https://api.hubapi.com/crm/v3"
        self.api_token = "ef13d414-88b8-4adc-89e1-d6e4f019b62c"
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        self.allowed_properties = ["firstname", 
                                    "lastname", 
                                    "email", 
                                    "phone", 
                                    "hs_lead_status", 
                                    "lifecyclestage", 
                                    "form_complete_dataset",
                                    "funnel", 
                                    "campaign_last_click", 
                                    "salutation",
                                    "hs_google_click_id", 
                                    "hs_facebook_click_id"]

        self.additional_properties = "firstname,lastname,email,phone,hs_lead_status,salutation,lifecyclestage,lp_form___complete_dataset,lp_form___funnel"
        self.field_map = {
            "funnel": "lp_form___funnel",
            "campaign_last_click": "campaign___last_click",
            "form_complete_dataset": "lp_form___complete_dataset"
        }
    



    def getContactByEmail(self, email: str) -> Union[str, bool]:
        url = "%s/objects/contacts/search?hapikey=%s&properties=%s" % (self.base_url, self.api_token, self.additional_properties)

        body = {
        "filterGroups":[
                {
                    "filters":[
                        {
                            "propertyName": "email",
                            "operator": "EQ",
                            "value": email
                        }
                    ]
                }
            ]
        }

        r = requests.post(url, data=json.dumps(body), headers=self.headers)

        if r.ok:
            r_json = r.json()

            if r_json["total"] > 0:
                return r_json["results"][0]
            else:
                return False


        return r.text





    
    def getContactById(self, id: str) -> Union[str, bool]:
        """
        Retrieve a hubspot contact by id
        @param id <str>: Hubspot Contact ID

        @return r_json <json>: JSON Response Object with Contact properties
        """
        url = "%s/objects/contacts/%s?hapikey=%s&properties=%s" % (self.base_url, id, self.api_token, self.additional_properties)

        r = requests.get(url, headers=self.headers)
        r_json = r.json()

        # If successfull
        if r.ok and "properties" in r_json:
            return r_json
        
        pprint(r_json)
        return False


    def __prepareDataForRequest(self, data: json) -> json:
        hs_data = {
            "properties": {}
        }
        
        utils = Utilities()

        # Only pass through allowed values
        for attribute, value in data.items():
            if attribute in self.allowed_properties:
                if attribute in self.field_map:
                    hs_data["properties"][self.field_map[attribute]] = utils.fixDataType(data[attribute])
                else:
                    hs_data["properties"][attribute] = utils.fixDataType(data[attribute])

        return hs_data




    def createContact(self, data: json) -> Union[str, bool]:
        """
        Create a hubspot contact or update it
        @param data <json>: Key-Value JSON Object with form data

        @return contact_id <str> if successfull / False if attempt failed
        """

        url = "%s/objects/contacts?hapikey=%s" % (self.base_url, self.api_token)
  
        hs_data = self.__prepareDataForRequest(data)

        r = requests.post(url, data=json.dumps(hs_data), headers=self.headers)
        r_json = r.json()

        pprint("HUBSPOT RESPONSE")

        if r.ok and "id" in r_json:
            pprint("Hubspot Contact created succesfully.")
            return r_json["id"]

        else:
            if r_json["status"] == 'error' and r_json["category"] == 'CONFLICT':
                regex = r"\d+"
                # Contact ID is written in message property, so we'll get it from there
                contact_id = re.search(regex, r_json["message"]).group()

                if contact_id:
                    return self.updateContact(contact_id, data)
            
                pprint("HubSpot Conflict Error - no contact_id provided.")
                return False
    
            pprint("Hubspot Contact creation failed!")
            return False





    def updateContact(self, contact_id: str, data: json) -> Union[str, bool]:   
        """
        Update a hubspot contact
        @param contact_id <str>: Hubspot Contact ID
        @param hs_data <json>: JSON Object of properties to update the contact with

        @return contact_id <str> if successfull / False if attempt failed
        """
        url = "%s/objects/contacts/%s?hapikey=%s" % (self.base_url, contact_id, self.api_token)

        hs_data = self.__prepareDataForRequest(data)

        r = requests.patch(url, data=json.dumps(hs_data), headers=self.headers)
        r_json = r.json()

        if r.ok and "id" in r_json:
            pprint("HubSpot Contact successfully updated.")
            return r_json["id"]
    
        pprint("HubSpot Contact update failed.")
        return False