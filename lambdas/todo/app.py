import boto3
import os
import json
from boto3.dynamodb.conditions import Key
from datetime import datetime, timedelta

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])

def lambda_handler(event, context):
    print("=== TODO API CALLED ===")
    
    # Extract user from Cognito authorizer
    claims = event['requestContext']['authorizer']['claims']
    user_id = claims["sub"]
    user_email = claims.get("email")
    
    method = event["httpMethod"]
    path = event["path"]

    print(f"User: {user_id}, Method: {method}, Path: {path}")

    try:
        if method == "GET" and path == "/tasks":
            # Get all tasks for user
            response = table.query(
                KeyConditionExpression=Key("UserId").eq(user_id)
            )
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'message': 'Tasks retrieved successfully',
                    'tasks': response['Items']
                })
            }

        elif method == "POST" and path == "/tasks":
            # Create new task
            body = json.loads(event["body"])
            task_id = body.get("TaskId")
            task_name = body.get("TaskName")
            expiry_hours = body.get("ExpiryHours", 24)  # default 24 hours
            expiry_date = datetime.utcnow() + timedelta(hours=expiry_hours)

            if not task_id or not task_name:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({'error': 'TaskId and TaskName are required'})
                }

            # Create task item
            task_item = {
                "UserId": user_id,
                "TaskId": task_id,
                "TaskName": task_name,
                "Status": "Pending",
                "UserEmail": user_email,
                "CreatedAt": datetime.utcnow().isoformat(),
                "ExpiryDate": expiry_date.isoformat()  # new field
            }

            
            table.put_item(Item=task_item)
            
            return {
                'statusCode': 201,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'message': 'Task created successfully',
                    'task': task_item
                })
            }

        elif method == "PUT" and path == "/tasks":
            body = json.loads(event["body"])
            task_id = body.get("TaskId")
            new_status = body.get("Status")
            new_name = body.get("TaskName")

            if not task_id:
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': 'TaskId is required'})
                }

            update_expression = []
            expression_values = {}
            expression_names = {}

            if new_status:
                update_expression.append("#S = :s")
                expression_values[":s"] = new_status
                expression_names["#S"] = "Status"
            if new_name:
                update_expression.append("TaskName = :n")
                expression_values[":n"] = new_name

            if not update_expression:
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': 'Nothing to update'})
                }

            table.update_item(
                Key={"UserId": user_id, "TaskId": task_id},
                UpdateExpression="SET " + ", ".join(update_expression),
                ExpressionAttributeValues=expression_values,
                ExpressionAttributeNames=expression_names,
                ReturnValues="ALL_NEW"
            )

            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'message': f'Task {task_id} updated successfully'})
            }

        
        elif method == "DELETE" and path == "/tasks":
            # Delete task
            body = json.loads(event["body"])
            task_id = body.get("TaskId")

            if not task_id:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({'error': 'TaskId is required'})
                }

            table.delete_item(
                Key={"UserId": user_id, "TaskId": task_id}
            )

            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'message': f'Task {task_id} deleted successfully'})
            }

        else:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Endpoint not found'})
            }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }