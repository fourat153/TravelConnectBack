import firebase_admin
from firebase_admin import credentials

cred = credentials.Certificate('app/config/travelconnect-caf0c-firebase-adminsdk-fbsvc-c0137b9f87.json')
firebase_admin.initialize_app(cred)