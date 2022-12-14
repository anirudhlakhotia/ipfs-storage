from re import S
from flask import Flask, render_template, request, redirect, send_file, session
import pyrebase
import json
import subprocess
from werkzeug.utils import secure_filename
import os
import requests
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import bcrypt
from flask_cors import CORS, cross_origin
import time
from flask import make_response

from flask_session import Session


app = Flask(__name__)
# ALlow cross origin requests
session_value = {}
app.config["uploadFolder"] = "uploads/"
# cors = CORS(
#     app,
#     resources={r"/upload": {"origins": "http://localhost:3000"}},
#     supports_credentials=True,
# )

SESSION_TYPE = "filesystem"
app.config.from_object(__name__)
Session(app)
CORS(app)

# session["allowed_files"] = []
# session["UserID"] = "ObSYhNpRwSYcIeVI8vKWpMCB3tu2"
# session["UserName"] = "anirudhlakhotia"


def verify_hash(hash, passwd):
    ohash = hash
    salt = hash.split("$$")[0].encode()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=390000,
    )
    key = base64.urlsafe_b64encode(
        kdf.derive(passwd.encode() + app.secret_key.encode("utf-8"))
    )
    hash = salt + "$$".encode() + bcrypt.hashpw(key, salt)
    print(hash, ohash)
    if hash == ohash.encode():
        return True, key
    else:
        return False, 0


def encrypting(password, pepper):
    print("Encrypting")
    bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    print(salt)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=390000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(bytes + pepper.encode("utf-8")))
    hash = salt + "$$".encode() + bcrypt.hashpw(key, salt)
    return key, hash


def encrypt_file(filedata, key, filename):

    fernet = Fernet(key)
    encrypted = fernet.encrypt(filedata)
    a = open(app.config["uploadFolder"] + filename, "wb")
    a.write(encrypted)
    a.flush()
    a.close()


def decrypt_file(filename, key):
    fernet = Fernet(key)
    encrypted = open(
        app.config["uploadFolder"] + "encrypted_" + filename + "/" + filename, "rb"
    ).read()
    decrypted = fernet.decrypt(encrypted)
    a = open(app.config["uploadFolder"] + "decrypted" + filename, "wb")
    a.write(decrypted)
    a.flush()
    a.close()


def upload_file(file, hash):
    users = db.get().val()

    opp = subprocess.run(
        f"w3 put {file}", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
    )
    filename = file.split("/")[-1].replace(".", ",")
    filecid = opp.stdout.decode().split()[1]
    print(filename, filecid)
    data = {"data": [hash.decode(), filecid]}
    db.child(session["UserID"]).child(filename).set(data)


app.secret_key = "cre=ebrorU#Ipr&b#gibapreyAqlmLwufof+7ipo4uJa@rozi2"
app.config["uploadFolder"] = "uploads/"


config = {
    "apiKey": "AIzaSyCzeZb62c_LyBLVSGwMMiVWJ8frHp9dKi4",
    "authDomain": "test-ipfs-8d946.firebaseapp.com",
    "projectId": "test-ipfs-8d946",
    "storageBucket": "test-ipfs-8d946.appspot.com",
    "messagingSenderId": "72753508870",
    "appId": "1:72753508870:web:52d51c4f54bf06a83f4987",
    "databaseURL": "https://test-ipfs-8d946-default-rtdb.asia-southeast1.firebasedatabase.app/",
}

firebase = pyrebase.initialize_app(config)
auth = firebase.auth()
db = firebase.database()

# @app.route("/")
# def home_page():

#     if "UserName" in session:
#         return render_template("upload.html")
#     else:
#         return render_template("login.html")


@app.route("/files", methods=["GET"])
@cross_origin(origin="localhost", headers=["Content- Type", "Authorization"])
def getFiles():
    if request.method == "GET":
        print("HEADERS in FILES", request.headers)
        if "UserId" in session:

            d = db.child(session["UserID"]).get().val()
            lis = {}
            c = 0
            for i in d:
                lis[c] = i.replace(",", ".")
                c = c + 1
            return {"status": 200, "data": lis}
        else:
            return {"status": 400}


@app.route("/login", methods=["POST"])
@cross_origin(
    origin="http://localhost:3000",
    headers=[
        "Content-Type",
        "Authorization",
        "Access-Control-Allow-Origin",
        "Set-Cookie:true; SameSite=None;",
    ],
    supports_credentials=True,
)
def login():
    email = request.form.get("email")
    password = request.form.get("password")
    print(f"Email: {email} Password: {password}")
    try:
        user = auth.sign_in_with_email_and_password(email, password)
    except:
        return {"status": 400}
    print("Login Successful")
    UserInfo = auth.get_account_info(user["idToken"])
    session["Verified"] = UserInfo["users"][0]["emailVerified"]
    if session["Verified"]:
        session["UserName"] = user["displayName"]
        session["UserID"] = UserInfo["users"][0]["localId"]
        session["AllowedFiles"] = []
        for i in session:
            session_value[i] = session[i]
        return {
            "status": 200,
            "UserName": user["displayName"],
            "UserID": UserInfo["users"][0]["localId"],
            "verified": UserInfo["users"][0]["emailVerified"],
        }
    else:
        return {"status": 400}


