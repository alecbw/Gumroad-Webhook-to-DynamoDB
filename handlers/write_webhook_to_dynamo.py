from utility.util import *
from utility.util_datastores import write_dynamodb_item

import os
from datetime import datetime
import logging
logger = logging.getLogger()

import boto3

############################################################################################


def lambda_handler(event, context):
    param_dict, missing_params = validate_params(event,
        required_params=["Secret_Key"],
        optional_params=[]
    )

    if missing_params:
        return package_response(f"Missing required params {missing_params}", 422)
    elif param_dict["Secret_Key"] != os.environ["SECRET_KEY"]:
        return package_response(f"Please authenticate", 403)

    webhook_data = json.loads(event["body"])[0]
    data_to_write = {
        "email": webhook_data["email"],
        "timestamp": webhook_data["sale_timestamp"], # TODO convert
        "order_number": webhook_data["order_number"],
        "product_id": webhook_data["product_id"],
        "value": webhook_data["price"],
        "offer_code": webhook_data.get("offer_code"),
        "country": webhook_data["ip_country"],
        "refunded": webhook_data["refunded"],
    }

    write_dynamodb_item(data_to_write, "GRWebhookData", **kwargs)

    return package_response("Sucess", 200)


############################################################################################
