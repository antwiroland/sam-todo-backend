import boto3
import json
import os

cognito = boto3.client('cognito-idp')
client_id = os.environ['CLIENT_ID']


print("ENV CLIENT_ID:", os.environ.get("CLIENT_ID"))
print("client_id var in code:", client_id)


def build_response(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent',
            'Access-Control-Allow-Credentials': 'true'
        },
        'body': json.dumps(body)
    }

# --------------------
# Login
# --------------------
def login(event, context):
    try:
        body = json.loads(event['body'])
        username = body['username']
        password = body['password']

        print("Request body:", event['body'])
        print("Username:", username, "Password:", password)

        response = cognito.initiate_auth(
            AuthFlow='USER_PASSWORD_AUTH',
            ClientId=client_id,
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password
            }
        )

        return build_response(200, {
            'message': 'Login successful',
            'AuthenticationResult': response['AuthenticationResult']
        })

    except cognito.exceptions.NotAuthorizedException:
        return build_response(401, {'message': 'Invalid username or password'})
    except cognito.exceptions.UserNotFoundException:
        return build_response(401, {'message': 'User not found'})
    except Exception as e:
        return build_response(400, {'message': str(e)})

# --------------------
# Register
# --------------------
def register_user(event, context):
    try:
        body = json.loads(event['body'])
        username = body['username']
        password = body['password']
        email = body['email']

        response = cognito.sign_up(
            ClientId=client_id,
            Username=username,
            Password=password,
            UserAttributes=[
                {'Name': 'email', 'Value': email}
            ]
        )

        return build_response(200, {
            'message': 'User registered. Check your email for confirmation code.',
            'UserSub': response['UserSub']
        })

    except cognito.exceptions.UsernameExistsException:
        return build_response(400, {'message': 'User already exists'})
    except Exception as e:
        return build_response(400, {'message': str(e)})

# --------------------
# Confirm Registration
# --------------------
def confirm_user(event, context):
    try:
        body = json.loads(event['body'])
        username = body['username']
        code = body['code']

        cognito.confirm_sign_up(
            ClientId=client_id,
            Username=username,
            ConfirmationCode=code
        )

        return build_response(200, {'message': 'User confirmed successfully'})
    except Exception as e:
        return build_response(400, {'message': str(e)})

# --------------------
# Dispatcher
# --------------------
def lambda_handler(event, context):
    print("Auth Lambda invoked:", event.get("resource"), event.get("httpMethod"))

    if event.get('httpMethod') == 'OPTIONS':
        return build_response(200, {'message': 'CORS preflight'})

    path = event.get("resource")

    if path == "/auth" and event["httpMethod"].lower() == "post":
        return login(event, context)
    elif path == "/register" and event["httpMethod"].lower() == "post":
        return register_user(event, context)
    elif path == "/confirm" and event["httpMethod"].lower() == "post":
        return confirm_user(event, context)
    else:
        return build_response(404, {"message": "Not found"})
