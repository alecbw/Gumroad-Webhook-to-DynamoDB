from utility.util import *

import os
import random
from datetime import datetime, timedelta
from urllib.parse import parse_qs
import logging
import time

import boto3
import requests

############################################################################################

"""
Both timestamps - the sale timestamp 'timestamp' and the write timestamp 'updatedAt' are UTC timezone-agnostics
"""
def lambda_handler(event, context):
    param_dict, missing_params = validate_params(event,
        required_params=["Secret_Key"],
        optional_params=[]
    )
    logging.info(event)
    if param_dict.get("Secret_Key") not in [os.environ["SECRET_KEY"], "export SECRET_KEY=" + os.environ["SECRET_KEY"]]:
        return package_response(f"Please authenticate", 403, warn="please auth")

    if os.getenv("DEBUG"): logging.info("You are now in debug mode. The Dynamo row will write, but the GA POST will be to the debug endpoint")


    # parse_qs writes every value as a list, so we subsequently unpack those lists
    webhook_data = parse_qs(event["body"])
    webhook_data = {k:v if len(v)>1 else v[0] for k,v in webhook_data.items()}

    timestamp = datetime.strptime(webhook_data.pop("sale_timestamp").replace("T", " ").replace("Z", ""), "%Y-%m-%d %H:%M:%S")

    data_to_write = {
        "email": webhook_data.pop("email"),
        "timestamp": int(timestamp.timestamp()), # UTC Non-Adjusted
        "value": int(webhook_data.pop("price")), # you'll need to divide by 100 to get $$.¢¢, as the data as sent as xxxx
        "offer_code": webhook_data.pop("offer_code", "No Code"),
        "country": webhook_data.pop("ip_country", "Unknown"),
        "refunded": 1 if webhook_data.pop("refunded") in ["true", "True", True] else 0,
        "_ga": webhook_data.get("url_params[_ga]", ""),
        "data": webhook_data, # store the rest in a blob
        'updatedAt': int(datetime.utcnow().timestamp()), # UTC Non-Adjusted
    }

    write_dynamodb_item(data_to_write, "GRWebhookData")

    track_google_analytics_event(data_to_write)

    logging.info("Dynamo write and GA POST both appear to be successful")
    return package_response(f"Dynamo write and GA POST both appear to be successful", 200)


############################################################################################

