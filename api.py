import dataclasses
import json
import flask
import requests
import logging

from pprint import pprint
from flask import request, jsonify, abort

from hubspot import Hubspot
from airtable import Airtable
from active_campaign import ActiveCampaign
from slack import Slack
from config import BESTRONG_API_TOKEN

app = flask.Flask(__name__)
app.config["DEBUG"] = True
logging.basicConfig(filename='api_logs.log', level=logging.DEBUG, format='%(asctime)s %(levelname)-8s %(message)s')




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
def home():
    authenticate(request)
    logging.info("hey")
    return '''<h1>BeStrong API</h1>
<p>Because we can.</p>'''





# LEAD
@app.route('/lead', methods=['POST'])
def lead_flow():
    print("New Lead Request")
    data = json.loads(request.data) if request.data else False
    authenticate(request)

    if data:
        at = Airtable()
        hs = Hubspot()
        ac = ActiveCampaign()
        slack = Slack()

        data["hs_lead_status"] = "OPEN"
        # AIRTABLE
        at_record_id = at.createRecord('Leads', data)

        # HUBSPOT
        hs_contact_id = hs.createContact(data)


        # SLACK MESSAGE
        firstname = data["firstname"] if "firstname" in data else ""
        lastname = data["lastname"] if "lastname" in data else ""
        email = data["email"] if "email" in data else ""
        funnel = data["lp_form___funnel"] if "lp_form___funnel" in data else ""
        slack_message = "Neuer Lead!\n%s %s\n%s\n%s" % (firstname, lastname, email, funnel)
        slack.sendMessage('fitness-leads', slack_message)


        at_id = at_record_id if at_record_id else ""
        hs_id = hs_contact_id if hs_contact_id else ""

        data["hs_id"] = hs_id
        data["at_id"] = at_id

        # ACTIVE CAMPAIGN
        ac_contact_id = ac.createContact(data)
        ac.addContactToList(ac_contact_id, "Gratis Session")

        ac_id = ac_contact_id if ac_contact_id else ""

        # AIRTABLE UPDATE WITH HS & AC ID's
        if at_record_id and (hs_contact_id or ac_contact_id):
            at_updated_record = at.updateRecord('Leads', at_record_id, {
                    "ac_id": ac_contact_id,
                    "hs_id": hs_id
                })

            logging.info("Calls finished successfully.")
            return "Success"
        
        logging.error("Calls finished with Errors!")
        logging.info("AirTable Response")
        logging.info("Airtable Record Id: %s" & (at_record_id))
        logging.info("Hubspot Response")
        logging.info("Hubspot Contact Id: %s" % (hs_contact_id))
        logging.info("ActiveCampaign Response")
        logging.info("ActiveCampaign Contact Id: %s" % (ac_contact_id))
        slack.sendMessage('fitness-dev-notifications', 'Lead Calls finished with errors.')
        abort(400, description="Failed API Call in execution chain")
    
    abort(400, description="Missing request data")





# SYNC LEADSTATUS
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
            return at.createRecord(request.args.get('table'), data)

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
            
            return at.createRecord('Appointments', data)

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