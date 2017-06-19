import argparse
import ast
import html
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


def get_text(xml_elem):
    return '' if xml_elem is None else ''.join(xml_elem.itertext())


def print_point(point, long_description=False):
    description = point.long_description if long_description else point.short_description
    print('Name: ', point.name)
    print('Address: ', point.address)
    print('Description: ', description)
    print('Nearest stations with free slots: ')
    for station, distance in point.near_slots_stations:
        print('\t{} -- {} slots ({} meters)'.format(station.address, station.slots, distance, station.slots))
    print('Nearest stations with available bikes: ')
    for station, distance in point.near_bikes_stations:
        print('\t{} -- {} bikes ({} meters)'.format(station.address, station.bikes, distance))
    print('------------------------------------------------\n')


def remove_p(s):
    res = s
    if res.startswith('<p>'):
        res = res[len('<p>'):]
    if res.endswith('</p>'):
        res = res[:-len('</p>')]

    return res


class Station(object):

    def __init__(self, id, latitude, longitude, address, slots, bikes):
        self.id = id
        self.latitude = latitude
        self.longitude = longitude
        self.address = address
        self.slots = slots if isinstance(slots, int) else 0
        self.bikes = bikes if isinstance(bikes, int) else 0




class InterestPoint(object):

    def __init__(self, name, long_description, short_description,
                 address, district, barri, latitude, longitude):
        self.name = name
        self.long_description = remove_p(long_description)
        self.short_description = remove_p(short_description)
        self.address = address
        self.location = '{};{};{}'.format(address, district, barri)
        self.longitude = longitude
        self.latitude = latitude
        self.near_slots_stations = []   # List of tuples (station, distance to this point)
        self.near_bikes_stations = []    # List of tuples (station, distance to this point)

    def matches(self, field, query):
        if field == 'name':
            field_value = self.name
        elif field == 'content':
            field_value = self.long_description
        elif field == 'location':
            field_value = self.location
        else:
            return None

        return re.search(query, remove_accents(field_value), re.IGNORECASE)

    def add_near_slot_station(self, station, distance):
        self.near_slots_stations.append((station, distance))

    def add_near_bike_station(self, station, distance):
        self.near_bikes_stations.append((station, distance))

    def sort_stations(self):
        self.near_slots_stations.sort(key=lambda pair: pair[0].slots, reverse=True)
        self.near_bikes_stations.sort(key=lambda pair: pair[0].bikes, reverse=True)


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
        self.SELECTED_LANG_URL = Evaluator.LANG_URLS[language]

        self.stations = []
        self.points = []

        # Stations data
        with urllib.request.urlopen(Evaluator.STATIONS_DATA_URL) as req:
            root = ET.fromstring(req.read())

            for child in root.findall('./station'):
                s = Station(
                    get_text(child.find('id')),
                    float(get_text(child.find('lat'))),
                    float(get_text(child.find('long'))),
                    html.unescape('{}, {}'.format(
                        get_text(child.find('street')),
                        get_text(child.find('streetNumber'))
                    )),
                    int(get_text(child.find('slots'))),
                    int(get_text(child.find('bikes')))
                )
                self.stations.append(s)

        # Interest points data
        with urllib.request.urlopen(self.SELECTED_LANG_URL) as req:
            root = ET.fromstring(req.read())
            for child in root.findall('./list_items/row'):
                address = child.find('./addresses/item')
                p = InterestPoint(
                    get_text(child.find('name')),
                    get_text(child.find('content')),
                    get_text(child.find('./custom_fields/descripcio-curta-pics')),
                    get_text(address.find('address')),
                    get_text(address.find('district')),
                    get_text(address.find('barri')),
                    float(get_text(address.find('gmapx'))),    # Latitude
                    float(get_text(address.find('gmapy')))     # Longitude
                )
                self.points.append(p)

        for point in self.points:
            for station in self.stations:
                distance = haversine(point.longitude, point.latitude, station.longitude, station.latitude)
                if distance <= 500:
                    if station.slots > 0:
                        point.add_near_slot_station(station, distance)
                    if station.bikes > 0:
                        point.add_near_bike_station(station, distance)

            point.sort_stations()

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

    # Disjunctions
    def evaluate_list(self, query):
        result = []
        for q in query:
            tmp = self.evaluate(q)
            result.extend(tmp)

        return result

    # Conjunctions
    def evaluate_tuple(self, query):
        result = []
        for q in query:
            tmp = self.evaluate(q)
            if not tmp:
                return []
            result.extend(tmp)

        return result

    # More conjunctions
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
            return [s for s in self.points if s.matches('name', query) or s.matches('location', query)]
        elif field == 'name':
            return [s for s in self.points if s.matches('name', query)]
        elif field == 'location':
            return [s for s in self.points if s.matches('location', query)]
        elif field == 'content':
            return [s for s in self.points if s.matches('content', query)]
        else:
            return []


def elem_with_text(tag, text):
    elem = ET.Element(tag)
    elem.text = text
    return elem


def build_html(points):
    root = ET.Element('html')

    style = ET.Element('style')
    style.text = 'th, td { padding: 10px; }'
    root.append(style)

    table = ET.Element('table', {'border': 'true'})

    header = ET.Element('tr')
    for field in ('name', 'description', 'address', 'Nearest stations with free slots', 'Nearest stations with available bikes'):
        header.append(elem_with_text('th', field))
    table.append(header)

    long_description = len(points) == 1

    for point in points:
        description = point.long_description if long_description else point.short_description
        row = ET.Element('tr')
        row.append(elem_with_text('td', point.name))
        row.append(elem_with_text('td', description))
        row.append(elem_with_text('td', point.address))

        slots = ET.Element('td')
        for s, dist in point.near_slots_stations[:5]:
            #slots.append(elem_with_text('p', '&amp;'.encode('utf-8').decode('utf-8')))
            slots.append(elem_with_text('p', '{} ({} free slots, ~{} meters away)'.format(s.address, s.slots, int(dist))))

        bikes = ET.Element('td')
        for s, dist in point.near_bikes_stations[:5]:
            bikes.append(elem_with_text('p', '{} ({} available bikes, ~{} meters away)'.format(s.address, s.bikes, int(dist))))

        row.append(slots)
        row.append(bikes)

        table.append(row)

    root.append(table)

    return ET.tostring(root, encoding='us-ascii', method='html').decode('us-ascii')


if __name__ == "__main__":
    args = parser.parse_args()

    query = None
    try:
        query = ast.literal_eval(args.key)
    except Exception as e:
        print('Error: Invalid value for argument --key. Message:')
        print('\t{}'.format(e))

    evaluator = Evaluator(args.lan)

    #print_result(evaluator.evaluate(query))

    print(build_html(evaluator.evaluate(query)))

