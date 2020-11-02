from utility.util import ez_split, ez_get
from utility.util_datastores import scan_dynamodb
from utility.util_local import write_output_csv
from utility.util_gspread import service_account_exchange_refresh_token_for_access_token

import os
import random
from datetime import datetime, timedelta, timezone
import logging

import requests


################################ ~ GA GET ~ ########################################


"""

"""
def lookup_GA_clientid(client_id):
    GA_VIEW_ID = "ga:" + os.environ["GA_VIEW_ID"] if "ga:" not in os.environ["GA_VIEW_ID"] else os.environ["GA_VIEW_ID"]
    GA_TOKEN = service_account_exchange_refresh_token_for_access_token(os.environ["GA_KEYS"])

    today = datetime.utcnow()
    start_date = (today - timedelta(days=60)).strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")

    ga_cid_lookup_url = "https://www.googleapis.com/analytics/v3/data/ga"
    ga_cid_lookup_url += "?ids=" + GA_VIEW_ID 
    ga_cid_lookup_url += "&start-date=" + start_date
    ga_cid_lookup_url += "&end-date=" + end_date
    ga_cid_lookup_url += "&metrics=" + "ga:sessions,ga:totalEvents,ga:eventValue"
    ga_cid_lookup_url += "&dimensions=" + "ga:dataSource,ga:dateHourMinute,ga:fullReferrer,ga:sourceMedium,ga:keyword,ga:adMatchedQuery"
    ga_cid_lookup_url += "&filters=" + "ga:clientId==" + str(client_id)
    ga_cid_lookup_url += "&sort=" + "ga:dateHourMinute"
    ga_cid_lookup_url += "&samplingLevel=" + "HIGHER_PRECISION"
    
    # logging.info(ga_cid_lookup_url)

    resp = requests.get(
        ga_cid_lookup_url,
        headers={
            "User-Agent": "Python Lambda: github.com/alecbw/Gumroad-to-Google-Analytics-Webhook",
            "Authorization": "Bearer " + GA_TOKEN,
        },
    )

    resp_lol = resp.json().get("rows")

    if not resp_lol:
        logging.info("ClientID not found in this time range")
        return {}

    ga_output_dict = {
        "dataSource": ", ".join([x[0] for x in resp_lol]),
        "dateHourMinute": ", ".join([x[1] for x in resp_lol]),
        "fullReferrer": ", ".join([x[2] for x in resp_lol]),
        "sourceMedium": ", ".join([x[3] for x in resp_lol]),
        "sessions": sum([int(x[6]) for x in resp_lol]),
        "totalEvents": sum([int(x[7]) for x in resp_lol]),
        "eventValue": sum([int(x[8]) for x in resp_lol]),
        "first_event": resp_lol[0][1],
        "first_sourcemedium": next((x[3] for x in resp_lol if x[3] != "(direct) / (none)"), None),
        "pur_kw": resp_lol[0][4],
        "pur_search_term": resp_lol[0][5],

    }

    return ga_output_dict


def mailerlite_lookup(email):
    ml_lookup_url = "https://api.mailerlite.com/api/v2/subscribers/search"
    ml_lookup_url += "?query=" + email

    resp = requests.get(
        ml_lookup_url,
        headers={
            "User-Agent": "Python Lambda: github.com/alecbw/Gumroad-to-Google-Analytics-Webhook",
            "X-MailerLite-ApiKey": os.environ["ML_KEY"],
        },
    )
    if not resp.json():
        logging.info("Email not found in ML lookup")
        return {}

    ml_output_dict = {
        "ml_created": resp.json()[0].get("date_created"),
        "ml_source": next((x["value"] for x in resp.json()[0].get("fields") if x["key"] == "source" and x["value"]), None),
    }


    return ml_output_dict


