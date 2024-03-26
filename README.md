1. **Problem statement**

Our project aims to create an elastic cloud application using Amazon Web Services (AWS) that offers image recognition services. Key objectives include:<br />
**Elasticity**: The app should automatically scale resources based on demand, optimizing resource use and cost-effectiveness.<br />
**Image Recognition**: Users upload .jpeg images, and the app returns the top recognition result based on a provided deep learning model.<br />
**Concurrency**: The app should handle multiple requests concurrently without missing any. Persistence: Input images and results are stored in separate S3 buckets for long-term storage. Resource Constraints: It should use a maximum of 20 instances and queue requests when that limit is reached.<br />
**Monitoring and Scaling**: The app should automatically monitor and scale resources based on the SQS queue's depth.<br />
**Regional Deployment**: Resources are sourced from the us-east-1 AWS region.<br />

2. **Design and implementation**<br />

2.1 **Architecture** <br />
<img width="919" alt="Screenshot 2024-03-26 at 12 56 18 PM" src="https://github.com/edidamanish/iaasProject/assets/22556985/3c697759-7e22-4192-9680-5a99d06fdc2a">

a) **Workload Generator:**<br />
Explanation: The multithreaded workload generator is used for testing and simulating concurrent requests in parallel to our application to ensure it performs as expected.<br />
Implementation: We are using the provided multithreaded workload generator which is producing multiple requests in parallel to our Web Tier.<br />

b) **Web Tier**:<br />
Explanation: The Web Tier serves as the primary gateway for user image recognition requests, managing various user interactions, concurrently receiving requests, and delivering corresponding responses to the workload generator<br />
Implementation: To facilitate these tasks, we utilized Flask, a web server framework, to handle incoming HTTP POST requests and provide timely responses. A crucial component within the Web Tier is the Controller, a custom program designed to monitor the depth of the Request SQS Queue and make scaling decisions based on the queue's current depth. In our application, we've adopted a strategy where the number of app instances is determined as Number_of_instances = min(sqs_queue_depth, 20). This approach ensures that we do not create more than 20 instances of app instances, maintaining resource efficiency.<br />
Furthermore, the Web Tier plays a pivotal role in scaling down operations. When there are no pending messages in the Request SQS Queue, it orchestrates the termination of app instances, optimizing resource utilization. Additionally, the Web Tier is responsible for handling responses from the Response SQS. It diligently stores these responses in a result dictionary, which is periodically checked by an asynchronous post request. If a corresponding key is found in the result dictionary, it promptly delivers the results to the appropriate requester, ensuring a seamless user experience.<br />

c) **App Tier**:<br />
Explanation: The App Tier assumes the pivotal role of processing image recognition tasks. Its primary functions encompass receiving image requests from the Web Tier via the SQS queue, executing deep learning model-based processing, persisting results in S3 buckets, and delivering the recognition outcomes.<br />
Implementation: Leveraging AWS EC2 instances, we've established the App Tier infrastructure. Its operational scale dynamically adjusts in response to the volume of messages in the queue, ensuring efficiency and resource optimization. Within the App Tier, we've carefully crafted logic for processing image recognition requests. This logic efficiently transforms responses into a structured JSON format, where each key corresponds to the image name and the associated value represents the result derived from the model.<br />
 Subsequently, these processed results are swiftly conveyed to the response SQS queue for further handling. Additionally, the App Tier excels in data persistence, ensuring the secure storage of input images in the designated S3 bucket. Likewise, the recognition outcomes are efficiently preserved in the form of key-value pairs within the output S3 bucket, promoting a seamless and organized process.<br />

d) **Auto-Scaling**:<br />
Explanation: Auto-scaling plays a pivotal role in ensuring that your application dynamically manages the count of EC2 instances to align with the fluctuating demand. It's the intelligence that keeps resource usage finely tuned to match the workload.<br />
Implementation: The auto-scaling mechanism, in this context, is intricately tied to the number of messages residing in the SQS queue. We've established a maximum limit of 20 concurrent EC2 instances, each responsible for processing an individual message from the queue. This architecture is designed to flexibly respond to shifts in demand.<br />
If the quantity of messages in the queue diminishes, it triggers the scaling down of EC2 instances. In essence, the application adapts seamlessly to the workload's ebb and flow, ensuring that it doesn't allocate excessive resources during periods of lower demand. This approach optimizes both cost efficiency and system performance, creating a harmonious balance between resources and requests.<br />

