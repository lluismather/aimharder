from datetime import datetime, timedelta, timezone
from requests import Session
from bookings.models import Booking
import time
from zoneinfo import ZoneInfo
from multiprocessing import Pool

# aimharder class

class AimHarderSession:

    def __init__(self, username, password):
        self.BOX_ID = 6869
        self.BOX_NAME = 'fullcrossfitvalencia'
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
        self.last_response = self.session.post(
            self.LOGIN_ENDPOINT,
            data = data
        )

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
        self.last_response = self.session.post(
            self.BOOKINGS_API_ENDPOINT,
            data = data
        )
    
    def check_booking_status(self):
        if self.last_response.status_code == 200:
            response = self.last_response.json()

            if "bookState" in response:

                match response['bookState']:
                    case -2:
                        print('You have spent all your classes')
                        return -2
                    case -1:
                        print('This class is full')
                        return -1
                    case -4:
                        print('You can\'t book classes with more than 1 days of anticipation')
                        return -4
                    case -5:
                        print('The reservation cannot be made because you have at least one outstanding payment')
                        return -5
                    case -7:
                        print('You can\'t book classes with less than 15 minutes of anticipation')
                        return -7
                    case -8:
                        print('You cannot make more than 1 reservations for the same class on a day')
                        return -8
                    case -12:
                        print(response['errorMssg'])
                        return -12
                    
            if "errorMssg" not in response and "errorMssgLang" not in response:
                print('Booking successful')
                return 1

        print('Booking failed')
        return 0
        
# main


def get_now():
    return datetime.now(tz=ZoneInfo('Europe/Berlin'))


def time_to_wait(booking, delta, now):
    return booking - delta - now


def book_session(args):

    idx, booking, user, delta, now = args
    booking_datetime = datetime.combine(booking.date, booking.time, tzinfo=ZoneInfo('Europe/Berlin'))
            
    while time_to_wait(booking_datetime, delta, now).seconds > 60:
        now = get_now()
        ttw = time_to_wait(booking_datetime, delta, now)
        if ttw.seconds < 60:
            break
        print(f'waiting {time_to_wait(booking_datetime, delta, now).seconds} seconds...')
        time.sleep(60)
    
    ttw = time_to_wait(booking_datetime, delta, now).seconds
    print('waiting ' + str(ttw) + ' seconds...')
    time.sleep(ttw)
    
    print('booking class for ' + user.name)
    aimharder = AimHarderSession(user.email, user.password)

    if aimharder.last_response.status_code == 200:

        print('login successful')
        retrieved_booking = Booking.objects.get(id=booking.id)

        if not retrieved_booking.time:
            print('booking already done, exiting...')
            return f'booking {idx} already done'

        aimharder.get_classes(retrieved_booking.date.strftime("%Y%m%d"))

        if aimharder.class_list['bookings']:

            print(f"found {len(aimharder.class_list['bookings'])} classes")

            try:
                workout = [
                    lesson for lesson in aimharder.class_list['bookings']
                    if lesson['timeid'] == f'{retrieved_booking.time.strftime("%H%M")}_60' 
                        and lesson['className'] == retrieved_booking.type
                ][0]
            except:
                workout = None

            if not workout:
                print('no class found, trying 90 mins')
                try:
                    workout = [
                        lesson for lesson in aimharder.class_list['bookings']
                        if lesson['timeid'] == f'{retrieved_booking.time.strftime("%H%M")}_90' 
                            and lesson['className'] == retrieved_booking.type
                    ][0]
                except:
                    workout = None

            xf_class = workout['className'] or 'Unknown'
            xf_box = workout['boxName'] or 'Full Crossfit Valencia'
            xf_coach = workout['coachName'] or 'Unknown Coach'
            xf_time = workout['time'] or 'Unknown Time'

            # book the class
            print('booking the class ' + xf_class + ' at ' + xf_time + ' with ' + xf_coach + ' at ' + xf_box)
            aimharder.book_class(workout['id'])

            if aimharder.last_response and aimharder.last_response.status_code == 200:
                aimharder.check_booking_status()
                retrieved_booking.time = "00:00:00"
                retrieved_booking.save()
            else:
                print('Booking failed')


def run():

    now = get_now()
    print("now is " + str(now))
    delta = timedelta(hours=22)
    slot_date = now + timedelta(days=1)
    slot_start = now + delta
    slot_end = now + delta + timedelta(minutes=15)

    print(f'checking bookings from {slot_start} to {slot_end}')

    bookings = Booking.objects.filter(
        date = slot_date,
        time__gte = slot_start.time(),
        time__lte = slot_end.time()
    ).order_by('time')

    if not bookings:
        print('no bookings found')

    # run this in parallel
    pool_args = [(idx, booking, booking.user, delta, now) for idx, booking in enumerate(bookings)]
    with Pool(2) as p:
        logs = p.map(book_session, pool_args)

    print(logs)
    # ends
