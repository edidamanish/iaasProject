import boto3
import base64
import os
from io import BytesIO
from PIL import Image
import time
import json
import os
import torch
import torchvision
import torchvision.transforms as transforms
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models
from urllib.request import urlopen
from PIL import Image
import numpy as np
import json
import sys
import time

# url = str(sys.argv[1])
#img = Image.open(urlopen(url))

# # AWS credential/s and configuration
aws_access_key = '[AWS_ACCESS_KEY]'
aws_secret_key = '[AWS_SECRET_KEY]'
aws_region = 'us-east-1'

# Initialize AWS clients
sqs = boto3.client('sqs', aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key, region_name=aws_region)
s3 = boto3.client('s3', aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key, region_name=aws_region)

# SQS queue URL
queue_url = "[SQS_INPUT_QUEUE_URL]"
return_queue_url = '[SQS_OUTPUT_QUEUE_URL]'

# S3 bucket name
image_bucket_name = 'project1inputimages'
output_bucket_name = 'project1output'

model = models.resnet18(pretrained=True)

model.eval()


while True:
    # Receive messages from the SQS queue
    response = sqs.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=1,
        VisibilityTimeout=30  # Adjust as needed
    )

    messages = response.get('Messages', [])

    if not messages:
        print("No more messages in the queue. Exiting the loop.")
        break

    for message in response.get('Messages', []):
        # Get the base64-encoded image data from the message
        message_body = json.loads(message['Body'])
        base64_image_data = message_body['image']

        # Decode base64 to bytes
        image_data = base64.b64decode(base64_image_data)


        img = Image.open(BytesIO(image_data))
        file_name = message_body['image_name']
        s3.put_object(Bucket=image_bucket_name, Key=file_name, Body=image_data)

        img_tensor = transforms.ToTensor()(img).unsqueeze_(0)
        outputs = model(img_tensor)
        _, predicted = torch.max(outputs.data, 1)
        with open('./imagenet-labels.json') as f:
            labels = json.load(f)
        result = labels[np.array(predicted)[0]]

        save_name = f"{file_name},{result}"
        # print(f"{save_name}")
        
        
        file_name_txt = file_name.split('.')[0]
        result_json = {
            file_name_txt: result
        }
        result_message = json.dumps(result_json)
        print(file_name_txt)
        s3.put_object(Bucket=output_bucket_name, Key=file_name_txt, Body=result_message, ContentType='application/json')
        sqs_response = sqs.send_message(QueueUrl = return_queue_url, MessageBody = result_message)
        sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=message['ReceiptHandle'])

        

    # Sleep for an interval before checking for more messages
    time.sleep(10) 