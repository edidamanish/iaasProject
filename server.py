from flask import Flask, request, jsonify
import boto3
import json
import base64
import time
import threading
import boto3
import paramiko

#Details to access AWS resources
aws_access_key = '[AWS_ACCESS_KEY]'
aws_secret_key = '[AWS_SECRET_KEY]'
aws_region = 'us-east-1'
image_ami = "[IMAGE_AMI]"
ec2 = boto3.client('ec2', aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key, region_name=aws_region)
ec2_client = boto3.resource('ec2', aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key, region_name=aws_region)
ssm = boto3.client('ssm', aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key, region_name=aws_region)
instance_ids = []
ssh_key_file = 'project1.pem'
sqs = boto3.client('sqs', aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key, region_name=aws_region)
SQS_INPUT_QUEUE_URL = "[SQS_INPUT_QUEUE_URL]"
SQS_RETURN_QUEUE_URL = '[SQS_OUTPUT_QUEUE_URL]'

first_time = True
first_time_lock = threading.Lock()
result_dict = {}
result_dict_lock = threading.Lock()
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}

#POST method to receive the workload
app = Flask(__name__)
@app.route("/", methods=["POST"])
async def upload_file():
    global first_time
    if "myfile" not in request.files:
        return jsonify({"Error": "myfile missing"}), 400

    file = request.files["myfile"]
    
    if file.filename == "":
        return jsonify({"Error": "file name missing"}), 400

    if file and allowed_file(file.filename):
        with first_time_lock:
            if first_time:
                main_thread = threading.Thread(target=mainMethod)
                main_thread.start()
                first_time = False
        
        image_data = base64.b64encode(file.read()).decode('utf-8')
        image_json = {
            "image": image_data, 
            "image_name": file.filename
        }
        file_name_txt = file.filename.split('.')[0]
        image_message = json.dumps(image_json)
        sendMessageToSQSQueue(image_message)

        result = await receive_message_from_sqs_queue(file_name_txt)
        return jsonify(result)
    
    return jsonify({"Error": "Invalid file type"}), 400

def sendMessageToSQSQueue(message_body):
    response = sqs.send_message(QueueUrl = SQS_INPUT_QUEUE_URL, MessageBody = message_body)
    print('Message added to SQS queue : ', response)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

async def receive_message_from_sqs_queue(key):
    while True:
        with result_dict_lock:
            if key in result_dict:
                value = result_dict[key]
                del result_dict[key]
                return value
        time.sleep(20)

def startImageProcessingScript(instance_id):
    print("Connecting to Instance : ",instance_id)
    commands_to_run = [
        'cd app-tier/; python3 processScript.py'
    ]
    instance = ec2.describe_instances(InstanceIds=[instance_id])['Reservations'][0]['Instances'][0]
    instance_ip = instance['PublicIpAddress']
    cert = paramiko.RSAKey.from_private_key_file(ssh_key_file)
    ssh_client = paramiko.SSHClient()
    ssh_client.load_system_host_keys()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh_client.connect(instance_ip, username='ubuntu', pkey=cert)
        print("Connection established")
        for command in commands_to_run:
            print("Running command : ",command)
            stdin, stdout, stderr = ssh_client.exec_command(command)
            if stdout:
                print("Output of command : ",stdout.read().decode())
            if stderr: 
                print("Error running command : ",stderr.read().decode())
        
        ssh_client.close()
        print("Connection closed")
        ec2.terminate_instances(InstanceIds=[instance_id])
        print("Terminated Instance : ",instance_id)
    except Exception as e:
        print(f"Error connecting to instance {instance_id}: {str(e)}")

def createAndRunInstance(thread_id):
    response = ec2.run_instances(
        ImageId=image_ami,  
        InstanceType="t2.micro",
        KeyName="project1",
        MinCount=1,
        MaxCount=1,
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': 'app-instance' + str(thread_id)
                    }
                ]
            }
        ]
    )
    instance_id = response['Instances'][0]['InstanceId']
    print("Creating Instance : ",instance_id)
    instance = ec2_client.Instance(instance_id)
    instance.start()
    instance.wait_until_running()
    print("Running Instance : ",instance_id)
    #Wait for SSH init
    time.sleep(90)
    startImageProcessingScript(instance_id)



#Main method 
def mainMethod():

    global first_time
    print("Main method time clock 30s")
    time.sleep(30)

    #Get sqs queue attributes
    queue_attr = sqs.get_queue_attributes(
        QueueUrl=SQS_INPUT_QUEUE_URL,
        AttributeNames=[
            'ApproximateNumberOfMessages',
        ]
    )

    #Get number of messages in the input sqs queue
    message_count = int(queue_attr['Attributes']['ApproximateNumberOfMessages'])
    print("Num of Input queue messages : ", message_count)

    #Create threads wrt the message count
    num_threads = min(20, message_count)
    print("Num of threads created : ", num_threads)

    # Create a list to store thread objects
    threads = []
    for i in range(num_threads):
        thread = threading.Thread(target=createAndRunInstance, args=(i,))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()
    print("All threads finished processing")
    time.sleep(20)

    #Reading the output sqs queue
    while True:
        response = sqs.receive_message(
            QueueUrl=SQS_RETURN_QUEUE_URL,
            MaxNumberOfMessages=10,
            VisibilityTimeout=30 
        )   
    
        messages = response.get('Messages', [])
        if len(messages) == 0:
            with first_time_lock:
                first_time = True
                break

        for message in messages:
            message_body = json.loads(message['Body'])
            for key, value in message_body.items():
                sqs.delete_message(QueueUrl=SQS_RETURN_QUEUE_URL, ReceiptHandle=message['ReceiptHandle'])
                with result_dict_lock:
                    result_dict[key] = value
                    print('Writing', result_dict)

@app.route('/')
def index():
    return 'Web App with Python Flask!'

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)