""" 
If you don't provide geo, GA wrongly infers it from the Server's IP as US.
    We translate the GR ip_country to the GA shortcode, if possible
    If the param is missing or doesn't match, we return code: 99999999
    An invalid code will result in geographical dimensions to be set to '(not set)'.
    Docs: https://developers.google.com/analytics/devguides/collection/protocol/v1/parameters
"""
def convert_geo_code(country):
    geo_dict = {"Afghanistan": "AF","Angola": "AO","Anguilla": "AI","United Arab Emirates": "AE","Argentina": "AR","Antigua and Barbuda": "AG","Australia": "AU","Austria": "AT","Azerbaijan": "AZ","Belgium": "BE","Benin": "BJ","Bangladesh": "BD","Bulgaria": "BG","Bahrain": "BH","Belarus": "BY","Brazil": "BR","Barbados": "BB","Brunei": "BN","Canada": "CA","United Kingdom": "GB","Switzerland": "CH","Chile": "CL","China": "CN","Democratic Republic of the Congo": "CD","Colombia": "CO","Comoros": "KM","Costa Rica": "CR","Cayman Islands": "KY","Cyprus": "CY","Czechia": "CZ","Germany": "DE","Djibouti": "DJ","Dominica": "DM","Denmark": "DK","Dominican Republic": "DO","Algeria": "DZ","Ecuador": "EC","Egypt": "EG","Eritrea": "ER","Spain": "ES","Estonia": "EE","Ethiopia": "ET","Finland": "FI","Fiji": "FJ","France": "FR","Faroe Islands": "FO","Federated States of Micronesia": "FM","Gabon": "GA","Guernsey": "GG","Jersey": "JE","Georgia": "GE","Guadeloupe": "GP","Greece": "GR","Western Greece and the Ionian": "GR","Greenland": "GL","Guatemala": "GT","French Guiana": "GF","Guam": "GU","Guyana": "GY","Croatia": "HR","Haiti": "HT","Hungary": "HU","Indonesia": "ID","India": "IN","Ireland": "IE","Iraq": "IQ","Iceland": "IS","Israel": "IL","Italy": "IT","Apulia": "IT","Jamaica": "JM","Japan": "JP","Kazakhstan": "KZ","Kenya": "KE","Kyrgyzstan": "KG","Cambodia": "KH","Saint Kitts and Nevis": "KN","South Korea": "KR","Laos": "LA","Lebanon": "LB","Libya": "LY","Liechtenstein": "LI","Sri Lanka": "LK","Lithuania": "LT","Luxembourg": "LU","Latvia": "LV","Macao": "MO","Morocco": "MA","Moldova": "MD","Madagascar": "MG","Mexico": "MX","North Macedonia": "MK","Malta": "MT","Myanmar (Burma)": "MM","Mongolia": "MN","Northern Mariana Islands": "MP","Mozambique": "MZ","Martinique": "MQ","Mauritius": "MU","Malawi": "MW","Malaysia": "MY","Namibia": "NA","New Caledonia": "NC","Niger": "NE","Nigeria": "NG","Nicaragua": "NI","Netherlands": "NL","Norway": "NO","Nepal": "NP","New Zealand": "NZ","Pakistan": "PK","Panama": "PA","Peru": "PE","Philippines": "PH","Palau": "PW","Papua New Guinea": "PG","Poland": "PL","Puerto Rico": "PR","Portugal": "PT","Paraguay": "PY","French Polynesia": "PF","Qatar": "QA","Reunion": "RE","Romania": "RO","Russia": "RU","Rwanda": "RW","Saudi Arabia": "SA","Solomon Islands": "SB","El Salvador": "SV","Somalia": "SO","Sao Tome and Principe": "ST","Suriname": "SR","Slovakia": "SK","Slovenia": "SI","Sweden": "SE","Eswatini": "SZ","Chad": "TD","Togo": "TG","Thailand": "TH","Tajikistan": "TJ","Turkmenistan": "TM","Tonga": "TO","Tunisia": "TN","Turkey": "TR","Taiwan": "TW","Tanzania": "TZ","Uganda": "UG","Ukraine": "UA","Uruguay": "UY","United States": "US","Uzbekistan": "UZ","Saint Vincent and the Grenadines": "VC","Venezuela": "VE","British Virgin Islands": "VG","U.S. Virgin Islands": "VI","Vietnam": "VN","Vanuatu": "VU","Samoa": "WS","Yemen": "YE","Montenegro": "ME","Kosovo": "XK","Serbia": "RS","South Africa": "ZA","Zambia": "ZM","Zimbabwe": "ZW","Bosnia and Herzegovina": "BA","Bolivia": "BO","American Samoa": "AS","Hong Kong": "HK","Singapore": "SG","Armenia": "AM","Kuwait": "KW","Selangor": "MY","Burkina Faso": "BF","Cape Verde": "CV","Grenada": "GD","Ghana": "GH","Gibraltar": "GI","The Gambia": "GM","Guinea": "GN","Liberia": "LR","Lesotho": "LS","Mauritania": "MR","Sierra Leone": "SL","Senegal": "SN","Oman": "OM","Jordan": "JO","Honduras": "HN","Albania": "AL","Cameroon": "CM","Botswana": "BW","Bermuda": "BM","Belize": "BZ","Mali": "ML","Western Sahara": "EH","Cote d'Ivoire": "CI","Andorra": "AD","Burundi": "BI","The Bahamas": "BS","Bhutan": "BT","Central African Republic": "CF","Republic of the Congo": "CG","Equatorial Guinea": "GQ","Guinea-Bissau": "GW","Maldives": "MV"}
    return geo_dict.get(country, 99999999)


