from datetime import datetime
from requests import Session
from bookings.models import Booking
import json

# aimharder class
class AimHarderSession:

    def __init__(self, email, password):
        # constants
        self.BOX_ID = 8244
        self.BOX_NAME = 'crossfitgrau'
        self.LOGIN_ENDPOINT = 'https://aimharder.com/login'
        self.CLASS_API_ENDPOINT = f'https://{self.BOX_NAME}.aimharder.com/api/bookings'
        self.BOOKINGS_API_ENDPOINT = f'https://{self.BOX_NAME}.aimharder.com/api/book'
        # variables
        self.email = email
        self.password = password
        self.session = Session()
        self.last_response = None
        self.class_list = None
        # login on init
        self.login()

    def login(self):
        data = {
            'mail': self.email,
            'pw': self.password,
            'login': 'Log in'
        }
        response = self.session.post(
            self.LOGIN_ENDPOINT,
            data = data
        )
        self.last_response = response

    def get_classes(self, date):
        class_list = self.session.get(
            self.CLASS_API_ENDPOINT,
            params = {
                'day': date,
                'family_id': '',
                'box': self.BOX_ID,
            }
        )
        self.class_list = class_list.json()

    def book_class(self, class_id):
        data = {
            'id': class_id,
            'box': self.BOX_ID,
            'family_id': '',
            'insist': 0,
        }
        response = self.session.post(
            self.BOOKINGS_API_ENDPOINT,
            data = data
        )
        self.last_response = response


# main

def run():

    tomorrow = datetime.now() # + timedelta(days=1)
    bookings = Booking.objects.filter(date=tomorrow)

    for booking in bookings:

        # log in
        print('logging in')
        aimharder = AimHarderSession(booking.user.email, booking.user.password)

        # if login successful
        if aimharder.last_response.status_code == 200:

            print('login successful')
            
            # get classes
            aimharder.get_classes(tomorrow.strftime("%Y%m%d"))

            # if there are classes
            if aimharder.class_list:

                print(f"found {len(aimharder.class_list['bookings'])} classes")

                # find the class
                workout = [
                    lesson for lesson in aimharder.class_list['bookings'] 
                    if lesson['timeid'] == f'{booking.time.strftime("%H%M")}_60' 
                        and lesson['className'] == booking.type
                ][0]

                # book the class
                print('booking the class')
                print(workout['className'] + ' @ ' + workout['boxName'] + ': ' + workout['coachName'] + ' ' +  workout['time'])
                aimharder.book_class(workout['id'])

                # if booking response successful
                if aimharder.last_response.status_code == 200:
                    
                    # parse response
                    bookstate = json.loads(aimharder.last_response.content.decode('utf-8'))
                    
                    # booking failed
                    if bookstate['bookState'] == -2:
                        
                        print('booking failed')

