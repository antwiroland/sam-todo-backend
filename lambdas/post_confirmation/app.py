import boto3
import os
sns = boto3.client("sns")

def lambda_handler(event, context):
    """
    Triggered after a successful authentication in Cognito.
    Subscribes the user's email to the SNS topic for task expiry notifications.
    """
    try:
        email = event["userAttributes"]["email"]
        topic_arn = os.environ["TOPIC_ARN"]

        # Subscribe user to SNS topic
        response = sns.subscribe(
            TopicArn=topic_arn,
            Protocol="email",
            Endpoint=email
        )

        print(f"[PostAuth] Subscribed {email} to {topic_arn}")
        print(f"[PostAuth] Subscription ARN: {response['SubscriptionArn']}")

    except Exception as e:
        print(f"[PostAuth] Error subscribing user: {str(e)}")

    # Must always return event so Cognito login/signup continues
    return event