"""
Freebase utils.

@author: Krisztian Balog
"""


class FreebaseUtils(object):
    
    @staticmethod
    def freebase_id_to_uri(freebase_id):
        """Translate Freebase ID to (prefixed) Freebase URI. 
        For example, '/m/02_286' => '<fb:m.02_286>'
        """
        if freebase_id.startswith("/m/"):
            return "<fb:m." + freebase_id[3:] + ">"
        else:
            raise Exception("Invalid Freebase ID")

    @staticmethod
    def freebase_uri_to_id(freebase_uri):
        """Translate (prefixed) Freebase URI to Freebase ID. 
        For example, '<fb:m.02_286>' => '/m/02_286' 
        """
        if freebase_uri.startswith("<fb:m."):
            return "/m/" + freebase_uri[6:-1]
        else:
            raise Exception("Invalid Freebase URI")


def main():
    # example usage    
    print FreebaseUtils.freebase_id_to_uri("/m/02_286")
    print FreebaseUtils.freebase_uri_to_id("<fb:m.02_286>")
            
if __name__ == "__main__":
    main()