import barnum
import boto3
import json
import random
import time
import uuid
import requests
from jinja2 import Template



def datastream():
    record = {
        "customer": str(barnum.create_name()[0]),
        "saleid": str(uuid.uuid4())[24:],
        "timestamp": str(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))),
        "coffee": random.choice(["Flat White","Americano","Macchiato","Cappuccino","Latte","Mocha","Cold Brew"]),
        "milk": random.choice(["Full Cream","Skinny","Soy","Almond","Oat"]),
        "size":random.choice(["Small","Regular","Large"]),
        "qty": random.choice([1, 1, 2, 2, 3, 4])
    }

    print("Sales Id:", record["saleid"], " Timestamp :", record["timestamp"], " Customer:",record["customer"], " Coffee:",
          record["coffee"], " Milk:", record["milk"], " Size:",record["size"], "Qty:", record["qty"])

    return record


def send_message(message):

    data = json.dumps(message)
    url = 'http://coffeeshop-nlb-a9444195ced48ebd.elb.ap-southeast-1.amazonaws.com/orders'
    #url= 'http://localhost:8080/orders'
    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(url, data=data, headers=headers)
    except Exception as e:
        print('Problem encountered: ', str(e))
    else:
        print('Status: ', response.status_code)

if __name__=="__main__":

    while True:
        message = datastream()
        send_message(message)
        #datastream()
        time.sleep(0.25)
        print()