e) **SQS Queue (Request and Response)**:<br />
Explanation: The SQS Queue is used to queue incoming image recognition requests and responses. It helps manage the load on the App Tier and ensures requests are processed in order.<br />
Implementation: We set up two AWS Simple Queue Service (SQS) queues for this project -<br />
a) Request Queue was used to queue incoming image recognition requests<br />
b) Response Queue was used to queue the JSON responses after image recognition from the App Tier.<br />
We keep monitoring the depth of the Request queue for auto scaling the EC2 instances accordingly.<br />

f) **S3 Buckets (Input and Output)**:<br />
Explanation: S3 buckets are used for persistence. The Input S3 bucket stores uploaded images, while the Output S3 bucket stores recognition results.<br />
Implementation: We created two S3 buckets in the us-east-1 region, one for input and one for output. We upload the input images and store recognition results in these buckets.<br />

g) **Deep Learning Model**:<br />
Explanation: The deep learning model performs the image recognition task. It takes input images and returns recognition results.<br />
Implementation: We host the deep learning model on every EC2 instance created in the App Tier. The pretrained model is then invoked on the input images to get the recognition results.<br />

2.2 **Autoscaling** <br />

In this code, autoscaling is implemented dynamically to efficiently manage the number of EC2 instances based on the workload generated by the multi-workload generator.<br />
The autoscaling logic is driven by the controller in the code. It starts by assessing the number of threads generated by the multi-workload generator. These threads represent concurrent image recognition requests. The controller places these requests into the SQS queue for processing.<br />
After ensuring that all generated messages are loaded into the SQS queue, the controller evaluates the length of the queue. This queue length is crucial as it is used to control the number of EC2 instances that are created to handle the requests. To avoid overloading resources, the code limits the number of EC2 instances to a maximum of 20.<br />
If the length of the SQS queue is within the allowable limit (20 instances), the controller creates EC2 instances accordingly, and each instance is responsible for processing one of the queued messages concurrently. This ensures efficient resource utilization during periods of high demand.<br />
If the number of threads (representing incoming requests) reduces, indicating lower demand, the controller automatically scales down the number of EC2 instances to match the reduced workload. This dynamic scaling ensures that the application optimally utilizes resources, avoiding unnecessary costs during periods of lower demand.<br />
In essence, this autoscaling mechanism ensures that the application can adapt to varying workloads, scaling out to handle increased demand and scaling in to reduce resource usage when demand decreases. This approach optimizes both performance and cost-effectiveness, making the application efficient in processing image recognition requests.<br />

3. **Testing and evaluation**<br />

We performed the following steps for testing the application:<br />
1. Individual components which include the initial script, the Flask server, and the image classification code have been tested individually.<br />
2. We then tested the end-to-end flow using the workload_generator.py to send a single request and verify the output.This allowed us to verify that the entire workflow was functioning as expected.<br />
3. Then to assess the application's ability to scale, we used the multithread_workload_generator.py script to send multiple image recognition requests to the application (10 and 100). This allowed us to evaluate its capacity to handle multiple requests simultaneously.<br />
As mentioned in the requirements, all the following attributes of the application have been evaluated and the following are the corresponding outputs for both cases:<br />
**Test Case 1** : The output of the workload generator is correct.<br />
**Output** : The results have been compared with the given classification_results.csv file. The following are the screenshots of the console output after the workload generator is run for both cases(10 and 100).<br />

<img width="845" alt="Screenshot 2024-03-26 at 1 01 19 PM" src="https://github.com/edidamanish/iaasProject/assets/22556985/3196d645-555b-49f0-8246-0b57b22a7ddb">

<img width="844" alt="Screenshot 2024-03-26 at 1 01 34 PM" src="https://github.com/edidamanish/iaasProject/assets/22556985/dc213081-89e1-4ee0-a1fc-59247a3683ac">

**Test Case 2 **: The contents in the S3 buckets are correct. <br />
**Output** : The following are the screenshots of both input and output s3 bucket contents for both cases(10 and 100). <br />

<img width="847" alt="Screenshot 2024-03-26 at 1 02 18 PM" src="https://github.com/edidamanish/iaasProject/assets/22556985/b8b3c81f-5a36-47d2-af62-258305af71a9">

<img width="845" alt="Screenshot 2024-03-26 at 1 02 33 PM" src="https://github.com/edidamanish/iaasProject/assets/22556985/d79f95c7-0540-4fd5-b822-b5a808a3eaa1">

<img width="830" alt="Screenshot 2024-03-26 at 1 02 48 PM" src="https://github.com/edidamanish/iaasProject/assets/22556985/4016093e-2927-462a-b877-86d44b6b35bb">

