import argparse
import ast
from math import radians, cos, sin, asin, sqrt
import urllib.request
import xml.etree.ElementTree as ET


parser = argparse.ArgumentParser()
parser.add_argument(
    '--lan', type=str,
    help='Specifies the language of the result',
    nargs='?', const='cat', default='cat',
    choices=['cat', 'es', 'en', 'fr'])
parser.add_argument(
    '--key', type=str,
    help='A query',
    nargs='?', const=None, default=None)

def print_result():
    pass

class Finder(object):

    STATIONS_DATA_URL = 'http://wservice.viabicing.cat/v1/getstations.php?v=1'

    LANG_URL_MAP = {
        'cat': '',
        'es' : '',
        'en' : '',
        'fr' : ''
    }

    SELECTED_LANG_URL = None

    def __init__(self, language='cat'):
        self.language = language
        self.SELECTED_LANG_URL = Finder.LANG_URL_MAP[language]
        self.station_data = None
        self.lang_data = None

    def haversine(lon1, lat1, lon2, lat2):
        """
        Calculate the great circle distance between two points
        on the earth (specified in decimal degrees)
        """
        # convert decimal degrees to radians
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        # haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        meters = 6367 * c * 1000

        return meters

    def parse_xml(self):
        with urllib.request.urlopen(url) as req:
            self.station_data = ET.parse(req.read())

    def search(self, query, field=None):
        pass


class Evaluator(object):

    def __init__(self, finder=Finder()):
        self.finder = finder

    # Generic
    def evaluate(self, query):
        if isinstance(query, list):
            return self.evaluate_list(query)
        elif isinstance(query, tuple):
            return self.evaluate_tuple(query)
        elif isinstance(query, dict):
            return self.evaluate_dict(query)
        elif isinstance(query, str):
            return self.evaluate_string(query)
        else:
            return False

    # Disjuncions
    def evaluate_list(self, query):
        for q in query:
            if self.evaluate(q):
                return True
        return False

    # Conjuncions
    def evaluate_tuple(self, query):
        for q in query:
            if not self.evaluate(q):
                return False
        return True

    # Més conjuncions
    def evaluate_dict(self, query):
        for field, q in query.items():
            if not self.finder.search(q, field):
                return False
        return True

    def evaluate_string(self, query):
        return self.finder.search(query)

    def get_result():
        return 'Dummy'


if __name__ == "__main__":
    args = parser.parse_args()

    try:
        query = ast.literal_eval(args.key)

        searcher = Finder(query.lan)
        evaluator = Evaluator(searcher)

        evaluator.evaluate(query)

        print_result(evaluator.get_result())
    except:
        print('Error: Invalid value for argument --key')
