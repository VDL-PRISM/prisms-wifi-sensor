import threading
import time
from functools import wraps

def retry(e, retries=4, delay=1, logger=None):
    """
    A decorator that will retry whatever function that it decorates a specified
    number of times with a delay period between each try. If the decorated
    function does not return a result that is *not* None, then this decorator
    will raise the supplied exception.

    :param e: The exception to raise if the retry count is exceeded.
    :param retries: The of retries that should be carried out.
    :param delay: The time delay between retries (seconds).
    :param logger: An optional logger to use.
    """

    def deco_retry(f):

        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries = retries
            while mtries > 0:
                result = f(*args, **kwargs)

                if result is None:
                    time.sleep(delay)
                    mtries -= 1

                    if logger:
                        msg = "Call to '{0}' failed to acquire a value... Retrying in {1} seconds.".format(f.__name__,
                                                                                                           delay)
                        logger.warning(msg)
                else:
                    return result

            raise e("Call to '{0}' failed to acquire a value in the retry period.".format(f.__name__))

        return f_retry

    return deco_retry


def get_mac(interface):
    """
    Gets the MAC address for the supplied interface or None if the MAC could
    not be read from the system.

    :param interface: The network interface whose MAC should be returned
    :return: The unique MAC address, or None otherwise.
    """

    try:
        result = open('/sys/class/net/{0}/address'.format(interface)).readline()[0:17]
    except IOError:
        result = None

    return result
