from collections import namedtuple
import pwd
import spwd
import re
import timekpr_service.dirs as dirs
import os
from logging import getLogger

User = namedtuple("User", ["username"])
TimeStatus = namedtuple("TimeStatus", ["time", "locked"])

log = getLogger(__name__)

###############################################################################
## Queries
###############################################################################
def io_user_list():
    """
    io_user_list() : iter(User)
    """
    # Read UID_MIN / UID_MAX variables
    (uidmin, uidmax) = _read_uid_minmax()

    # Check if the user is normal (not system user)
    for userinfo in spwd.getspall():
        if _isnormal(userinfo[0], uidmin, uidmax):
            yield User(userinfo[0])


def io_user(username):
    return next(
        (user for user in io_user_list()
         if user.username == username),
        None
    )

def io_timestatus(username):
    """
    io_timestatus(username : unicode()) : TimeStatus()
    """
    timef = os.path.join(dirs.WORK_DIR, username + '.time')
    lockf = os.path.join(dirs.WORK_DIR, username + '.lock')
    logoutf = os.path.join(dirs.WORK_DIR, username + '.logout')
    latef = os.path.join(dirs.WORK_DIR, username + '.late')

    if os.path.isfile(timef):
        with open(timef) as fh:
            try:
                time = int(fh.read())
            except:
                time = 0
    else:
        time = 0

    locked = (
        os.path.isfile(lockf) |
        os.path.isfile(logoutf) | 
        os.path.isfile(latef)
    )
    return TimeStatus(
        time,
        locked
    )


def io_update_timestatus(username, new_time_status):
    """
    io_timestatus(username : unicode(), time_status : TimeStatus())
    """
    time_status = io_timestatus(username)

    log.debug("old: {}, new {}".format(time_status, new_time_status))

    if new_time_status.locked is not None:
        time_status = time_status._replace(locked=new_time_status.locked)

    if new_time_status.time is not None:
        time_status = time_status._replace(time=new_time_status.time)

    _type_check_time_status(time_status)

    timef = os.path.join(dirs.WORK_DIR, username + '.time')
    lockf = os.path.join(dirs.WORK_DIR, username + '.lock')
    logoutf =  os.path.join(dirs.WORK_DIR, username + '.logout')
    latef = os.path.join(dirs.WORK_DIR, username + '.latef')


    if time_status.locked:
        with open(lockf, "w") as fh:
            fh.write("")
    else:
        _rm(lockf)
        _rm(logoutf)
        _rm(latef)

    with open(timef, "w") as fh:
        fh.write(str(time_status.time))


###############################################################################
## Internal
###############################################################################
def _type_check_time_status(time_status):
    if type(time_status.time) is not int:
        raise TypeError("TimeStatus.time is not an int")
    if type(time_status.locked) is not bool:
        raise TypeError("TimeStatus.time is not a boolean")        


# Check if it is a regular user, with userid within UID_MIN and UID_MAX.
def _isnormal(username, uidmin, uidmax):
    # NOTE: Hides active (current admin) user - bug #286529
    if os.getenv('SUDO_USER') and username == os.getenv('SUDO_USER'):
        return False

    # Check if read_uid_minmax() returned an error string
    if type(uidmin) == type(str()) and uidmin == "ERROR":
        return True

    userid = int(pwd.getpwnam(username)[2])
    if uidmin <= userid <= uidmax:
        return True
    else:
        return False

def _read_uid_minmax(f=dirs.LOGIN_DEFS):
    # NOTE: If problem with login.defs or variables, show all (system and normal) users -- bug #529770
    try:
        logindefs = open(f)
    except IOError:
        log.warning("Could not open file {0} -- cannot distinguish normal users from system users. All users will be shown.".format(logindefs))
        return ("ERROR", "ERROR")

    uidminmax = re.compile('^UID_(?:MIN|MAX)\s+(\d+)', re.M).findall(logindefs.read())
    # Check if uidminmax array has less than 2 items
    # If less, return "ERROR". Show all users, system and normal users. Show a warning popup
    if len(uidminmax) < 2:
        log.warning("Missing UID_MIN / UID_MAX variables -- Cannot distinguish normal users from system users. All users will be shown.")
        return ("ERROR", "ERROR")
    else:
        if uidminmax[0] < uidminmax[1]:
            uidmin = int(uidminmax[0])
            uidmax = int(uidminmax[1])
        else:
            uidmin = int(uidminmax[1])
            uidmax = int(uidminmax[0])
        return (uidmin, uidmax)

def _rm(f):
    try:
        os.remove(f)
    except OSError:
        pass