"""
A note on queue time (&qt):
    If you don't include a value, the event will be logged when you POST to GA, not when it actually happened
    This can mess with your reporting, by e.g. pushing events' reporting to the subsequent day
    There are two latencies (both are accounted for):
         Event happened -> Webhook sent: avg 19000ms, range of 13-25s
         Lambda triggered -> GA POST: ~200-300ms total
    Queue times > 4 hours silently fail the POST, so we modify the param if the true qt is above that
"""
def track_google_analytics_event(data_to_write, **kwargs):
    tracking_url = "https://www.google-analytics.com/"
    if os.getenv("DEBUG"): tracking_url += "debug/"
    tracking_url += "collect?v=1&t=event"
    tracking_url += "&tid=" + "UA-131042255-2"
    tracking_url += "&ec=" + "product-" + ez_get(data_to_write, "data", "permalink") # event category
    tracking_url += "&ea=" + "purchased" # event action
    tracking_url += "&el=" + "purchased a product" # event label
    tracking_url += "&geoid=" + convert_geo_code(data_to_write.get("country"))
    tracking_url += "&ev=" + str(ez_get(data_to_write, "value")) # value. stays as 100x higher bc no decimal for cents
    tracking_url += "&aip=1" # anonymize IP since it's always the server's IP
    tracking_url += "&ds=" + "python" # data source - identify that this is not client JS

    queue_time = (data_to_write.get("updatedAt") - data_to_write.get("timestamp")) * 1000 # queue time - elapsed ms since event timestamp
    if queue_time > 14400000:
        logging.warning("Queue times above 4 hours will cause GA to silently reject the event. We are going to modify (!) the qt to be below that limit")
        queue_time = 14300000

    tracking_url += "&qt=" + str(queue_time)

    # Extract the Client ID from the Cross-Domain Session ID, if present
    if data_to_write.get("_ga"):
        client_id = ez_split(data_to_write.get("_ga"), "-", 1)
        tracking_url += "&cid=" + client_id
    # If not present, generate a random ID of the same length and shape
    else:
        tracking_url += "&cid=" + str(int(random.random() * 10**8)) + "." + str(data_to_write.get("timestamp"))

    # just to check how the next couple run
    logging.info(tracking_url)


    # Note: this will always return status_code 200
    resp = requests.post(tracking_url)
    if os.getenv("DEBUG"): print(resp.text)
    if not kwargs.get("disable_print"): logging.info(f"Successfully did POST'd the information to Google Analytics")


def write_dynamodb_item(dict_to_write, table, **kwargs):
    table = boto3.resource('dynamodb').Table(table)
    dict_to_write = {"Item": dict_to_write}

    try:
        table.put_item(**dict_to_write)
    except Exception as e:
        logging.error(e)
        logging.error(dict_to_write)
        return False

    if not kwargs.get("disable_print"): logging.info(f"Successfully did a Dynamo Write to {table}")


# Document location
# "&dl=" + "https://gumroad.com/l/" + ez_get(data_to_write, "data", "permalink")

# Document Path
# "&dp=" + "/" + ez_get(data_to_write, "data", "permalink")

# Document Title
# "dt=" + "purchased a product"


# times = "2020-09-12T21:37:48Z"
# timestamp = datetime.strptime(times.replace("T", " ").replace("Z", ""), "%Y-%m-%d %H:%M:%S")
# timestamp = timestamp - timedelta(hours=7)

# test_dict = {
#     "_ga": "2.197206063.1689275659.1599939181-845139552.1599939181",
#     "country": "Unknown",
#     "data": {"permalink": "WPLqz"},
#     "value": 19900,
#     "timestamp": timestamp,
# }

# tz_adjustment = 7 if is_timezone_in_daylight_savings("America/Los_Angeles") else 8
# timestamp = timestamp - timedelta(hours=tz_adjustment)
# - timedelta(hours=tz_adjustment)

# I hate that I have to write this
# def is_timezone_in_daylight_savings(zonename):
#     os.environ['TZ'] = zonename
#     return time.localtime().tm_isdst > 0

# Not used in traditional event tracking
# tracking_url += "&cu=" + ez_get(data, "data", "currency") # currency
