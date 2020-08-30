from utility.util import *
from utility.util_datastores import write_dynamodb_item

import os
from datetime import datetime
from urllib.parse import parse_qs
import logging

import boto3

############################################################################################


def lambda_handler(event, context):
    param_dict, missing_params = validate_params(event,
        required_params=["Secret_Key"],
        optional_params=[]
    )

    if param_dict.get("Secret_Key") != os.environ["SECRET_KEY"]:
        return package_response(f"Please authenticate", 403)

    # parse_qs writes every value as a list, so we subsequently unpack those lists
    webhook_data = parse_qs(event["body"])
    webhook_data = {k:v if len(v)>1 else v[0] for k,v in webhook_data.items()}

    data_to_write = {
        "email": webhook_data.pop("email"),
        "timestamp": datetime.strptime(webhook_data.pop("sale_timestamp"), "%Y-%m-%d %H:%M:%S"),
        # "order_number": webhook_data.pop("order_number"),
        # "product_id": webhook_data.pop("product_id"),
        "value": int(webhook_data.pop("price")),
        "offer_code": webhook_data.get("offer_code"),
        "country": webhook_data.pop("ip_country"),
        "refunded": 1 if webhook_data.pop("refunded") in ["true", "True", True] else 0,
        "data": webhook_data,
    }
    if not data_to_write["email"] or not data_to_write["timestamp"]:
        logging.error(webhook_data)
        raise KeyError("Missing a necessary key to perform a write")

    write_dynamodb_item(data_to_write, "GRWebhookData")

    return package_response("Success", 200)


############################################################################################
# 2020-06-09T18:11:22Z
# "%Y-%m-%dT%H:%M:%SZ"