@app.route("/register", methods=["POST"])
@cross_origin(origin="localhost", headers=["Content- Type", "Authorization"])
def registerUser():
    if request.method == "POST":
        try:
            username = request.form.get("username")
            email = request.form.get("email")
            passwd = request.form.get("password")
            cpasswd = request.form.get("cpassword")

            request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/signupNewUser?key={0}".format(
                config["apiKey"]
            )
            headers = {"content-type": "application/json; charset=UTF-8"}
            data = json.dumps(
                {
                    "email": email,
                    "password": passwd,
                    "returnSecureToken": True,
                    "displayName": username,
                }
            )

            request_object = requests.post(request_ref, headers=headers, data=data)
            out = request_object.json()
            auth.send_email_verification(out["idToken"])

            return {"status": 200}
        except Exception as e:
            print("Error is", e)
            return {"status": 400}


@app.route("/logout")
def logout():
    if "UserID" in session:
        d = db.child(session["UserID"]).get().val()
        for i in d:
            i = i.replace(",", ".")
            if os.path.exists(os.path.join(app.config["uploadFolder"], i, i)):
                os.remove(os.path.join(app.config["uploadFolder"], i, i))

            if os.path.exists(os.path.join(app.config["uploadFolder"], i)):
                os.rmdir(os.path.join(app.config["uploadFolder"], i))
            if os.path.exists(
                os.path.join(app.config["uploadFolder"], "decrypted" + i)
            ):
                os.remove(os.path.join(app.config["uploadFolder"], "decrypted" + i))
        session.pop("UserID", None)
        session.pop("UserName", None)
        return {"status": 200}
    else:
        return {"status": 400}


@app.route("/verify", methods=["POST"])
@cross_origin(origin="localhost", headers=["Content- Type", "Authorization"])
def download():
    session["UserID"] = "test"
    if request.method == "POST":

        if "UserID" in session:

            passwd = request.form.get("password")
            filename = request.form.get("filename").replace(".", ",")

            users = db.get().val()
            if session["UserID"] in users:

                cid = (
                    db.child(session["UserID"])
                    .child(filename)
                    .child("data")
                    .get()
                    .val()[-1]
                )
                shash = (
                    db.child(session["UserID"])
                    .child(filename)
                    .child("data")
                    .get()
                    .val()[0]
                )
                check, key = verify_hash(shash, passwd)
                if check:
                    file = filename.replace(",", ".")
                    session["allowed_files"].append(file)
                    os.system(
                        "w3 get {} -o {}".format(
                            cid, app.config["uploadFolder"] + "encrypted_" + file
                        )
                    )
                    decrypt_file(file, key)
                    file = "decrypted" + filename.replace(",", ".")
                    return {"status": 200}
                else:
                    return {"status": 400}
        else:
            return {"status": 400}


@app.route("/upload", methods=["GET", "POST"])
@cross_origin(origin="localhost", headers=["Content- Type", "Authorization"])
def uploadToServer():
    if request.method == "POST":
        print("Uploading")
        print(request.headers["Authorization"])
        session = request.headers["Authorization"].split(";")
        print(session)

        if "UserID" in session_value:

            print("uploading")
            for i in request.files:
                print(request.files[i])
            files = request.files.get("file")
            # print("Time taken to get files: ", new_time - Time) Most Time
            secretKey = request.form.get("key")
            filename = secure_filename(files.filename)
            filedata = files.read()
            key, hash = encrypting(secretKey, app.secret_key)
            encrypt_file(filedata, key, filename)
            print("Encrypted")
            t1 = time.time()
            upload_file(
                os.path.join(app.config["uploadFolder"], filename),
                hash,
            )
            t2 = time.time()
            print("Time taken to upload: ", t2 - t1)
            return {"status": "success"}
        else:
            print("Not logged in")

            return {"status": 400}


@app.route("/download/<file>", methods=["POST", "GET"])
@cross_origin(origin="localhost", headers=["Content- Type", "Authorization"])
def send_download(file):
    if request.method == "GET":
        if "UserID" in session:
            if file in session["allowed_files"]:

                print("Sending: " + app.config["uploadFolder"] + "decrypted" + file)
                return send_file(
                    app.config["uploadFolder"] + "decrypted" + file,
                    as_attachment=True,
                    attachment_filename=file,
                )
            else:
                return {"status": 400}
        else:
            return {"status": 400}


if __name__ == "__main__":
    app.run(debug=True)
