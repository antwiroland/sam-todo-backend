import boto3
import os
from datetime import datetime, timezone

dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")

TABLE_NAME = os.environ["TABLE_NAME"]
TOPIC_ARN = os.environ["TOPIC_ARN"]

table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    """
    Scheduled Lambda to mark expired tasks and notify users via SNS.
    Runs on a schedule (e.g., every hour).
    """
    now = datetime.now(timezone.utc)
    
    # Scan all tasks (for large tables, use pagination or a GSI for expiry)
    response = table.scan()
    tasks = response.get("Items", [])

    expired_count = 0

    for task in tasks:
        if task.get("Status") != "Pending":
            continue  # Only Pending tasks can expire
        
        expiry_date_str = task.get("ExpiryDate")
        if not expiry_date_str:
            continue  # No expiry date, skip
        
        expiry_date = datetime.fromisoformat(expiry_date_str)
        
        if expiry_date < now:
            # Update task status to Expired
            table.update_item(
                Key={"UserId": task["UserId"], "TaskId": task["TaskId"]},
                UpdateExpression="SET #S = :s",
                ExpressionAttributeNames={"#S": "Status"},
                ExpressionAttributeValues={":s": "Expired"}
            )
            expired_count += 1

            # Optionally notify user via SNS
            if task.get("UserEmail"):
                sns.publish(
                    TopicArn=TOPIC_ARN,
                    Message=f"Your task '{task['TaskName']}' has expired.",
                    Subject="Task Expired",
                    MessageAttributes={
                        "email": {"DataType": "String", "StringValue": task["UserEmail"]}
                    }
                )
    
    print(f"Expired tasks processed: {expired_count}")
    return {"expired_tasks": expired_count}