<img width="831" alt="Screenshot 2024-03-26 at 1 03 01 PM" src="https://github.com/edidamanish/iaasProject/assets/22556985/eeb2a80d-a390-40f9-9bae-9cbeb8fc9eeb">

**Test Case 3** : The number of EC2 instances is correct.<br />
**Output** : As observed in the following screenshots, the auto scaling is happening as expected. 10 app instances were created for 10 requests and 20 were created for 100 requests.<br />

<img width="860" alt="Screenshot 2024-03-26 at 1 03 38 PM" src="https://github.com/edidamanish/iaasProject/assets/22556985/93a80c27-7c35-42a4-a99a-a4d07c85e40d">

<img width="854" alt="Screenshot 2024-03-26 at 1 03 55 PM" src="https://github.com/edidamanish/iaasProject/assets/22556985/ecccb22c-14ef-4e37-9419-62e1a98ef3b9">

**Test Case 4** : All the requests are processed within a reasonable amount of time.<br />
**Output** : The estimated time that took to see the output on the console was 4 mins 53 secs.<br/>



4. **Code**<br/>
4.1 **Files Description**<br/>
The zip folder has the following files:<br/>
Helper files<br/>
1. _README.md_ : Contains the information as mentioned in the submission requirements.<br/>
2. _requirements.txt_ : Contains the dependencies required to run the project on the machine.<br/>
3. _project1.pem_ : Contains the private key to authenticate and log into the ec2 instances.<br/>
Input/Test Files<br/>
4. _imagenet-100_ : Contains the 100 input image data files.<br/>
5. _multithread_workload_generator.py_ : The script file given to use for testing.<br/>
Source Code files<br/>
6. _createWebInstance.py_ :<br/>
● This is the initial script file that’s run on the local machine.<br/>
● It’s used to create the web-tier instance and run the controller script on it.<br/>
● It has the following methods:<br/>
○ createAndRunInstance() : Creates and runs an ec2 instance with the name “web-instance1”.<br/>
○ runFlaskServer() : Connects to the “web-instance1”, and runs the controller script (server.py) on the instance.<br/>
7. _server.py _:<br/>
● This is the flask server script file(controller) that runs on the “web-instance1”.<br/>
● It has the following main methods:<br/>
○ upload_file() :<br/>
■ It’s the main controller method to process the post request from<br/>the workload generator.
■ It creates the input json message with the image and its corresponding file name and adds it to the sqs_input_queue.<br/>
■ It asynchronously reads the output dict for the corresponding file name in the keys and returns the value.<br/>
○ mainMethod() :<br/>
■ It’s the main method to process the messages in the queue.<br/>
■ It creates threads based on the length of the sqs_input_queue.<br/>
■ It uses the “min(20, message_count)” logic so that the number of threads created are equal to the number of messages in the queue if less than 20 or 20 otherwise.<br/>
       
■ Each of these threads calls the “createAndRunInstance()” method. ■ After the threads are finished running, it creates an output dict from the messages in the sqs_output_queue and clears the queue.<br/>
○ createAndRunInstance() :<br/>
■ This method creates an ec2 instance with the name “app-instance{#thread-id}”.<br/>
■ It then calls the startImageProcessingScript() method.<br/>
○ startImageProcessingScript() :<br/>
■ This method connects to the app-tier ec2 instance and runs the processScript.py script file on the instance.<br/>
8. _processScript.py_ :<br/>
● It’s the main script file that’s run on the app-tier instances.<br/>
● It uses the code in the image_classification.py file given, with some additional elements added.<br/>
● It reads the messages from the sqs_input_queue and adds them to the s3 bucket named ‘project1inputimages’. It then does the image classification.<br/>
● It adds the output messages to the sqs_output_queue and to the S3 bucket named 'project1output' as well. Additionally It clears the sqs_input_queue after all the messages are processed.<br/>

4.2 **Steps to run the code**<br/>
1. Install dependencies mentioned in the requirements.txt file.<br/>
2. Run the createWebInstance.py script file.<br/>
3. Check the console output, wait for the web-tier instance to Create, Start and Run. You'll see the following line in the output. This IP will be the same every time.<br/>
"Running Instance on IP: 54.145.47.82"<br/>
4. Run the multithread_workload_generator.py script file to send requests. Use the following command(sample to send 100 requests):
python3 multithread_workload_generator.py --num_request 100 --url 'http://54.145.47.82:3000/' --image_folder "imagenet-100/"<br/>
5. After some time, you'll see the results being printed in the console in the following format:<br/>
test_65.JPEG uploaded! Classification result: "shower curtain"








