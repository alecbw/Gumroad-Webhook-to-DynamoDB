from utility.util import *

import os
from datetime import datetime, timedelta
from urllib.parse import parse_qs
import logging

import boto3

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
        "value": int(webhook_data.pop("price")),
        "offer_code": webhook_data.pop("offer_code", "No Code"),
        "country": webhook_data.pop("ip_country", "Unknown"),
        "refunded": 1 if webhook_data.pop("refunded") in ["true", "True", True] else 0,
        "data": webhook_data,
        "_ga": webhook_data.get("url_params[_ga]", ""),
        'updatedAt': int(datetime.now().timestamp()),
    }

    success = write_dynamodb_item(data_to_write, "GRWebhookData")

    return package_response(f"Success status was {success}", 200)


############################################################################################


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