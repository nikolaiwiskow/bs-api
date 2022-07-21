import pprint
import json



class Utilities():
    
    """
    Post a message to slack
    """
    def fixDataType(self, input):
        if type(input) is str:

            # Lower case emails
            if input.find("@") > 0:
                return str(input.lower())

            return str(input)
        
        return json.dumps(input)



    def valueOrEmptyString(self, json_dict: dict, key_to_check: str) -> str:
        return json_dict[key_to_check] if key_to_check in json_dict else ""

