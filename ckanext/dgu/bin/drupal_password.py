'''Does the same password hash function that Drupal 7 does.

Based on /var/www/drupal/dgud7/current/includes/password.inc
'''
import os
import hashlib
import math

DRUPAL_HASH_COUNT = 15
DRUPAL_HASH_LENGTH = 55

def user_hash_password(password):
    count_log2 = DRUPAL_HASH_COUNT
    return password_crypt(hashlib.sha512, password,
                          password_generate_salt(count_log2))

def password_generate_salt(count_log2):
    '''Returns 12 character string containing the iteration count and a random salt.'''
    output = '$S$'
    itoa64 = password_itoa64()
    output += itoa64[count_log2]
    output += password_base64_encode(drupal_random_bytes(6), 6)
    return output

def password_itoa64():
    '''For encoding an iteration count as a letter'''
    return './0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'

def drupal_random_bytes(count):
    # just using python here - not using this for new passwords
    return os.urandom(count)

def password_base64_encode(input, count):
    output = ''
    i = 0
    itoa64 = password_itoa64()
    while i < count:
        value = ord(input[i])
        i += 1
        output += itoa64[value & 0x3f]
        if i < count:
            value |= ord(input[i]) << 8
        output += itoa64[(value >> 6) & 0x3f]
        if i >= count:
            break
        i += 1
        if i < count:
            value |= ord(input[i]) << 16
        output += itoa64[(value >> 12) & 0x3f]
        if i >= count:
            break
        i += 1
        output += itoa64[(value >> 18) & 0x3f]

    return output


def password_crypt(hash_algo, password, setting):
    if len(password) > 512:
        return False
    setting = setting[:12]
    if setting[0] != '$' or setting[2] != '$':
        return False
    count_log2 = password_get_count_log2(setting)
    salt = setting[4:12]
    if len(salt) != 8:
        return False
    count = 1 << count_log2
    hash_ = hash_algo(salt + password).digest()
    for i in range(count):
        hash_ = hash_algo(hash_ + password).digest()

    len_ = len(hash_)
    output = setting + password_base64_encode(hash_, len_)
    expected = int(12 + math.ceil((8 * len_) / 6.0))
    if len(output) != expected:
        return False
    return output[:DRUPAL_HASH_LENGTH]

def password_get_count_log2(setting):
    itoa64 = password_itoa64()
    return itoa64.find(setting[3])


def user_check_password(password, stored_hash):
    '''Check whether a plain text password matches a stored hashed password.'''
    type_ = stored_hash[:3]
    if type_ == '$S$':
        hash_ = password_crypt(hashlib.sha512, password, stored_hash)
    elif type_ in ('$H$', '$P$'):
        hash_ = password_crypt(hashlib.md5, password, stored_hash)
    else:
        return False
    return hash_ and stored_hash == hash_

# tests
password = 'pass'
old_hash = '$S$DRiiw/cbErl17QbvDynMsdbUGxsy5HPTXg4L1j0dlG2iOJB35XP6'
hash_ = user_hash_password(password)
print hash_
print 'New hash', user_check_password('pass', hash_)
print 'Old hash', user_check_password('pass', old_hash)