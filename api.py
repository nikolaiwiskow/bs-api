import dataclasses
import json
from os import truncate
import flask
import requests
import logging

from pprint import pprint
from flask import request, jsonify, abort
from flask_cors import CORS, cross_origin

from hubspot import Hubspot
from airtable import Airtable
from active_campaign import ActiveCampaign
from setmore import Setmore
from slack import Slack
from messagebird import MessageBird
from utilities import Utilities
from config import BESTRONG_API_TOKEN

app = flask.Flask(__name__)
CORS(app)
app.config["DEBUG"] = True
#logging.basicConfig(filename='/var/log/apache2/bestrong_wsgi_api_logs.log', level=logging.DEBUG, format='%(asctime)s %(levelname)-8s %(message)s')




def authenticate(request):
    """
    Check for API Token. Will return a 403 error if api_token is incorrect.
    """
    api_token = request.args.get("api_token") if request.args.get("api_token") else False

    if not api_token or api_token != BESTRONG_API_TOKEN:
        abort(403)



@app.errorhandler(400)
def api_error(e):
    """
    Return formatted JSON for 400 errors
    """
    return jsonify(error=str(e)), 400


@app.route('/', methods=['GET'])
@cross_origin()
def home():
    authenticate(request)
    logging.info("hey")
    return '''<h1>BeStrong API</h1>
<p>Because we can.</p>'''











# LEAD
@app.route('/lead', methods=['POST'])
def lead_flow():
    print("New Lead Request")
    authenticate(request)
    data = json.loads(request.data) if request.data else False

    if data:
        at = Airtable()
        hs = Hubspot()
        ac = ActiveCampaign()
        slack = Slack()
        utils = Utilities()

        # SLACK MESSAGE
        slack_message = "Neuer Lead!\n%s %s\n%s\n%s" % (utils.valueOrEmptyString(data, 'firstname'), 
                                                        utils.valueOrEmptyString(data, 'lastname'), 
                                                        utils.valueOrEmptyString(data, 'email'), 
                                                        utils.valueOrEmptyString(data, 'lp_form_funnel'))
        slack.sendMessage('fitness-leads', slack_message)

        data["hs_lead_status"] = "OPEN"

        # HUBSPOT
        hs_contact_id = hs.createContact(data)
        hs_id = hs_contact_id if hs_contact_id else ""
        data["hs_id"] = hs_id

        # ACTIVE CAMPAIGN
        ac_contact_id = ac.createContact(data)
        ac.addContactToList(ac_contact_id, "Gratis Session")
        ac_id = ac_contact_id if ac_contact_id else ""
        data["ac_id"] = ac_id

        form_complete_dataset = json.loads(data["form_complete_dataset"])

        # LOOKUP USER LOCATION
        if "google_location_id" in data:
            user_location = utils.lookupGoogleAdsGeotarget(data["google_location_id"])
            form_complete_dataset["user_location"] = user_location

        # Remove redundancy
        form_complete_dataset.pop("lp_form___complete_dataset", None)
        data["form_complete_dataset"] = form_complete_dataset

        # AIRTABLE
        at_record_id = at.create('Leads', data)

        # AIRTABLE UPDATE WITH HS & AC ID's
        if at_record_id:
            pprint("Calls finished successfully.")
            return "Success"
        
        slack.sendMessage('fitness-dev-notifications', 'Lead Calls finished with errors.')
        abort(400, description="Failed to create Airtable Record")
    
    abort(400, description="Missing request data")












# SYNC AIRTABLE CHANES TO HS AND AC
@app.route('/resources/sync_airtable_changes', methods=['POST'])
@cross_origin(origins='https://airtable.com/developers/scripting')
def sync_data_from_airtable():
    authenticate(request)

    data = json.loads(request.data) if request.data else False
    
    if data and 'hs_id' in data and 'ac_id' in data:
        ac = ActiveCampaign()
        hs = Hubspot()

        ac_response = ac.updateContact(str(data['ac_id']), data, use_standard_values=False)
        hs_response = hs.updateContact(str(data['hs_id']), data)

        if ac_response and hs_response:
            return json.dumps("Success.")

    return abort(400, description="Something went wrong.")












