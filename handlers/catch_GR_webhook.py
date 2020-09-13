from utility.util import *

import os
from datetime import datetime, timedelta
from urllib.parse import parse_qs
import logging

import boto3
import requests

############################################################################################


def lambda_handler(event, context):
    param_dict, missing_params = validate_params(event,
        required_params=["Secret_Key"],
        optional_params=[]
    )
    logging.info(event)
    if param_dict.get("Secret_Key") not in [os.environ["SECRET_KEY"], "export SECRET_KEY=" + os.environ["SECRET_KEY"]]:
        return package_response(f"Please authenticate", 403, warn="please auth")

    # parse_qs writes every value as a list, so we subsequently unpack those lists
    webhook_data = parse_qs(event["body"])
    webhook_data = {k:v if len(v)>1 else v[0] for k,v in webhook_data.items()}

    timestamp = datetime.strptime(webhook_data.pop("sale_timestamp").replace("T", " ").replace("Z", ""), "%Y-%m-%d %H:%M:%S")
    timestamp = timestamp - timedelta(hours=7)

    data_to_write = {
        "email": webhook_data.pop("email"),
        "timestamp": int(timestamp.timestamp()),
        "value": int(webhook_data.pop("price")), # need to divide by 100 later fyi
        "offer_code": webhook_data.pop("offer_code", "No Code"),
        "country": webhook_data.pop("ip_country", "Unknown"),
        "refunded": 1 if webhook_data.pop("refunded") in ["true", "True", True] else 0,
        "data": webhook_data,
        "_ga": webhook_data.get("url_params[_ga]", ""),
        'updatedAt': int(datetime.now().timestamp()),
    }

    success = write_dynamodb_item(data_to_write, "GRWebhookData")

    track_google_analytics_event(data_to_write)

    return package_response(f"Success status was {success}", 200)


############################################################################################

def track_google_analytics_event(data_to_write):
    tracking_url = 'https://www.google-analytics.com/collect?v=1&t=event'
    tracking_url += '&tid=' + 'UA-131042255-2'
    tracking_url += "&ec=" + "product-" + ez_get(data_to_write, "data", "permalink") # event category
    tracking_url += "&ea=" + "purchased" # event action
    tracking_url += "&el=" + "purchased a product" # event label
    tracking_url += "&ev=" + str(ez_get(data_to_write, "value")/100) # value
    tracking_url += "&cid=" + ez_get(data_to_write, "_ga") # Anon Client ID (actually GA Session ID sent Cross-Domain)
    tracking_url += '&aip=1'

    # Not used in traditional event tracking
    # tracking_url += "&cu=" + ez_get(data, "data", "currency") # currency

    print(tracking_url)
    resp = requests.post(tracking_url)
    print(resp)
    return


# Note: this will BY DEFAULT overwrite items with the same primary key (upsert)
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
    return True





    # event_category = "product-" + ez_get(data, "data", "permalink")
    # event_action = "purchased"
    # event_label = "
    #
    # tracking_id = 'UA-131042255-2'
	# clientid_str = str(datetime.now())
	# tid='+tracking_id+'&cid='+clientid_str+'&ec='+event_category+'&ea='+event_action+'&el='+event_label+'&aip=1'
    	# tracking_url = 'https://www.google-analytics.com/collect?v=1&t=event&tid='+tracking_id+'&cid='+clientid_str+'&ec='+event_category+'&ea='+event_action+'&el='+event_label+'&aip=1'
