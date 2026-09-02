import datetime


def now_datetime():
	return datetime.datetime.now()


def nowdate():
	return datetime.date.today().isoformat()


def getdate(value):
	if isinstance(value, datetime.date):
		return value
	return datetime.date.fromisoformat(str(value))


def get_datetime(value):
	if value is None:
		return None
	if isinstance(value, datetime.datetime):
		return value
	return datetime.datetime.fromisoformat(str(value))
