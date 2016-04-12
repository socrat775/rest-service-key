import pymongo
from string import ascii_letters
from random import shuffle

db = pymongo.MongoClient().test
all_symbol = ascii_letters + ''.join(str(i) for i in xrange(0, 10))
db.all_keys.create_index([('key', pymongo.ASCENDING),
                          ('status', pymongo.ASCENDING)], unique=True)
keys = []
for _1 in all_symbol:
   for _2 in all_symbol:
      for _3 in all_symbol:
         for _4 in all_symbol:
            keys.append(''.join((_1, _2, _3, _4)))

shuffle(keys)
for key in keys:
    db.all_keys.save({'key': key, 'status': 0})

