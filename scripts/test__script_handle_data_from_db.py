from datetime import datetime, timedelta
from model.alert import Period, HandleDataFromDB

end_date = datetime.today()
start_date = end_date - timedelta(days=5)

period = Period(start=start_date, end=end_date)



if __name__ == '__main__':
    hdl = HandleDataFromDB(period=period)
    result = hdl.get_data_from_db(meter_id=1)
    print(result)


