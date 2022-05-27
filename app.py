from flask import Flask, render_template, url_for, redirect, Response
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError
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


EMAIL_ADDRS = 'prajwal.s.k.596@gmail.com'
EMAIL_PSWRD = 'elfpokeahrabhvva'

app = Flask(__name__)

app.config['SECRET_KEY'] = 'thisisasecretkey'


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)


class RegisterForm(FlaskForm):
    username = StringField(validators=[
                           InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[
                             InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})
    admin_key = PasswordField(validators=[
                             InputRequired(), Length(min=4, max=20)])

    submit = SubmitField('Register')

    def validate_username(self, username):
        existing_user_username = User.query.filter_by(
            username=username.data).first()
        if existing_user_username:
            raise ValidationError(
                'That username already exists. Please choose a different one.')

    def validate_adminkey(self, admin_key):
        if admin_key != 'Admin1':
            raise ValidationError(
                'Wrong admin key, Enter correct admin Key to register!')


class LoginForm(FlaskForm):
    username = StringField(validators=[
                           InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[
                             InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField('Login')


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for('dashboard'))
    return render_template('login.html', form=form)


@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    return render_template('dashboard.html')


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    send_mail(attendance_score)
    return redirect(url_for('login'))


@ app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit() and form.admin_key.data == 'Admin1':
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        new_user = User(username=form.username.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('register.html', form=form)


#######
path = './static/training_images'
images = []
known_face_names = []
myList = os.listdir(path)
print(myList)

camera = cv2.VideoCapture(0)

for cl in myList:
    curImg = cv2.imread(f'{path}/{cl}')
    images.append(curImg)
    known_face_names.append(os.path.splitext(cl)[0])
print(known_face_names)

pickle_off = open("encodingfile.txt", "rb")
known_face_encodings = pickle.load(pickle_off)
print('Encoding Complete')


face_locations = []
face_encodings = []
face_names = []
process_this_frame = True
attendance_score = {}


def markAttendance(name, score):
    if score != 1:
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
                    print(attendance_score)


def gen_frames():
    cap = cv2.VideoCapture(0)

    score = 0

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
                cv2.putText(img, name, (x1 + 6, y2 - 6), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 2)

                now = str(datetime.now().time())
                #sec_int = (int(float(now[6:8])))
                min_int = int(now[3:5])
                if min_int % 2 == 0:
                    markAttendance(name, score)
                    score = 0
        ret, buffer = cv2.imencode('.jpg', img)
        img = buffer.tobytes()
        yield (b'--frame\r\n'
        b'Content-Type: image/jpeg\r\n\r\n' + img + b'\r\n')


def send_mail(AttendanceScore):
    time = list(AttendanceScore.keys())
    scores = list(AttendanceScore.values())

    plt.bar(range(len(AttendanceScore)), scores, tick_label=time)
    plt.xlabel("time present")
    plt.ylabel("relative attention, presence")
    plt.title("plot showing relative attention of student every 3-min ")
    #plt.legend()
    plt.savefig('graph.pdf')
    #plt.show()

    msg = EmailMessage()
    msg['Subject'] = 'Engage-2022'
    msg['From'] = EMAIL_ADDRS
    msg['To'] = 'ma20btech11013@iith.ac.in'
    msg.set_content('pdf attached')
    with open('graph.pdf', 'rb') as f:
        file_data = f.read()
        #file_type = imghdr.what(f.name)
        file_name = f.name
    msg.add_attachment(file_data, maintype='pdf', subtype='pdf', filename=file_name)
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_ADDRS, EMAIL_PSWRD)

        smtp.send_message(msg)

    #os.remove('graph.pdf')


@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == "__main__":
    app.run(debug=True)