def lookup_email_signup_in_ga(ml_timestamp):
    GMT_ADJUSTMENT = int(os.environ["GMT_ADJUSTMENT"])
    GA_VIEW_ID = "ga:" + os.environ["GA_VIEW_ID"] if "ga:" not in os.environ["GA_VIEW_ID"] else os.environ["GA_VIEW_ID"]
    GA_TOKEN = service_account_exchange_refresh_token_for_access_token(os.environ["GA_KEYS"])

    ml_timestamp = datetime.strptime(ml_timestamp, "%Y-%m-%d %H:%M:%S")
    ml_timestamp = ml_timestamp - timedelta(hours=GMT_ADJUSTMENT)
    date = datetime.strftime(ml_timestamp, "%Y-%m-%d")
    ga_timestamp = datetime.strftime(ml_timestamp, "%Y%m%d%H%M")

    filters = "ga:goal4Completions>0"
    filters += ";ga:dateHourMinute==" + str(ga_timestamp) + ",ga:dateHourMinute==" + str(int(ga_timestamp)-1)

    ga_ts_lookup_url = "https://www.googleapis.com/analytics/v3/data/ga"
    ga_ts_lookup_url += "?ids=" + GA_VIEW_ID 
    ga_ts_lookup_url += "&start-date=" + date
    ga_ts_lookup_url += "&end-date=" + date
    ga_ts_lookup_url += "&metrics=" + "ga:uniquePageviews"
    ga_ts_lookup_url += "&dimensions=" + "ga:adMatchedQuery,ga:keyword,ga:dateHourMinute,ga:fullReferrer,ga:sourceMedium,ga:clientId"
    ga_ts_lookup_url += "&filters=" + filters
    ga_ts_lookup_url += "&samplingLevel=" + "HIGHER_PRECISION"

    # logging.info(ga_ts_lookup_url)

    resp = requests.get(
        ga_ts_lookup_url,
        headers={
            "User-Agent": "Python Lambda: github.com/alecbw/Gumroad-to-Google-Analytics-Webhook",
            "Authorization": "Bearer " + GA_TOKEN,
        },
    )
    resp_lol = resp.json().get("rows")

    if not resp_lol:
        # logging.info("No GA Goal Completion for Email Signup found at this timestamp")
        return {
            "signup_ga_timestamp": ga_timestamp #resp_lol[0][2],
        }

    if len(resp_lol) > 1:
        logging.warning(f"More than one email found for timestamp {ga_timestamp}")

    ga_matched_signup_dict = { # should this be comma delim string of all entries? TODO
        "signup_search_query": resp_lol[0][0],
        "signup_keyword": resp_lol[0][1],
        "signup_ga_timestamp": resp_lol[0][2],
        "signup_sourcemedium": resp_lol[0][3],
        "signup_referrer": resp_lol[0][4],
        "signup_clientid": '"' + resp_lol[0][5] + '"', # prevent truncation
    }

    return ga_matched_signup_dict

################################# ~ Main ~ ###################################################


"""
"""
if __name__ == "__main__":

    start_at_timestamp = 1603678545
    data_lod = scan_dynamodb("GRWebhookData", after={"timestamp": start_at_timestamp})

    logging.info(f"Starting after timestamp: {start_at_timestamp}")

    output_lod = []
    for row in data_lod:
        client_id = row.get("cid") or ez_split(row.get("_ga"), "-", 1)
        row["sale_readable"] = datetime.utcfromtimestamp(row["timestamp"])

        if client_id:
            ga_cid_dict = lookup_GA_clientid(client_id)
            row = {**row, **ga_cid_dict}
            row['cid'] = '"' + client_id + '"' # prevent truncation
        else: 
            pass


        ml_looked_up_dict = mailerlite_lookup(row["email"])
        row = {**row, **ml_looked_up_dict}

        if "ml_created" in row: # and row.get("ml_source") in [None]:
            ga_signup_dict = lookup_email_signup_in_ga(row["ml_created"])
            row = {**row, **ga_signup_dict}

        output_lod.append(row)


    output_lod = sorted(output_lod, key = lambda i: i['timestamp'])

    logging.info(f"The output will have {len(output_lod)} rows")

    header = ["sale_readable", "value", "country", "first_event", "first_sourcemedium", "dataSource", "dateHourMinute", "referralPath", "fullReferrer", "sourceMedium", "sessions", "totalEvents", "eventValue", "email", "gifter_email", "cid", "offer_code",  "data", "updatedAt", "timestamp", "_ga", "refunded", "ad_attr", "delta ml_signup and purchase", "ml_created", "ml_source", "pur_kw", "pur_search_term", "signup_keyword", "signup_search_query", "signup_sourcemedium", "signup_referrer", "signup_ga_timestamp", "signup_clientid"]
    write_output_csv("DyDB Purchase Data.csv", output_lod, header=header)

  
