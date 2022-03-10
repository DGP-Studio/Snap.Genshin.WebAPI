import hashlib


def encrypt(key, timestamp):
    keyValue = key + timestamp[::-1] + "masterain"
    correctKey = hashlib.md5(keyValue.encode('utf-8')).hexdigest()
    print("Your key: " + correctKey)


encrypt("QdJ3#t%DTN_m[2S", "1646825290")
