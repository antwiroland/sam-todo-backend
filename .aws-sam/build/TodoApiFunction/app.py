import boto3
import os
import json
from boto3.dynamodb.conditions import Key
from datetime import datetime, timedelta

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])

def build_response(status_code, body):
    """Helper function to build consistent responses with CORS headers"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': 'https://main.d8nrjjr8w3276.amplifyapp.com',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent',
            'Access-Control-Allow-Credentials': 'true'
        },
        'body': json.dumps(body)
    }

def lambda_handler(event, context):
    print("=== TODO API CALLED ===")
    
    # Handle OPTIONS preflight request
    if event.get('httpMethod') == 'OPTIONS':
        return build_response(200, {'message': 'CORS preflight'})
    
    # Extract user from Cognito authorizer
    try:
        claims = event['requestContext']['authorizer']['claims']
        user_id = claims["sub"]
        user_email = claims.get("email")
    except KeyError:
        return build_response(401, {'error': 'Unauthorized - missing user claims'})
    
    method = event["httpMethod"]
    path = event["path"]

    print(f"User: {user_id}, Method: {method}, Path: {path}")

    try:
        if method == "GET" and path == "/tasks":
            # Get all tasks for user
            response = table.query(
                KeyConditionExpression=Key("UserId").eq(user_id)
            )
            
            return build_response(200, {
                'message': 'Tasks retrieved successfully',
                'tasks': response['Items']
            })

        elif method == "POST" and path == "/tasks":
            # Create new task
            body = json.loads(event["body"])
            task_id = body.get("TaskId")
            task_name = body.get("TaskName")
            expiry_hours = body.get("ExpiryHours", 24)  # default 24 hours
            expiry_date = datetime.utcnow() + timedelta(hours=expiry_hours)

            if not task_id or not task_name:
                return build_response(400, {'error': 'TaskId and TaskName are required'})

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
            
            return build_response(201, {
                'message': 'Task created successfully',
                'task': task_item
            })

        elif method == "PUT" and path == "/tasks":
            body = json.loads(event["body"])
            task_id = body.get("TaskId")
            new_status = body.get("Status")
            new_name = body.get("TaskName")

            if not task_id:
                return build_response(400, {'error': 'TaskId is required'})

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
                return build_response(400, {'error': 'Nothing to update'})

            table.update_item(
                Key={"UserId": user_id, "TaskId": task_id},
                UpdateExpression="SET " + ", ".join(update_expression),
                ExpressionAttributeValues=expression_values,
                ExpressionAttributeNames=expression_names,
                ReturnValues="ALL_NEW"
            )

            return build_response(200, {'message': f'Task {task_id} updated successfully'})

        elif method == "DELETE" and path == "/tasks":
            # Delete task
            body = json.loads(event["body"])
            task_id = body.get("TaskId")

            if not task_id:
                return build_response(400, {'error': 'TaskId is required'})

            table.delete_item(
                Key={"UserId": user_id, "TaskId": task_id}
            )

            return build_response(200, {'message': f'Task {task_id} deleted successfully'})

        else:
            return build_response(404, {'error': 'Endpoint not found'})

    except json.JSONDecodeError:
        return build_response(400, {'error': 'Invalid JSON in request body'})
    except Exception as e:
        print(f"Error: {str(e)}")
        return build_response(500, {'error': f'Internal server error: {str(e)}'})