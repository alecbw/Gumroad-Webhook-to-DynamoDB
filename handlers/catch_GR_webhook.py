from utility.util import ez_split, ez_get, validate_params, package_response

import os
import random
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs
import logging

import boto3
import requests


################################ ~ GA POST and helpers ########################################
# onst scopes = [''];

"""
ClientID's identify non-logged-in users' devices.
    >= 1 ClientIDs map to the eventual UserID, if the user authenticates 
        (You have to set this up in GA Admin -> Property -> Tracking Info -> User-ID)

Here, we:
1. Extract the ClientID from the Cross-Domain Linker Session ID (_ga), if present
2. If not present, generate a random ID of the same length and shape
    Generated IDs will have Source=(direct)	& Medium=(none) applied by default
!. This code does not handle User IDs in any way.
"""

def generate_clientid(webhook_data, sale_timestamp):
    if webhook_data.get("url_params[_ga]"):
        return ez_split(webhook_data.get("url_params[_ga]"), "-", 1)
    else:
        logging.info("No _ga param found; generating a new Client ID")
        return f"{int(random.random() * 10**8)}.{int(sale_timestamp.timestamp())}"


"""
# Calculates Queue Time, the elapsed ms since event timestamp
A note on queue time (&qt):
    If you don't include a value, the event will be logged when you POST to GA, not when it actually happened
    This can mess with your reporting, by e.g. pushing events' reporting to the subsequent day
    There are two latencies (both are accounted for):
         1. Event happened -> Webhook sent: avg 19000ms, range of 13-25s
         2. Lambda triggered -> GA POST: ~200-300ms total
    Queue times > 4 hours silently fail the POST, so we modify the param if the true qt is above that
"""
def calculate_queue_time(data_to_write):
    queue_time = (data_to_write["updatedAt"] - data_to_write["timestamp"]) * 1000
    if queue_time > 14400000:
        logging.warning("We are going to modify (!) the qt to be below the 4 hour GA limit")
        queue_time = 14300000
    return str(queue_time)


"""
If you don't provide geo, GA wrongly infers it from the Server's IP as US.
    We translate the GR ip_country to the GA shortcode, if possible
    If the param is missing or doesn't match, we return code: 99999999
    An invalid code will result in geographical dimensions to be set to '(not set)'.
    Docs: https://developers.google.com/analytics/devguides/collection/protocol/v1/parameters
"""
def convert_geo_code(country):
    geo_dict = {"Afghanistan": "AF","Angola": "AO","Anguilla": "AI","United Arab Emirates": "AE","Argentina": "AR","Antigua and Barbuda": "AG","Australia": "AU","Austria": "AT","Azerbaijan": "AZ","Belgium": "BE","Benin": "BJ","Bangladesh": "BD","Bulgaria": "BG","Bahrain": "BH","Belarus": "BY","Brazil": "BR","Barbados": "BB","Brunei": "BN","Canada": "CA","United Kingdom": "GB","Switzerland": "CH","Chile": "CL","China": "CN","Democratic Republic of the Congo": "CD","Colombia": "CO","Comoros": "KM","Costa Rica": "CR","Cayman Islands": "KY","Cyprus": "CY","Czechia": "CZ","Germany": "DE","Djibouti": "DJ","Dominica": "DM","Denmark": "DK","Dominican Republic": "DO","Algeria": "DZ","Ecuador": "EC","Egypt": "EG","Eritrea": "ER","Spain": "ES","Estonia": "EE","Ethiopia": "ET","Finland": "FI","Fiji": "FJ","France": "FR","Faroe Islands": "FO","Federated States of Micronesia": "FM","Gabon": "GA","Guernsey": "GG","Jersey": "JE","Georgia": "GE","Guadeloupe": "GP","Greece": "GR","Western Greece and the Ionian": "GR","Greenland": "GL","Guatemala": "GT","French Guiana": "GF","Guam": "GU","Guyana": "GY","Croatia": "HR","Haiti": "HT","Hungary": "HU","Indonesia": "ID","India": "IN","Ireland": "IE","Iraq": "IQ","Iceland": "IS","Israel": "IL","Italy": "IT","Apulia": "IT","Jamaica": "JM","Japan": "JP","Kazakhstan": "KZ","Kenya": "KE","Kyrgyzstan": "KG","Cambodia": "KH","Saint Kitts and Nevis": "KN","South Korea": "KR","Laos": "LA","Lebanon": "LB","Libya": "LY","Liechtenstein": "LI","Sri Lanka": "LK","Lithuania": "LT","Luxembourg": "LU","Latvia": "LV","Macao": "MO","Morocco": "MA","Moldova": "MD","Madagascar": "MG","Mexico": "MX","North Macedonia": "MK","Malta": "MT","Myanmar (Burma)": "MM","Mongolia": "MN","Northern Mariana Islands": "MP","Mozambique": "MZ","Martinique": "MQ","Mauritius": "MU","Malawi": "MW","Malaysia": "MY","Namibia": "NA","New Caledonia": "NC","Niger": "NE","Nigeria": "NG","Nicaragua": "NI","Netherlands": "NL","Norway": "NO","Nepal": "NP","New Zealand": "NZ","Pakistan": "PK","Panama": "PA","Peru": "PE","Philippines": "PH","Palau": "PW","Papua New Guinea": "PG","Poland": "PL","Puerto Rico": "PR","Portugal": "PT","Paraguay": "PY","French Polynesia": "PF","Qatar": "QA","Reunion": "RE","Romania": "RO","Russia": "RU","Rwanda": "RW","Saudi Arabia": "SA","Solomon Islands": "SB","El Salvador": "SV","Somalia": "SO","Sao Tome and Principe": "ST","Suriname": "SR","Slovakia": "SK","Slovenia": "SI","Sweden": "SE","Eswatini": "SZ","Chad": "TD","Togo": "TG","Thailand": "TH","Tajikistan": "TJ","Turkmenistan": "TM","Tonga": "TO","Tunisia": "TN","Turkey": "TR","Taiwan": "TW","Tanzania": "TZ","Uganda": "UG","Ukraine": "UA","Uruguay": "UY","United States": "US","Uzbekistan": "UZ","Saint Vincent and the Grenadines": "VC","Venezuela": "VE","British Virgin Islands": "VG","U.S. Virgin Islands": "VI","Vietnam": "VN","Vanuatu": "VU","Samoa": "WS","Yemen": "YE","Montenegro": "ME","Kosovo": "XK","Serbia": "RS","South Africa": "ZA","Zambia": "ZM","Zimbabwe": "ZW","Bosnia and Herzegovina": "BA","Bolivia": "BO","American Samoa": "AS","Hong Kong": "HK","Singapore": "SG","Armenia": "AM","Kuwait": "KW","Selangor": "MY","Burkina Faso": "BF","Cape Verde": "CV","Grenada": "GD","Ghana": "GH","Gibraltar": "GI","The Gambia": "GM","Guinea": "GN","Liberia": "LR","Lesotho": "LS","Mauritania": "MR","Sierra Leone": "SL","Senegal": "SN","Oman": "OM","Jordan": "JO","Honduras": "HN","Albania": "AL","Cameroon": "CM","Botswana": "BW","Bermuda": "BM","Belize": "BZ","Mali": "ML","Western Sahara": "EH","Cote d'Ivoire": "CI","Andorra": "AD","Burundi": "BI","The Bahamas": "BS","Bhutan": "BT","Central African Republic": "CF","Republic of the Congo": "CG","Equatorial Guinea": "GQ","Guinea-Bissau": "GW","Maldives": "MV"}
    return geo_dict.get(country, str(99999999))


