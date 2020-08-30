# Gumroad-Webhook-to-DynamoDB

# Setup


Set environment variables
```
export SECRET_KEY="foobar"
export SENTRY_DSN="foo@bar.co"
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
  "sale_timestamp": "2020-06-09T18:11:22Z",
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
  "dispute_won": "false"
}```


All the resources fit easily in the AWS Free Tier and should have no ongoing costs (presuming you stay in the Free Tier, particularly on S3 storage).

To take down the CloudFormation Stack and associated Lambda/Dynamo Tabe, use:
```
sls remove
```