# SYNC LEADSTATUS OLD
@app.route('/resources/sync_leadstatus', methods=['POST'])
def sync_leadstatus():
    authenticate(request)

    data = json.loads(request.data) if request.data else False

    if data and "email" in data and "lead_status" in data:
        response = False
        success_rate = 0

        # ACTIVE CAMPAIGN
        ac = ActiveCampaign()
        ac_contact = ac.searchForContact(data["email"])

        if ac_contact:
            ac_contact_id = ac.updateContact(ac_contact["id"], {"hs_lead_status": data["lead_status"]}, use_standard_values=False)

            if ac_contact_id:
                response = "ActiveCampaign Update successfull."
                success_rate += 1


        # AIRTABLE
        at = Airtable()
        at_record_id = at.searchRecord('Leads', 'email', data["email"])

        if at_record_id:
            at_response = at.updateRecord('Leads', at_record_id, {"hs_lead_status": data["lead_status"]})
       
            if at_response:
                response = response + " AirTable Update successfull."
                success_rate += 1

        # Handle partial failure
        if success_rate == 2:
            return "All updates finished successfully."
        else:
            return abort(400, description=response)

    else:
        abort(400, description="Missing or incomplete payload. Make sure to include 'email' and 'lead_status'")







@app.route('/resources/update_erstberatungsslots', methods=['GET'])
def update_erstberatungsslots():
    at = Airtable()
    sm = Setmore()
    truncate_successfull = at.truncate("Erstberatung-Slots")

    if truncate_successfull:
        coaches = at.getAllRecords("Coaches")

        setmore_staff_ids = [coach["fields"]["setmore_staff_id"] for coach in coaches]

        for id in Utilities().dedupArray(setmore_staff_ids):
            pprint("Pulling slots for staff id %s" % (id))
            sm.getSlotsForStaffNextXDays(id)

        return "Success."
    
    return abort(400, description="Truncate Table incomplete.")





@app.route('/contract_signed', methods=["POST"])
def contract_signed():
    authenticate(request)

    data = json.loads(request.data) if request.data else False

    if data and "client_email" in data:
        at = Airtable()

        at_lead = at.searchRecord('Leads', "email", data["client_email"], return_full_record=True)

        # Select Coach. If ptd_coach is set, it will trump the person who held the Erstberatung
        if len(at_lead['fields']['ptd_coach']) > 0:
            at_coach = at.getRecord('Coaches', at_lead['fields']['ptd_coach'][0])
        else:
            at_coach = at.getRecord('Coaches', at_lead["fields"]["Coach (from Appointments)"][0])

        at.updateRecord('Leads', at_lead["id"], {
            "hs_lead_status": "WON",
            "contract_status": data["contract_status"]
        })

        return json.dumps({
            "coach_email": at_coach["fields"]["Email"],
            "ptd_package": at_lead["fields"]["ptd_package"],
            "gender": at_lead["fields"]["gender"]
        })

    return abort(400, description="Missing data. Make sure 'client_email' is in Body.")




"""
HUBSPOT
"""
@app.route('/resources/hubspot_contact', methods=['GET', 'POST'])
def hs_contact():
    authenticate(request)

    hs = Hubspot()

    # GET METHODS
    if request.method == 'GET':
        if request.args.get('email'):
            return hs.getContactByEmail(request.args.get('email'))

        elif request.args.get('id'):
            return hs.getContactById(request.args.get('id'))

        return "Missing argument 'email' or 'id'. Couldn't fetch contact."

    # POST METHOD
    elif request.method == 'POST':
        data = json.loads(request.data) if request.data else False

        if data:
            return hs.createContact(data)

        return "Missing data. Couldn't create contact."









