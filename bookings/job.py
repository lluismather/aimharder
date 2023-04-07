from datetime import datetime, timedelta
from requests import Session
from bookings.models import Booking


# constants

BOX_ID = 8244
BOX_NAME = 'crossfitgrau'
LOGIN_ENDPOINT = 'https://aimharder.com/login'
CLASS_API_ENDPOINT = f'https://{BOX_NAME}.aimharder.com/api/bookings'
BOOKINGS_API_ENDPOINT = f'https://{BOX_NAME}.aimharder.com/api/book'


# functions

def login(username, password):
    data = {
        'mail': username,
        'pw': password,
        'login': 'Log in'
    }
    session = Session()
    response = session.post(
        LOGIN_ENDPOINT,
        data = data
    )
    return [session, response]


def get_classes(session, date):
    class_list = session.get(
        CLASS_API_ENDPOINT,
        params = {
            'day': date,
            'family_id': '',
            'box': BOX_ID,
        }
    )
    return class_list.json()


def book_class(session, class_id):
    data = {
        'id': class_id,
        'box': BOX_ID,
        'family_id': '',
        'insist': 0,
    }
    response = session.post(
        BOOKINGS_API_ENDPOINT,
        data = data
    )
    return response


def run():

    tomorrow = datetime.now() + timedelta(days=1)
    bookings = Booking.objects.filter(date=tomorrow)

    for booking in bookings:

        # log in
        session, response = login(booking.user.email, booking.user.password)

        # if login successful
        if response.status_code == 200:
            
            # get classes
            class_list = get_classes(session, tomorrow.strftime("%Y%m%d"))

            # if there are classes
            if class_list['bookings']:

                # find the class
                workout = [
                    lesson for lesson in class_list['bookings'] 
                    if lesson['timeid'] == f'{booking.time.strftime("%H%M")}_60' 
                        and lesson['className'] == booking.type
                ][0]

                # book the class
                response = book_class(session, workout['id'])

