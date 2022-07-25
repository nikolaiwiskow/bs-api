import requests
import json
import datetime

from pprint import pprint
from typing import Union

from config import CONFIG

from airtable import Airtable


class Setmore():

    def __init__(self):
        self.refresh_token = CONFIG["setmore"]["refresh_token"]
        self.base_url = "https://developer.setmore.com/api/v1"
        self.access_token = self.__getAccessToken()
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer %s" % (self.access_token)
        }



    def __getAccessToken(self) -> Union[str, bool]:
        url = "%s/o/oauth2/token?refreshToken=%s" % (self.base_url, self.refresh_token)

        r = requests.get(url)
        r_json = r.json()

        if r.ok and "response" in r_json and r_json["response"]:
            access_token = r_json["data"]["token"]["access_token"]
            return access_token

        pprint("AccessToken not retrieved.")
        return False





    def getSlotsForStaff(self, staff_id: str, date=False, service_id="s7573f8594d854246a60e9ed2809816552dcb0b48") -> list:
        """
        @param staff_id <str>: Setmore Staff Id
        @param date <str>: Date in the format "23/06/1988"
        @param service_id <str>: Setmore Service ID

        @return slots <list>.<obj> or False
        """
        url = "%s/bookingapi/slots" % (self.base_url)

        date_for_call = date or datetime.date.today()
        date_api_format = date_for_call.strftime('%d/%m/%Y')

        staff_airtable_record_id = Airtable().searchRecord('Coaches', 'setmore_staff_id', staff_id)

        timeslot_length = 60
        
        data = {
            "staff_key": staff_id,      
            "service_key": service_id,    
            "selected_date": date_api_format,
            "off_hours": False,
            "double_booking" : False,
            "slot_limit" : timeslot_length,
            "timezone"   : "UTC"
        }

        r = requests.post(url, data=json.dumps(data), headers=self.headers)
        r_json = r.json()
    
        if r.ok and "response" in r_json and r_json["response"]:
            staff_slots = []

            for slot in r_json["data"]["slots"]:
                slot_datetime = "%sT%s:00.000Z" % (date_for_call.strftime('%Y-%m-%d'), slot.replace(".", ":"))
                staff_slots.append({
                    "setmore_staff_id":  staff_id,
                    "timeslot": slot_datetime ,
                    "Coach": [staff_airtable_record_id],
                    "timeslot_length": timeslot_length
                })

            return staff_slots
        
        pprint("Failed to retrieve slots for %s" % (date_api_format))
        return False





    def getSlotsForStaffNextXDays(self, staff_id: str, service_id="s7573f8594d854246a60e9ed2809816552dcb0b48", days=14) -> list:
        """
        Get available timeslots for staff & service from Setmore
        @staff_id <str>: The setmore staff id
        @service_id <str> (optional): The setmore service id, else we'll pull slots for Erstberatung
        @days <int> (optional): The number of days we want to go into the future. Default: 14

        @return <list>.<obj> slots
        """
        date_today = datetime.date.today()
        slots = []

        for i in range(0, days):
            dt = date_today + datetime.timedelta(i)
            slots_of_day = self.getSlotsForStaff(staff_id, date=dt, service_id=service_id)
            for s in slots_of_day:
                slots.append(s)
            
        Airtable().create("Erstberatung-Slots", slots)

        return slots