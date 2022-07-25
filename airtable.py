from sys import float_repr_style
import requests
import json
import logging

from pprint import pprint
from typing import Union

from utilities import Utilities
from config import CONFIG

#logging.basicConfig(filename='api.log', level=logging.DEBUG)

class Airtable():

    def __init__(self):
        self.project_id = "applnNCLOId0ZsBOv"
        self.base_url = "https://api.airtable.com/v0/%s/" % (self.project_id)
        self.api_key = CONFIG["airtable"]["api_key"]
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
            "Appointments": ["setmore_id", "setmore_service_id", "setmore_service_name", "Coach", "appointment_time", "client_name", "client_email", "Leads", "meeting_url"],
            "Erstberatung-Slots": ["setmore_staff_id", "timeslot", "Coach", "timeslot_length"]
        }
        self.field_map = {
            "form_complete_dataset": "form_data",
        }
        self.dont_json_stringify = ["Coach", "Leads", "timeslot_length"]
        self.pagination_results = []
        





    def __prepRecord(self, record_data: object, table_name: str) -> object:
        record = {
            "fields": {}
        }
        utils = Utilities()

        for attribute,value in record_data.items():
            if attribute in self.allowed_fields[table_name]:
                if attribute in self.field_map:
                    # Apply custom column names for Airtable
                    record["fields"][self.field_map[attribute]] = utils.fixDataType(record_data[attribute])

                elif attribute in self.dont_json_stringify:
                    # Pass through data directly for certain columns
                    record["fields"][attribute] = record_data[attribute]
                
                else:
                    # We'll json_dumps the rest
                    record["fields"][attribute] = utils.fixDataType(record_data[attribute])    

        return record    




    def create(self, table_name: str, data: Union[list, object]) -> Union[str, bool]:
        if isinstance(data, list):
            records = []
            for item in data:
                records.append(self.__prepRecord(item, table_name))
            
            record_chunks = Utilities().chunkArray(records, 10)

            for chunk in record_chunks:
                self.createRecord(table_name, chunk)

            return True

        elif isinstance(data, object):
            return self.createRecord(table_name, [self.__prepRecord(data, table_name)])

        return []
        



    def createRecord(self, table_name: str, data: Union[list, object]) -> Union[str, bool]:
        """
        Create Airtable Record
        @param data <json>: Key-Value map of data to create record from
        @param table_name <str>: Name of the Airtables Table

        @return record_id <str> if successfull / False it attempt failed
        """
        at_data = {
            "records": data,
            "typecast": True
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



    def getAllRecords(self, table_name: str, fields=False, offset=False) -> list:
        """
        Return a list of all records in a table
        @param table_name <str>: Table Name
        @param fields <list>.<str>: List of fields to return

        @return <list>.<obj> list of Airtable Record Objects
        {   'createdTime': '2022-07-12T12:53:54.000Z',
            'fields':   {'Vorname': 'Linnea',
                        'record_id': 'recqK13qjTs50HLUh',
                        'setmore_staff_id': 'r3f251651666455574'},
            'id': 'recqK13qjTs50HLUh'
        }
        """

        url = "%s%s" % (self.base_url, table_name)

        if fields:
            query_params = ""
            for field in fields:
                query_params += "&fields=%s" % (field)
            
            url += query_params

        if offset:
            url += "&offset=%s" % (offset)

        url = url.replace("&", "?", 1)

        r = requests.get(url, headers=self.headers)
        r_json = r.json()

        if r.ok and "records" in r_json:
            self.pagination_results += r_json["records"]

            if "offset" in r_json:
                self.getAllRecords(table_name, fields=fields, offset=r_json["offset"])

            return self.pagination_results

        return []


    def truncate(self, table_name: str) -> bool:
        """
        Truncate a whole Table in Airtable
        @param table_name <str>: Table name

        @return pass
        """
        records = self.getAllRecords(table_name)
        record_ids = [record["id"] for record in records]
        chunks = Utilities().chunkArray(record_ids, 10)

        url = self.base_url + table_name

        for chunk in chunks:
            params = {
                "records[]": chunk
            }
            r = requests.delete(url, params=params, headers=self.headers)

            if not r.ok:
                pprint(r.json())
                return False

        return True