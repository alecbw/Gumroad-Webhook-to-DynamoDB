from utility.util import package_response, validate_params
from utility.util_datastores import get_s3_file, write_s3_file

import os
from datetime import datetime
import logging
logger = logging.getLogger()

from more_itertools import unique_everseen

import boto3
##############################################


def lambda_handler(event, context):
    param_dict, missing_params = validate_params(event,
        required_params=[],
        optional_params=[]
    )
    if missing_params:
        return package_response(f"Missing required params {missing_params}", 422)

    logging.info('start')
    logging.info(datetime.now())

    # s3 = boto3.resource("s3")
    # s3_object = s3.Object(bucket, filename)
    # s3_object.put(Body=(bytes(json.dumps(json_data).encode("UTF-8"))))

    # lod = [{"foo":"bar", "fez":"faz"}, {"foo":"bar", "fez":"faz"}, {"foo":"234", "fez":"faz"},  {"foo":"2s4", "fez":"2345"}]
    # sets = (frozenset(d.items()) for d in lod)
    # unique_sets = unique_everseen(sets, key=itemgetter(None))
    # logging.info(unique_sets)
    # unique_dicts = [dict(s) for s in unique_sets]

    s3_file = get_s3_file("db-staging-bucket", "email_format_csv/Email Formats.csv")
    s3_read = s3_file.read()

    with open(s3_read,'r') as f, open('output.csv','w') as out_file:
        out_file.writelines(unique_everseen(f))

    # logging.info(lod)
    # new_lod = list(unique_everseen(s3_read, None))
    # logging.info(new_lod)
    # for line in unique_everseen(s3_read, key=None):
    #     outfile.write(line)

    # logging.info(datetime.now())

    # logging.info(s3_read)
    # logging.info(len(s3_read))
    # logging.info(s3_read[0])
    # logging.info(datetime.now())
    client = boto3.client('s3')
    # variable = b'csv, output, from, json' # need bytes here or a file path
    response = client.put_object(Bucket='db-staging-bucket', Body='output.csv', Key='email_format_csv/DD Email Formats.csv')
    # write_s3_file("", "", out_file):
    logging.info(datetime.now())


    # return package_response(result_lod, 200)


