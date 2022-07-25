import pprint
import json



class Utilities():
    

    def fixDataType(self, input) -> str:
        """
        typecast data as to upload it safely to various api's
        @param input <any>

        return <str> typecast data
        """
        if type(input) is str:

            # Lower case emails
            if input.find("@") > 0:
                return str(input.lower())

            return str(input)
        
        return json.dumps(input)



    def valueOrEmptyString(self, json_dict: dict, key_to_check: str) -> str:
        """
        @param json_dict <dict>: Object to retrieve value from
        @param key_to_check <str>: key of object, whose value we want
        
        @return value of key in obj or empty string, if key not present in object
        """
        return json_dict[key_to_check] if key_to_check in json_dict else ""





    def chunkArray(self, lst: list, n: int) -> list:
        """
        Yield successive n-sized chunks from lst.
        @param lst <list>: the array to chunk into pieces
        @param n <int>: size of individual chunks

        @return 2d array of chunks
        """
        for i in range(0, len(lst), n):
            yield lst[i:i + n]


    
    def dedupArray(self, lst: list) -> list:
        """
        Deduplicate an array
        @param lst <list>: The list to deduplicate

        @return <list> deduplicated list
        """
        return list(dict.fromkeys(lst))