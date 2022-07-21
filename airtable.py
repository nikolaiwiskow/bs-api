from sys import float_repr_style
import requests
import json
import logging

from pprint import pprint
from typing import Union

from utilities import Utilities

#logging.basicConfig(filename='api.log', level=logging.DEBUG)

class Airtable():

    def __init__(self):
        self.project_id = "applnNCLOId0ZsBOv"
        self.base_url = "https://api.airtable.com/v0/%s/" % (self.project_id)
        self.api_key = "keyXEGb8jeZPIM83r"
        self.headers = {
            "Authorization": "Bearer %s" % (self.api_key),
            "Content-Type": "application/json"
        }
        self.allowed_fields = {
            "Leads": ["firstname", 
                        "lastname", 
                        "email", 
                        "phone", 
                        "hs_id", 
                        "ac_id", 
                        "form_complete_dataset", 
                        "hs_lead_status",
                        "funnel",
                        "campaign_last_click",
                        "messagebird_conversation_id"],
            "Appointments": ["setmore_id", "setmore_service_id", "setmore_service_name", "Coach", "appointment_time", "client_name", "client_email", "Leads", "meeting_url"]
        }
        self.field_map = {
            "form_complete_dataset": "form_data",
        }
        self.dont_json_stringify = ["Coach", "Leads"]
        





    def createRecord(self, table_name: str, data: json) -> Union[str, bool]:
        """
        Create Airtable Record
        @param data <json>: Key-Value map of data to create record from
        @param table_name <str>: Name of the Airtables Table

        @return record_id <str> if successfull / False it attempt failed
        """
        record = {}
        utils = Utilities()

        for attribute,value in data.items():
            if attribute in self.allowed_fields[table_name]:
                if attribute in self.field_map:
                    # Apply custom column names for Airtable
                    record[self.field_map[attribute]] = utils.fixDataType(data[attribute])

                elif attribute in self.dont_json_stringify:
                    # Pass through data directly for certain columns
                    record[attribute] = data[attribute]
                
                else:
                    # We'll json_dumps the rest
                    record[attribute] = utils.fixDataType(data[attribute])

        at_data = {
            "records": [{"fields": record}]
        }

        r = requests.post(self.base_url + table_name, data=json.dumps(at_data), headers=self.headers)
        r_json = r.json()

        print("AIRTABLE-RESPONSE")

        if r.ok and "records" in r_json and len(r_json["records"]) > 0:
            pprint("AirTable Create Record created successfully.")
            return r_json["records"][0]["id"]

        pprint("AirTable Create Record failed!")
        pprint(r.text)
        return False




    def updateRecord(self, table_name: str, record_id: str, data: json) -> Union[str, bool]:
        """
        Update Airtable Record
        @param table_naem <str>: Airtbable Table name
        @param record_id <str>: Airtable record id
        @param data <json>: Key-Value map of fields to update

        @return record_id <str> / False if failed attempt
        """
        at_data = {
            "records": [
                {
                    "id": record_id,
                    "fields": data
                }
            ]
        }

        r = requests.patch(self.base_url + table_name, data=json.dumps(at_data), headers=self.headers)
        r_json = r.json()

        if r.ok and "records" in r_json and len(r_json["records"]) > 0:
            pprint("AirTable Update Record successfull.")
            return r_json["records"][0]["id"]

        pprint("AirTable Update Record failed!")
        pprint(r.text)
        return False




    def searchRecord(self, table_name: str, search_field: str, search_value: str) -> Union[str, bool]:
        """
        Search for Airtable Record by field & value
        @param table_name <str>: Airtable Table name
        @param search_field <str>: The field / column we want to filter for with search_value
        @param search_value <str>: The value we'll filter the field / clumn search_field by

        @return record_id <str> / False if failed attempt
        """
        url = "%s?fields[]=%s&maxRecords=1&filterByFormula=SEARCH(LOWER('%s'), %s)" % (self.base_url + table_name, search_field, search_value, search_field)

        r = requests.get(url, headers=self.headers)
        r_json = r.json()
        
        if r.ok and "records" in r_json and len(r_json["records"]) > 0:
                return r_json["records"][0]["id"]
        
        pprint("No records found.")
        return False