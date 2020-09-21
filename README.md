# Gumroad-Webhook-to-DynamoDB

# Setup


Set environment variables
```
export SECRET_KEY="foobar"
export SENTRY_DSN="foo@bar.co"
```
If you want to test locally, ensure you export the DEBUG env var:
```
export DEBUG=True
```


# Using this


This repo contains a serverless.yml infrastructure-as-code file, which deploys 1 DynamoDB table and 1 Lambda

To create the CloudFormation Stack (and also subsequently update it), use:
``` 
sls deploy
```

You can test the Lambda by POSTing to it from Postman or curl. A sample body JSON string is provided below:
```
{
  "seller_id": "A_LONG_STRING==",
  "product_id": "A_LONG_STRING==",
  "product_name": "Dividend Cultivator Web App",
  "permalink": "mHSuk",
  "product_permalink": "https://gum.co/mHSuk",
  "email": "anonymous@gmail.com",
  "price": "1249",
  "currency": "usd",
  "quantity": "1",
  "order_number": "A_STRINGIFIED_INTEGER",
  "sale_id": "A_LONG_STRING==",
  "sale_timestamp": "2020-09-09T18:11:22Z",
  "subscription_id": "kjletlkjeqasdf==",
  "variants": {
    "Tier": "Base Subscription"
  },
  "offer_code": "an_discount_code_you_have_set_up",
  "license_key": "C14341FC-C14341FC-C14341FC-C14341FC",
  "ip_country": "Canada",
  "recurrence": "quarterly",
  "is_gift_receiver_purchase": "false",
  "refunded": "false",
  "resource_name": "sale",
  "disputed": "false",
  "dispute_won": "false",
  "url_params[_ga]": "2.6349685.1583997846.1600074293-639960653.1599804853"
}
```

You can also test it from the Terminal with `sls invoke local`:
```bash
sls invoke local -f catch-GR-webhook -d '{"Secret_Key":"WRITE-THE-SECRET-KEY-HERE","body": "seller_id=A_LONG_STRING%3D%3D&product_id=A_LONG_STRING%3D%3D&product_name=The%20DynamoDB%20Book%20-%20Plus%20Package&permalink=EZyTW&product_permalink=https%3A%2F%2Fgum.co%2FEZyTW&email=test%40testing.com&price=150&currency=usd&quantity=1&order_number=252699543&sale_id=GDxsfC0xDX9MI9i2i6d78A%3D%3D&is_gift_receiver_purchase=false&refunded=false&resource_name=sale&disputed=false&dispute_won=false&ip_country=Nigeria&url_params%5B_ga%5D=2.6349685.1583997846.1600074293-639960653.1599804853&sale_timestamp=2020-09-14T22%3A26%3A12Z"}'
```
The PII is all fake; you'll want to updated the sale_timestamp to be w/in 4 hours for the GA API call to not fail.


All the resources fit easily in the AWS Free Tier and should have no ongoing costs.

To take down the CloudFormation Stack and associated Lambda/Dynamo Tabe, use:
```
sls remove
```

If you want to check a particular purchase, lookup the ClientID with this GA Core Reporting API call (replace `VIEW_ID`, `CLIENT_ID`, and the `end-date`:
```
https://www.googleapis.com/analytics/v3/data/ga?ids=ga:VIEW_ID&start-date=2020-08-01&end-date=2020-09-21&metrics=ga:totalEvents,ga:eventValue,ga:sessions&dimensions=ga:dataSource,ga:dateHourMinute,ga:referralPath,ga:fullReferrer,ga:sourceMedium&filters=ga:clientId==CLIENT_ID&samplingLevel=HIGHER_PRECISION
```


A last note: Gumroad will retry the webhook up to 3 times (4 total invocations) over 15-20 minutes if you don't return a response to it. Both the Dynamo write and GA POST should upsert, rather than create duplicate entries, on each subsequent invocation of the same payload.
