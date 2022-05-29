# all the necessary imports
import time
from flask import Flask, render_template, url_for, redirect, Response
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FileField
from wtforms.validators import InputRequired, Length, ValidationError
from werkzeug.utils import secure_filename
from flask_bcrypt import Bcrypt
import face_recognition
import os
import pickle
import numpy as np
import cv2
from datetime import datetime
import smtplib
import imghdr
from email.message import EmailMessage
import matplotlib.pyplot as plt

# the email-id from which the report mail will be sent
EMAIL_ADDRS = 'servermail314@gmail.com'
EMAIL_PSWRD = 'bskviayazdoerpmb'

# declaring the flask app
app = Flask(__name__)

# creating a secure secret key
app.config['SECRET_KEY'] = 'BE2910F1058BC3C4468D8DD209A4A864363'

# configuring the app
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True
app.config['UPLOAD_FOLDER'] = './static/Training_images'
db = SQLAlchemy(app)
# in app we're using Bcrypy for generating hashes for the students passwords stored in database
bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

Time = [0, 0]


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# declaring the class User, which will be stored in database and will be used for validation purpose
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)


# class Resisterform is to be filled by Admin,
# it will be used in web-form to register students in Database by admin
class RegisterForm(FlaskForm):
    username = StringField(validators=[
        InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[
        InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})

    admin_key = PasswordField(validators=[
        InputRequired(), Length(min=4, max=20)])

    submit = SubmitField('Register')


# Login form is to be filled by students
# it will be used to Validate students
class LoginForm(FlaskForm):
    username = StringField(validators=[
        InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[
        InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField('Login')


# UploadFileForm is to be filled by the Admin
# it will be used to add student photos in Training_images directory
class UploadFileForm(FlaskForm):
    file = FileField("File", validators=[InputRequired()])

    admin_key = PasswordField(validators=[InputRequired(), Length(min=4, max=20)])

    submit = SubmitField("Upload File")


# Our web apps home Route
@app.route('/')
def home():
    return render_template('home.html')


# route for login Form
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                logged_in_user = str(form.username.data)
                f_log = open('logins.txt', 'a')  # login records are maintained in logins.txt file
                f_log.writelines(f'{logged_in_user}\n')
                f_log.close()
                return redirect(url_for('dashboard'))
    return render_template('login.html', form=form)


# the main Dashboard, where attendance using face recognition and markAttendance() is taken
@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    Time[0] = time.time()
    return render_template('dashboard.html')


# on the Dashboard if you click for 'Submit and Logout',
# it will send your attendance report (by send_mail() function) to the Admin and log you out
@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    Time[1] = time.time()
    logout_user()
    send_mail(attendance_score)
    return redirect(url_for('login'))


# route for RedisteForm, can be filled only if Admin Key is entered,
# admin key is "Admin1"
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit() and form.admin_key.data == 'Admin1':
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        if User.query.filter_by(username=form.username.data).count() > 0:
            User.query.filter_by(username=form.username.data).delete()
            db.session.commit()
        new_user = User(username=form.username.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

    return render_template('register.html', form=form)


# route for filling form of UploadFileForm()
@app.route('/upload', methods=['GET', "POST"])
def upload():
    form = UploadFileForm()
    if form.validate_on_submit() and form.admin_key.data == "Admin1":
        file = form.file.data  # First grab the file
        file.save(os.path.join(os.path.abspath(os.path.dirname(__file__)), app.config['UPLOAD_FOLDER'],
                               secure_filename(file.filename)))  # Then save the file
        return render_template('upload.html', form=form)
    return render_template('upload.html', form=form)


### Face Recognition part

# path where student images(training images) for located, used for creating face encodings
path = './static/training_images'
images = []
known_face_names = []
myList = os.listdir(path)
print(myList)

# used for capturing the webcam, we can also add address of IP camera to view it through an IP camera
camera = cv2.VideoCapture(0)

# adding photos name to list of names, i.e. names of students of class
for cl in myList:
    curImg = cv2.imread(f'{path}/{cl}')
    images.append(curImg)
    known_face_names.append(os.path.splitext(cl)[0])
print(known_face_names)

# to increase efficiency and avoiding making face encoding everytime
# we stored the list of face encodings in the encodingfile.txt using pickling.py file,
# below we're just retrieving it
pickle_of = open("encodingfile.txt", "rb")
known_face_encodings = pickle.load(pickle_of)
print('Encoding Complete')

face_locations = []
face_encodings = []
face_names = []
process_this_frame = True

# attendance score is the dictionary with: keys as time, values as score
attendance_score = {}


def markAttendance(name, score, loggedin_user):
    if (score != 1):
        # we just maintain a csv file for additional records
        with open('Attendance.csv', 'r+') as f:
            myDataList = f.readlines()
            nameList = []
            for line in myDataList:
                entry = line.split(',')
                nameList.append(entry[0])
                if name not in nameList:
                    now = datetime.now()
                    dtString = now.strftime('%H:%M:%S')
                    f.writelines(f'\n{name},{dtString},{score}')
                    attendance_score[dtString] = score
                    print(loggedin_user, ':', attendance_score)


def gen_frames():
    cap = cv2.VideoCapture(0)

    score = 0
    # reading the last line of the logins.txt to find last user logged in
    # reading it as binary to speed up the process
    with open('logins.txt', 'rb') as f:
        try:  # catch OSError in case of a one line file
            f.seek(-2, os.SEEK_END)
            while f.read(1) != b'\n':
                f.seek(-2, os.SEEK_CUR)
        except OSError:
            f.seek(0)
        user_logged = f.readline().decode()

    user_logged = user_logged[:-1]
    print("\n\n\n", user_logged)
    # for streaming the webcam live
    while True:
        success, img = cap.read()

        small_frame = cv2.resize(img, (0, 0), None, 0.25, 0.25)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

        for encodeFace, faceLoc in zip(face_encodings, face_locations):
            matches = face_recognition.compare_faces(face_encodings, encodeFace)
            face_distances = face_recognition.face_distance(known_face_encodings, encodeFace)
            # print(faceDis)
            matchIndex = np.argmin(face_distances)

            if matches[matchIndex]:
                score += 1
                name = known_face_names[matchIndex].upper()
                y1, x2, y2, x1 = faceLoc
                y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.rectangle(img, (x1, y2 - 35), (x2, y2), (0, 255, 0), cv2.FILLED)
                # adding a rectangle showing name of the person in the stream
                cv2.putText(img, name, (x1 + 6, y2 - 6), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 2)

                now = str(datetime.now().time())
                min_int = int(now[3:5])
                # marking attendance every 3 min
                if min_int % 2 == 0:
                    markAttendance(name, score, user_logged)
                    score = 0
        ret, buffer = cv2.imencode('.jpg', img)
        img = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + img + b'\r\n')


def send_mail(Attendance_Score):
    times = list(Attendance_Score.keys())
    scores = list(Attendance_Score.values())

    # plotting the bargraph of students attendance using matplotlib
    plt.bar(range(len(Attendance_Score)), scores, tick_label=times)
    plt.xlabel("time present")
    plt.ylabel("relative attention, presence")
    plt.title("plot showing relative attention of student every 3-min ")
    plt.savefig('graph.pdf')
    attendance_score = {}

    class_time = (Time[1] - Time[0])/60
    time_absent = int(class_time - len(Attendance_Score)*2)
    msg = EmailMessage()
    msg['Subject'] = 'Engage-2022, Student attendance report'
    msg['From'] = EMAIL_ADDRS
    msg['To'] = 'clientmail31415@gmail.com'
    msg.set_content(f''' Attendance and Attention score report of Student\n
                         total time of class {class_time} min\n'
                         time absent in class {time_absent}\n
                         below pdf attached of relative attendance throughout class time''')
    with open('graph.pdf', 'rb') as f:
        file_data = f.read()
        file_name = f.name
    msg.add_attachment(file_data, maintype='pdf', subtype='pdf', filename=file_name)
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_ADDRS, EMAIL_PSWRD)

        smtp.send_message(msg)


@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == "__main__":
    app.run(debug=True)
