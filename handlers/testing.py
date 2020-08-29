from utility.util import *
# from utility.util_datastores import get_s3_file, write_s3_file

import os
from datetime import datetime
import logging
logger = logging.getLogger()

from more_itertools import unique_everseen

import boto3
##############################################


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


    logging.info('start')
    logging.info(datetime.now())


    # return package_response(result_lod, 200)


