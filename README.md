
# Attendance and Attention scoring web app

    This Web App is made with Flask (web framework) in python laguage,  
    It calculates the number of frames a user appears in span of every 3 minutes.
    Then it makes an attendance report, which is then sent to the instructer.
    here, instructors mail id is: clientmail31415@gmail.com and the servers mail id 
    is: servermail314@gmail.com.
    Passwords of both mail ids is: Qmpzg+123
    the mail is sent using smpt, and app passwords since google is removing support for
    less secure apps from 30 may it may not work later.
    
## Installation

Install python 3.8 (dlib wont work well for ther than 3.7 and 3.8 on windows) from https://www.python.org/downloads/
then install virtual environment, 
create a virtaul environment and then activate it using following commands

```bash
  pip install virtualenv
  virtalenv env
  virtualenv env .\env\Scripts\activate\ps1
```
clone the git repo
```bash
  git clone https://github.com/prajwal-3-14159/Engage-2022-face-detection.git
  cd Engage-2022-face-detection
```
install the requirements.
  
```bash
  pip install -r requirements.txt
``` 
Note. opencv is used as headless
You might face some issues with the dlib and face recognition follow the following steps in geeks for geeeks article
Use this url to install to face recognition library
https://www.geeksforgeeks.org/how-to-install-face-recognition-in-python-on-windows/

after installing the requirements,
run the app using 
```bash
   python app.py
```  
## Tech Stack

Flask web framewok, python, Bootsrap, html, css, sqlite, sqlalchemy 

