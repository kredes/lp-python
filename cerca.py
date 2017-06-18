import argparse
import ast
import copy
from math import radians, cos, sin, asin, sqrt
import re
import unicodedata
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

def remove_accents(s):
    return ''.join((c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn'))

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

def print_result():
    pass

class Station(object):

    def __init__(self, id, latitude, longitude, address, slots, bikes):
        self.id = id
        self.latitude = latitude
        self.longitude = longitude
        self.address = address
        self.slots = slots
        self.bikes = bikes

class InterestPoint(object):

    def __init__(self, name, long_description, short_description,
                 address, district, barri, longitude, latitude):
        self.name = name
        self.long_description = long_description
        self.short_description = short_description
        self.address = address
        self.location = '{};{};{}'.format(address, district, barri)
        self.longitude = longitude
        self.latitude = latitude

    def matches(field, query):
        field_value = None

        if field == 'name':
            field_value = self.name
        elif field == 'content':
            field_value = self.long_description
        elif field == 'location':
            field_value = self.location
        else:
            return None

        return re.search(query, remove_accents(field_value), re.IGNORECASE)


class Finder(object):



    def __init__(self, language='cat'):
        self.language = language
        self.SELECTED_LANG_URL = Finder.LANG_URLS[language]
        self.stations = None
        self.interest_points = None

    def parse_xml(self):
        with urllib.request.urlopen(STATIONS_DATA_URL) as req:
            root = ET.parse(req.read()).getroot()
            self.stations =

    def search(self, query, field=None):
        pass


class Evaluator(object):

    STATIONS_DATA_URL = 'http://wservice.viabicing.cat/v1/getstations.php?v=1'

    LANG_URLS = {
        'cat': 'http://www.bcn.cat/tercerlloc/pits_opendata.xml',
        'es' : 'http://www.bcn.cat/tercerlloc/pits_opendata_es.xml',
        'en' : 'http://www.bcn.cat/tercerlloc/pits_opendata_en.xml',
        'fr' : 'http://www.bcn.cat/tercerlloc/pits_opendata_fr.xml'
    }

    SELECTED_LANG_URL = None

    def __init__(self, language='cat'):
        self.SELECTED_LANG_URL = Finder.LANG_URLS[language]

        # Stations data
        with urllib.request.urlopen(STATIONS_DATA_URL) as req:
            root = ET.parse(req.read()).getroot()
            self.stations = None

        # Interest points data
        with urllib.request.urlopen(SELECTED_LANG_URL) as req:
            root = ET.parse(req.read()).getroot()
            self.points = None


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
        result = []
        for q in query:
            tmp = self.evaluate(q):
            result.extend(tmp)

        return result

    # Conjuncions
    def evaluate_tuple(self, query):
        result = []
        for q in query:
            tmp = self.evaluate(q)
            if not tmp:
                return []
            result.extend(tmp)

        return result

    # Més conjuncions
    def evaluate_dict(self, query):
        result = []
        for field, q in query.items():
            tmp = self.evaluate_string(q, field)
            if not tmp:
                return []
            result.extend(tmp)

        return result

    def evaluate_string(self, query, field=None):
        if field is None:
            return [s for s in self.points if s.matches('name', query) or s.matches('location', query))]
        elif field == 'name':
            return [s for s in self.points if s.matches('name', query)]
        elif field == 'location':
            return [s for s in self.points if s.matches('location', query)]
        elif field == 'content':
            return [s for s in self.points if s.matches('content', query)]
        else:
            return []



if __name__ == "__main__":
    args = parser.parse_args()

    try:
        query = ast.literal_eval(args.key)

        searcher = Finder(query.lan)
        evaluator = Evaluator(searcher)

        print_result(evaluator.evaluate(query))
    except:
        print('Error: Invalid value for argument --key')