"""
MESSAGEBIRD
"""
@app.route('/resources/messagebird_reply', methods=['POST'])
def messagebird_reply():
    authenticate(request)

    data = json.loads(request.data) if request.data else False

    if data and "conversationId" in data and "message_text" in data and "payload" in data:
        mb = MessageBird()
        response = mb.replyToConversation(data["conversationId"], data["message_text"], data["payload"])
        return response

    else:
        abort(400, description="Missing payload. Make sure to include conversationId and message_text in request body.")






"""
AIRTABLE
"""
@app.route('/resources/airtable_record', methods=['GET', 'POST'])
def airtable_record():
    authenticate(request)

    at = Airtable()

    if request.method == 'GET':
        if request.args.get('search_field') and request.args.get('search_value') and request.args.get('table'):
            record_id =  at.searchRecord(request.args.get('table'), request.args.get('search_field'), request.args.get('search_value'))

            if record_id:
                return record_id
            else:
                return "No record found."

        else:
            abort(400, description="Missing query parameters. Make sure to include 'search_field', 'search_value' and 'table'")


    elif request.method == 'POST':
        data = json.loads(request.data) if request.data else False

        if data and request.args.get('table'):
            return at.create(request.args.get('table'), data)

        return "Missing data. Couldn't create Airtable record."














@app.route('/resources/airtable_appointment', methods=['GET', 'POST'])
def airtable_appointment():
    authenticate(request)

    at = Airtable()

    # GET
    if request.method == 'GET':
        search_field = request.args.get('search_field')
        search_value = request.args.get('search_value')

        if search_field and search_value:
            record_id =  at.searchRecord('Appointments', search_field, search_value)

            if record_id:
                return record_id
            else:
                return "No record found."

        else:
            abort(400, description="Missing query parameters. Make sure to include 'search_field', 'search_value' and 'table'")


    # POST
    elif request.method == 'POST':
        data = json.loads(request.data) if request.data else False

        if data:
            setmore_staff_id = data["setmore_staff_id"] if "setmore_staff_id" in data else ""
            client_email = data['client_email'] if "client_email" in data else ""

            coach_id = at.searchRecord('Coaches', 'setmore_staff_id', setmore_staff_id)
            lead_id = at.searchRecord('Leads', 'email', client_email)

            if coach_id:
                data["Coach"] = [coach_id]

            if lead_id:
                data['Leads'] = [lead_id]
            
            return at.create('Appointments', data)

        return "Missing data. Couldn't create Airtable record."













@app.route('/resources/airtable_update', methods=['POST'])
def airtable_update():
    authenticate(request)

    data = json.loads(request.data) if request.data else False
    search_field = request.args.get('search_field')
    search_value = request.args.get('search_value')
    table_name = request.args.get('table')

    if data and search_field and search_value and table_name:
        at = Airtable()
        record_id = at.searchRecord(table_name, search_field, search_value)
        
        if record_id and "fields" in data:
            return at.updateRecord(table_name, record_id, data["fields"])

    else:
        return abort(400, description="Missing query parameters or payload. Make sure to include 'search_field', 'search_value' and 'table' as query params, as well as JSON payload with fields to update.")

    return "Airtable update failed. 'email' and 'fields' required in payload."







"""
ACTIVE CAMPAIGN
"""
@app.route('/resources/ac_contact', methods=['POST'])
def ac_lead():
    authenticate(request) 

    data = json.loads(request.data) if request.data else False

    if data:
        ac = ActiveCampaign()
        contact_id = ac.createContact(data)

        return ac.addContactToList(contact_id, "Gratis Session")

    return "Missing data. Couldn't create AC record."





"""
SLACK 
"""
@app.route('/resources/slack_message', methods=['POST'])
def slack_message():
    authenticate(request)  

    data = json.loads(request.data) if request.data else False

    if data:
        slack = Slack()
        return slack.sendMessage(data['channel'], data['message'])

    return "Missing payload: requiring channel & message properties in JSON object."




if __name__ == '__main__':
    app.run()