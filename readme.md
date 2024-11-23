
Creating a virtual environment
$ virtualenv myenv 

Activate virtualenv
$ myenv\Scripts\activate

To run 
$ python app.py

#for docker
1.Build
$ docker build -t cicd_test . to build the Docker image.
2.Run
$ docker run -p 5000:5000 cicd_test to start the container.

Jenkins sucessfully build : 

![alt text](image.png)