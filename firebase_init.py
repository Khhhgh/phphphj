import firebase_admin
from firebase_admin import credentials, db

# -------- بيانات اعتماد Firebase مباشرة --------
cred_dict = {
    "type": "service_account",
    "project_id": "thaker-17eb6",
    "private_key_id": "xxxxxx",
    "private_key": "-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY\n-----END PRIVATE KEY-----\n",
    "client_email": "firebase-adminsdk-xxxx@thaker-17eb6.iam.gserviceaccount.com",
    "client_id": "xxxxxxxxxxxx",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-xxxx%40thaker-17eb6.iam.gserviceaccount.com"
}

cred = credentials.Certificate(cred_dict)
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://thaker-17eb6-default-rtdb.firebaseio.com/'
})

# -------- دوال Firebase --------
def add_user(user_id):
    db.reference("/users").child(str(user_id)).update({"channels": []})

def user_exists(user_id):
    return db.reference("/users").child(str(user_id)).get() is not None

def add_channel(user_id, channel):
    ref = db.reference(f"/users/{user_id}/channels")
    channels = ref.get() or []
    if channel not in channels:
        channels.append(channel)
        ref.set(channels)

def remove_channel(user_id, channel):
    ref = db.reference(f"/users/{user_id}/channels")
    channels = ref.get() or []
    if channel in channels:
        channels.remove(channel)
        ref.set(channels)

def get_user_channels(user_id):
    return db.reference(f"/users/{user_id}/channels").get() or []

def set_mandatory_channel(channel):
    db.reference("/config").update({"mandatory_channel": channel})

def get_mandatory_channel():
    return db.reference("/config/mandatory_channel").get()

def get_all_users():
    users = db.reference("/users").get()
    return list(users.keys()) if users else []
