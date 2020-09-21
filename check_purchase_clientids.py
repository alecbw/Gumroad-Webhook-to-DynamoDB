from utility.util import ez_split, ez_get
from utility.util_datastores import scan_dynamodb
from utility.util_local import write_output_csv

import os
import random
from datetime import datetime, timedelta, timezone
import logging
from pprint import pprint

import boto3
import requests


################################ ~ GA POST and helpers ########################################


"""
This checks for a purchase of the same value at the same minute as the sale_timestamp, timezone adjusted
If there is one, we don't POST this webhook to GA
"""
def check_for_existing_GA_purchase(client_id):
    GA_VIEW_ID = "ga:" + os.environ["GA_VIEW_ID"] if "ga:" not in os.environ["GA_VIEW_ID"] else os.environ["GA_TOKEN"]


    # GMT_ADJUSTMENT = int(os.environ["GMT_ADJUSTMENT"])

    # adj_sale_timestamp = data_to_write["timestamp"] - (GMT_ADJUSTMENT * 60 * 60) #- timedelta(hours=5)
    # adj_sale_timestamp = datetime.utcfromtimestamp(adj_sale_timestamp)
    # ga_event_dateHourMinute = datetime.strftime(adj_sale_timestamp, "%Y%m%d%H%M") 
    today = datetime.utcnow()
    start_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")

    lookup_url = "https://www.googleapis.com/analytics/v3/data/ga"
    lookup_url += "?ids=" + GA_VIEW_ID 
    lookup_url += "&start-date=" + start_date
    lookup_url += "&end-date=" + end_date
    lookup_url += "&metrics=" + "ga:totalEvents,ga:eventValue,ga:sessions"
    lookup_url += "&dimensions=" + "ga:dataSource,ga:dateHourMinute,ga:referralPath,ga:fullReferrer,ga:sourceMedium"
    lookup_url += "&filters=" + "ga:clientId==" + str(client_id)
    lookup_url += "&samplingLevel=" + "HIGHER_PRECISION"
    
    logging.info(lookup_url)

    resp = requests.get(
        lookup_url,
        headers={
            "User-Agent": "Python Lambda: github.com/alecbw/Gumroad-to-Google-Analytics-Webhook",
            "Authorization": "Bearer " + os.environ["GA_TOKEN"],
        },
    )
    logging.info(f"Successfully looked up purchase timestamp; status code: {resp.status_code}")

    pprint(resp.json())
    if resp.json() and resp.json().get("totalResults") > 0:
        logging.info("There is an existing purchase at the same time; this will not write this event to GA")
        return True




################################# ~ Main ~ ###################################################


"""
Both timestamps - the sale_timestamp 'timestamp' and the write timestamp 'updatedAt' are UTC timezone-agnostic
'value' ('price' in the GR webhook) is an int multiplied by 100 (e.g. $23.99 represented as 2399)
The conversion back to dollars and cents is not handled here, so make sure you account for that
Misc note: GMT and UTC are the same thing
"""
if __name__ == "__main__":

    data_lod = scan_dynamodb("GRWebhookData")
    logging.info(f"Found {len(data_lod)} entries")

    for row in data_lod:
        client_id = row.get("cid") or ez_split(row.get("url_params[_ga]"), "-", 1)
        check_for_existing_GA_purchase(client_id)

    # write_output_csv(filename, output_lod)




# def lambda_handler(event, context):
#     param_dict, missing_params = validate_params(event,
#          required_params=["Secret_Key"],
#          optional_params=[]
#     )
#     logging.info(event) # will take this out once I've seen enough data
#     if param_dict.get("Secret_Key", "").replace("export SECRET_KEY=", "") != os.environ["SECRET_KEY"]:
#         return package_response("Please authenticate", 403, warn="please auth")

#     if os.getenv("DEBUG"):
#         logging.info("\033[36mYou are now in debug. Dynamo won't write, and the GA POST will be to the debug endpoint\033[39m\n")

#     # parse_qs writes every value as a list, so we subsequently unpack those lists
#     webhook_data = parse_qs(event["body"])
#     webhook_data = {k: v if len(v) > 1 else v[0] for k, v in webhook_data.items()}

#     sale_timestamp = datetime.strptime(webhook_data.pop("sale_timestamp").replace("Z", ""), "%Y-%m-%dT%H:%M:%S")

#     data_to_write = {
#         "email": webhook_data.pop("email"),
#         "gifter_email": webhook_data.pop("gifter_email"),
#         "timestamp": int(sale_timestamp.replace(tzinfo=timezone.utc).timestamp()),  # UTC Non-Adjusted
#         "value": int(webhook_data.pop("price")) or int(webhook_data.pop("gift_price")),
#         "offer_code": webhook_data.pop("offer_code", "No Code"),
#         "country": webhook_data.pop("ip_country", "Unknown"),
#         "refunded": 1 if webhook_data.pop("refunded") in ["true", "True", True] else 0,
#         "_ga": webhook_data.get("url_params[_ga]", ""),
#         "cid": generate_clientid(webhook_data, sale_timestamp),
#         "data": webhook_data,  # Store the rest in a blob
#         "updatedAt": int(datetime.utcnow().timestamp()),  # UTC Non-Adjusted
#     }

#     if not os.getenv("DEBUG"):
#         write_dynamodb_item(data_to_write, "GRWebhookData")

#     # if not check_for_existing_GA_purchase(data_to_write):
#     track_google_analytics_event(data_to_write)

#     logging.info("Dynamo write and GA POST both appear to be successful")
#     return package_response("Success", 200)


###################################################################################################