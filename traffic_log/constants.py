
HOUR = range(24) # 0->23

DOW = range(1,8) # 1-6

SLOT = (0,12,13,24,25,30,36,37,48,49,54,55)

SPOT_TYPE = [
    "Live Read Promo",
    "Recorded Promo",
    "Live Read PSA",
    "Recorded PSA",
    "Underwriting Spot",
    "Pledge Liner",
    "Station ID",
    "Other"
    ]

DAY = (
    'Monday',
    'Tuesday',
    'Wednesday',
    'Thursday',
    'Friday',
    'Saturday',
    'Sunday',
    )

DOW_CHOICES = (zip(DOW, DAY))

DOW_DICT = dict(DOW_CHOICES)

DOW_REVERSED = dict(zip(DAY,DOW))

def dd(val):
    return "%d"%val if val>=10 else "0%d"%val

HOUR_CHOICES = [(x,dd(x)) for x in HOUR]

SLOT_CHOICES = [('','Slot')] + [(x,dd(x)) for x in SLOT]

SPOT_TYPE_CHOICES = ["Spot Type"] + SPOT_TYPE
