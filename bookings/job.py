from datetime import datetime, timedelta
from requests import Session
from bookings.models import Booking

# aimharder class
class AimHarderSession:

    def __init__(self, username, password):
        self.BOX_ID = 8244
        self.BOX_NAME = 'crossfitgrau'
        self.LOGIN_ENDPOINT = 'https://aimharder.com/login'
        self.CLASS_API_ENDPOINT = f'https://{self.BOX_NAME}.aimharder.com/api/bookings'
        self.BOOKINGS_API_ENDPOINT = f'https://{self.BOX_NAME}.aimharder.com/api/book'
        self.username = username
        self.password = password
        self.session = Session()
        self.last_response = None
        self.class_list = None
        self.date = None
        self.login()

    def login(self):
        data = {
            'mail': self.username,
            'pw': self.password,
            'login': 'Log in'
        }
        response = self.session.post(
            self.LOGIN_ENDPOINT,
            data = data
        )
        self.last_response = response

    def get_classes(self, date):
        self.date = date
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
            'day': self.date,
            'family_id': '',
            'insist': 0,
        }
        response = self.session.post(
            self.BOOKINGS_API_ENDPOINT,
            data = data
        )
        return response
    
    def check_booking_status(self):
        if self.last_response.status_code == 200:
            response = self.last_response.json()
            # error
            if "bookState" in response:
                match response['bookState']:
                    case -2:
                        print('You have spent all your classes')
                    case -1:
                        print('This class is full')
                    case -4:
                        print('You can\'t book classes with more than 1 days of anticipation')
                    case -5:
                        print('The reservation cannot be made because you have at least one outstanding payment')
                    case -7:
                        print('You can\'t book classes with less than 15 minutes of anticipation')
                    case -8:
                        print('You cannot make more than 1 reservations for the same class on a day')
                    
            if "errorMssg" not in response and "errorMssgLang" not in response:
                print('Booking successful')
                return

        print('Booking failed')
        

# main

def run():

    tomorrow = datetime.now() + timedelta(days=1)
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

                    #TODO check booking status and return errors
                    # have added case in check_booking_status
                    # but content returns big html string
                    # aimharder.check_booking_status()
                    print('Booking attempted. Check Aimharder to confirm your booking was made')
