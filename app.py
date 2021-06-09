from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from jinja2 import Template
import boto3
import json
import os
import requests

sqs = boto3.client("sqs", region_name='ap-southeast-1')
dynamodb = boto3.client('dynamodb', region_name='ap-southeast-1')

app = Flask(__name__, static_url_path='/')
CORS(app)


def ec2_container(file):
    with open(file, 'r') as f:
        metadata = f.read()
    metadata_json = json.loads(metadata)

    data = {
        "LaunchType": "EC2",
        "ContainerId": metadata_json['ContainerID'],
        "PublicIP": metadata_json['HostPublicIPv4Address'],
        "PrivateIP": metadata_json['HostPrivateIPv4Address'],
        "AZ": metadata_json['AvailabilityZone'],
        "HostPort": metadata_json['PortMappings'][0]['HostPort'],
        "ContainerPort": metadata_json['PortMappings'][0]['ContainerPort']
    }

    return data


def fargate_container(file):
    metadata_json = file

    data = {
        "LaunchType": metadata_json["LaunchType"],
        "ContainerId": metadata_json["Containers"][0]["DockerId"],
        "PublicIP": "",
        "PrivateIP": metadata_json["Containers"][0]['Networks'][0]['IPv4Addresses'],
        "AZ": metadata_json["AvailabilityZone"],
        "HostPort": "",
        "ContainerPort": ""
    }

    return data


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/healthcheck')
def healthCheckResponse():

    if 'ECS_CONTAINER_METADATA_FILE' in os.environ:
        metadatafile = os.environ['ECS_CONTAINER_METADATA_FILE']
        data = ec2_container(metadatafile)

    elif 'ECS_CONTAINER_METADATA_URI_V4' in os.environ:
        url = os.getenv('ECS_CONTAINER_METADATA_URI_V4')
        r = requests.get(f'{url}/task')
        data = fargate_container(r.json())
    else:
        data = {
            "LaunchType": 'Local',
            "ContainerId": '',
            "PublicIP": '',
            "PrivateIP": '',
            "AZ": '',
            "HostPort": '',
            "ContainerPort": ''
        }

    return render_template('healthcheck.html', LaunchType=data["LaunchType"],
                           ContainerId=data["ContainerId"],
                           PublicIP=data["PublicIP"],
                           PrivateIP=data["PrivateIP"],
                           AZ=data["AZ"],
                           HostPort=data["HostPort"],
                           ContainerPort=data["ContainerPort"])


@app.route('/orders', methods=['POST'])
def post_orders():
    queue_url = (sqs.get_queue_url(QueueName="QueueOne"))["QueueUrl"]
    if request.method == 'POST':
        response = request.get_json()
        with open('coffee-record-template.json', 'r') as fh:
            tmpl = fh.read()

        tm = Template(tmpl)
        msg = tm.render(Customer=response["customer"], SalesId=response["saleid"],
                        Timestamp=response["timestamp"], Coffee=response["coffee"],
                        Milk=response["milk"], Size=response["size"],
                        Quantity=response["qty"])

        # print(msg)
        try:
            response = sqs.send_message(QueueUrl=queue_url, DelaySeconds=10, MessageAttributes=json.loads(
                msg), MessageBody='Coffe Order')
        except Exception as e:
            print('ERROR: ', str(e))
        else:
            print("MessageId:", response["MessageId"])

    return msg


@app.route('/orders', methods=['GET'])
def get_orders():
    response = sqs.get_queue_attributes(
        QueueUrl=(sqs.get_queue_url(QueueName='QueueOne'))['QueueUrl'],
        AttributeNames=['ApproximateNumberOfMessages',
                        'ApproximateNumberOfMessagesNotVisible',
                        'ApproximateNumberOfMessagesDelayed']
    )

    ApproximateNumberOfMessages = response['Attributes']['ApproximateNumberOfMessages']
    ApproximateNumberOfMessagesNotVisible = response['Attributes']['ApproximateNumberOfMessagesNotVisible']
    ApproximateNumberOfMessagesDelayed = response['Attributes']['ApproximateNumberOfMessagesDelayed']

    response = sqs.get_queue_attributes(
        QueueUrl=(sqs.get_queue_url(QueueName='QueueTwo'))['QueueUrl'],
        AttributeNames=['ApproximateNumberOfMessages'])

    ApproximateNumberOfMessages = response['Attributes']['ApproximateNumberOfMessages']
    print('Number of Orders Going into the Queue:  ',
          ApproximateNumberOfMessages)

    response = dynamodb.scan(
        TableName=(dynamodb.list_tables(ExclusiveStartTableName='cpe'))[
            'TableNames'][0],
        Select='COUNT')

    dynamoItems = response['Count']
    print('Number of Orders recorded in the Database: ', dynamoItems)
    print('Number of Orders fullfilled:             ',
          ApproximateNumberOfMessagesNotVisible)
    print('Number of Orders the Process of being deliver to Customer: ',
          ApproximateNumberOfMessagesDelayed)

    return render_template('orders.html', ApproximateNumberOfMessagesNotVisible=ApproximateNumberOfMessagesNotVisible,
                           ApproximateNumberOfMessagesDelayed=ApproximateNumberOfMessagesDelayed,
                           ApproximateNumberOfMessages=ApproximateNumberOfMessages,
                           dynamoItems=dynamoItems)


if __name__ == '__main__':
    app.run('0.0.0.0', 8080, debug=True)
