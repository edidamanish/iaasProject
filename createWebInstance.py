import boto3
import paramiko
import time

#Details to access AWS resources
aws_access_key = '[AWS_ACCESS_KEY]'
aws_secret_key = '[AWS_SECRET_KEY]'
aws_region = 'us-east-1'
web_instance_ami = "[WEB_INSTANCE_AMI]"
ssh_key_file = 'project1.pem'

ec2 = boto3.client('ec2', aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key, region_name=aws_region)
ec2_client = boto3.resource('ec2', aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key, region_name=aws_region)
ssm = boto3.client('ssm', aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key, region_name=aws_region)

def runFlaskServer(instance_ip):
    
    cert = paramiko.RSAKey.from_private_key_file(ssh_key_file)
    ssh_client = paramiko.SSHClient()
    ssh_client.load_system_host_keys()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh_client.connect(instance_ip, username='ubuntu', pkey=cert)
        command = 'cd app-tier/; python3 server.py'
        print("Connection established")
        stdin, stdout, stderr = ssh_client.exec_command(command)

        # Continuously read and print the output
        for line in iter(stdout.readline, ''):
            print(line, end='')

    except Exception as e:
        print(f"Error connecting to instance : {str(e)}")

def createAndRunInstance():
    response = ec2.run_instances(
        ImageId=web_instance_ami,  
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
                        'Value': 'web-instance1'
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
    # Associate the existing/new Elastic IP with the EC2 instance
    eip=(ec2.describe_addresses())['Addresses'][0]
    instance_ip = eip['PublicIp'] 
    ec2.associate_address(InstanceId=instance_id, PublicIp=instance_ip)
    print("Starting Instance : ",instance_id)
    #Wait for SSH init
    time.sleep(90)
    instance = ec2.describe_instances(InstanceIds=[instance_id])['Reservations'][0]['Instances'][0]
    print("Running Instance on IP: ", instance_ip)
    runFlaskServer(instance_ip)

createAndRunInstance()