"""
POSTs the event data to Google Analytics. There will be no request and it will always return 200 (unless in DEBUG)
A note: the GA call will silently fail without a User Agent, even if the debug endpoint says it's valid
"""
def track_google_analytics_event(data_to_write):
    tracking_url = "https://www.google-analytics.com/"
    if os.getenv("DEBUG"):
        tracking_url += "debug/"
    tracking_url += "collect?v=1&t=event"
    tracking_url += "&tid=" + "UA-131042255-2"  # web property ID
    tracking_url += "&ec=" + "product-" + ez_get(data_to_write, "data", "permalink")  # event category
    tracking_url += "&ea=" + "purchased"  # event action
    tracking_url += "&el=" + "purchased a product"  # event label
    tracking_url += "&geoid=" + convert_geo_code(data_to_write.get("country"))  # geocode
    tracking_url += "&ev=" + str(ez_get(data_to_write, "value"))  # value. stays as 100x higher bc no decimal for cents
    tracking_url += "&aip=" + "1"  # anonymize IP since it's always the server's IP
    tracking_url += "&ds=" + "python"  # data source - identify that this is not client JS
    tracking_url += "&cid=" + data_to_write["cid"]  # client ID
    tracking_url += "&qt=" + calculate_queue_time(data_to_write)

    resp = requests.post(
        tracking_url,
        headers={
            "User-Agent": "Python Lambda: github.com/alecbw/Gumroad-to-Google-Analytics-Webhook"
        },
    )

    if os.getenv("DEBUG"):
        logging.info(tracking_url)
        logging.info(resp.text)

    logging.debug("Successfully POST'd the information to Google Analytics")


"""
This checks for a purchase of the same value at the same minute as the sale_timestamp, timezone adjusted
If there is one, we don't POST this webhook to GA
"""
def check_for_existing_GA_purchase(data_to_write):
    GMT_ADJUSTMENT = int(os.environ["GMT_ADJUSTMENT"])
    GA_VIEW_ID = "ga:" + os.environ["GA_VIEW_ID"] if "ga:" not in os.environ["GA_TOKEN"] else os.environ["GA_TOKEN"]

    adj_sale_timestamp = data_to_write["timestamp"] - (GMT_ADJUSTMENT * 60 * 60) #- timedelta(hours=5)
    adj_sale_timestamp = datetime.utcfromtimestamp(adj_sale_timestamp)
    ga_event_dateHourMinute = datetime.strftime(adj_sale_timestamp, "%Y%m%d%H%M") 

    adj_date = (adj_sale_timestamp).strftime("%Y-%m-%d")

    filters = f"ga:dateHourMinute==" + ga_event_dateHourMinute
    filters += ";ga:eventAction==" + "purchased"
    filters += ";ga:eventValue==" + str(data_to_write["value"])

    reports_url = "https://www.googleapis.com/analytics/v3/data/ga"
    reports_url += "?ids=" + GA_VIEW_ID
    reports_url += "&start-date=" + adj_date
    reports_url += "&end-date=" + adj_date
    reports_url += "&metrics=" + "ga:totalEvents,ga:eventValue"
    reports_url += "&dimensions=" + "ga:dataSource,ga:clientId,ga:dateHourMinute"
    reports_url += "&filters=" + filters
    reports_url += "&samplingLevel=" + "HIGHER_PRECISION"
    
    if os.getenv("DEBUG"):
        logging.info(reports_url)

    resp = requests.get(
        reports_url,
        headers={
            "User-Agent": "Python Lambda: github.com/alecbw/Gumroad-to-Google-Analytics-Webhook",
            "Authorization": "Bearer " + os.environ["GA_TOKEN"],
        },
    )
    logging.info(f"Successfully looked up purchase timestamp; status code: {resp.status_code}")

    if resp.json() and resp.json().get("totalResults") > 0:
        logging.info("There is an existing purchase at the same time; this will not write this event to GA")
        return True


########################### ~ Dynamo Write ~ ###################################################


# We do this before the GA POST just to be safe and to have our own copy of the data
def write_dynamodb_item(dict_to_write, table):
    table = boto3.resource("dynamodb").Table(table)
    dict_to_write = {"Item": dict_to_write}

    try:
        table.put_item(**dict_to_write)
    except Exception as e:
        logging.error(f"There's been a Dynamo write error: {e}")
        logging.error(dict_to_write)
        return False

    logging.debug(f"Successfully did a Dynamo Write to {table}")


################################# ~ Main ~ ###################################################


"""
Both timestamps - the sale_timestamp 'timestamp' and the write timestamp 'updatedAt' are UTC timezone-agnostic
'value' ('price' in the GR webhook) is an int multiplied by 100 (e.g. $23.99 represented as 2399)
The conversion back to dollars and cents is not handled here, so make sure you account for that
Misc note: GMT and UTC are the same thing
"""
def lambda_handler(event, context):
    param_dict, missing_params = validate_params(event,
         required_params=["Secret_Key"],
         optional_params=[]
    )
    logging.info(event) # will take this out once I've seen enough data
    if param_dict.get("Secret_Key", "").replace("export SECRET_KEY=", "") != os.environ["SECRET_KEY"]:
        return package_response("Please authenticate", 403, warn="please auth")

    if os.getenv("DEBUG"):
        logging.info("\033[36mYou are now in debug. Dynamo won't write, and the GA POST will be to the debug endpoint\033[39m\n")

    # parse_qs writes every value as a list, so we subsequently unpack those lists
    webhook_data = parse_qs(event["body"])
    webhook_data = {k: v if len(v) > 1 else v[0] for k, v in webhook_data.items()}

    sale_timestamp = datetime.strptime(webhook_data.pop("sale_timestamp").replace("Z", ""), "%Y-%m-%dT%H:%M:%S")

    data_to_write = {
        "email": webhook_data.pop("email"),
        "timestamp": int(sale_timestamp.replace(tzinfo=timezone.utc).timestamp()),  # UTC Non-Adjusted
        "value": int(webhook_data.pop("price")),
        "offer_code": webhook_data.pop("offer_code", "No Code"),
        "country": webhook_data.pop("ip_country", "Unknown"),
        "refunded": 1 if webhook_data.pop("refunded") in ["true", "True", True] else 0,
        "_ga": webhook_data.get("url_params[_ga]", ""),
        "cid": generate_clientid(webhook_data, sale_timestamp),
        "data": webhook_data,  # Store the rest in a blob
        "updatedAt": int(datetime.utcnow().timestamp()),  # UTC Non-Adjusted
    }

    if not os.getenv("DEBUG"):
        write_dynamodb_item(data_to_write, "GRWebhookData")

    if not check_for_existing_GA_purchase(data_to_write):
        track_google_analytics_event(data_to_write)

    logging.info("Dynamo write and GA POST both appear to be successful")
    return package_response("Success", 200)


###################################################################################################