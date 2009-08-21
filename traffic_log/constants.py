
HOUR = range(24)

DOW = range(1,8)

SLOT = (0,12,13,24,25,30,36,37,48,49)

SPOT_TYPE = [
    "Live Read Promo",
    "Recorded Promo",
    "Live Read Promo",
    "Recorded PSA",
    "Underwriting Spot",
    "Pledge Liner",
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

HOUR_CHOICES = [('','Hour')] + [(x,dd(x)) for x in HOUR]

SLOT_CHOICES = [('','Slot')] + [(x,dd(x)) for x in SLOT]

SPOT_TYPE_CHOICES = ["Spot Type"] + SPOT_TYPE

HOURBUCKET_CHOICES = (
    ('','Hour Bucket'),
    ('0,24','Every hour'),
    ('0,24,2','All even hours'),
    ('1,24,2','All odd hours'),
    ('0,24,3','Every three hours'),
    ('0,24,6','Every six hours')
    )

HOURBUCKET_DICT = dict(HOURBUCKET_CHOICES)
