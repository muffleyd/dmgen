import os
import http.client
import http.cookiejar
import urllib.request
import urllib.parse
import urllib.error
import urllib.request
import urllib.error
import urllib.parse
import time
from io import StringIO

try:
    import gzip as _gzip
except ImportError:
    HEADER_ENCODING = {}
else:
    HEADER_ENCODING = {'Accept-encoding': 'gzip'}

_CookieJar = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def enable_cookies():
    global CookieJar
    CookieJar = _CookieJar


def disable_cookies():
    global CookieJar
    CookieJar = None


enable_cookies()

CHARSET = {}  # 'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7'}

# fools webserver into thinking I'm firefox, if they don't look too closely
# otherwise, sometimes it will not return nicely formated data
BROWSERHEADER = {}


def enable_firefox_mode():
    global BROWSERHEADER
    BROWSERHEADER['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/109.0'


def disable_firefox_mode():
    global BROWSERHEADER
    del BROWSERHEADER['User-Agent']


enable_firefox_mode()


def enable_chrome_mode():
    global BROWSERHEADER
    BROWSERHEADER['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36'


def disable_chrome_mode():
    global BROWSERHEADER
    del BROWSERHEADER['User-Agent']


def get_last_modified(response):
    return ('last-modified' in response.headers and
            time.mktime(time.strptime(response.headers.get('last-modified'),
                                      "%a, %d %b %Y %H:%M:%S GMT")) or 0)


class _special_response(urllib.response.addinfourl):
    astringio = StringIO()  # ???

    def __init__(self, obj, gzip=True, data=None, conv_unicode=True):
        if isinstance(obj, (list, tuple)):
            urllib.response.addinfourl.__init__(self, self.astringio, {}, obj[0], obj[1])
        else:
            urllib.response.addinfourl.__init__(self, obj.fp, obj.headers, obj.url, obj.code)

        if data is None:
            if gzip:
                self.data = _gzip.decompress(obj.read())
            else:
                self.data = obj.read()
        else:
            self.data = data
        if conv_unicode:
            contenttype = obj.headers.get('content-type')
            if contenttype and 'utf' in contenttype.lower():
                try:
                    encoding = contenttype[contenttype.index('=') + 1:]
                except ValueError:
                    pass
                else:
                    self.data = str(self.data, encoding)
        self.after = len(self.data) + 1
        self.index = 0
        self.read = self.read2

    def read2(self, amount=-1):
        if amount < 0:
            prevind = self.index
            self.index = self.after
            return self.data[prevind:]
        else:
            self.index += amount
            if self.index > self.after:
                self.index = self.after
            return self.data[self.index - amount:self.index]

    def seek(self, where):
        if where < 0:
            self.index = 0
        else:
            self.index = min(self.after, where)


def urlopen(url, data=None, read=True, header={}, firefox=BROWSERHEADER,
            dounicode=True, unquote=True, lastmod=0):
    header = dict(header)
    if lastmod:
        header['If-Unmodified-Since'] = time.ctime(lastmod)
    for i in HEADER_ENCODING:
        if i not in header:
            header[i] = HEADER_ENCODING[i]
    if firefox:
        for i in firefox:
            if i not in header:
                header[i] = firefox[i]
    if unquote:
        url = urllib.parse.unquote(url)
    try:
        try:
            response = (CookieJar and CookieJar.open or urllib.request.urlopen)(
                urllib.request.Request(url, data, header))
        except ValueError:
            response = (CookieJar and CookieJar.open or urllib.request.urlopen)(
                urllib.request.Request('http://' + url, data, header))
    except urllib.error.HTTPError as e:
        if lastmod and e.code in (304, 412):
            # 304 is unmodified-since
            # 412 is *-condition-failed
            response = _special_response((url, 412), False, '')
        else:
            raise
    if not isinstance(response, _special_response):
        response = _special_response(
            response,
            gzip=response.info().get('content-encoding') == 'gzip',
            conv_unicode=dounicode)
    if read:
        return response.read()
    return response


def httpConstructHostnameUrl(url):  # internal use, mostly
    url = url.strip()
    if url.find('http://') == 0:
        url = url[7:]
    slash = url.find('/')
    if slash != -1:
        server = url[:slash]
        url = url[slash:]
        if url == '':
            url = '/'
    else:
        server = url
        url = '/'
    return server, url


SOMESORTOFEXCEPTIONTEXT = 'Error "%d" while getting url "http://%s"'


def httpurlget(url, action="GET", server=None, only_on_200=True):
    hostname, url = httpConstructHostnameUrl(url)
    if not server:
        h = http.client.HTTPConnection(hostname)
    else:
        h = server
    h.request("GET", url,
              headers={  # 'Host': hostname,
                  # 'Accept-Encoding': 'gzip',
                  'User-Agent': 'Firefox/2.0.0.20'
              })
    # h.putheader('Host', hostname)
    #     h.putheader('User-Agent', 'Firefox/2.0.0.20')
    # h.endheaders()
    response = h.getresponse()

    if response.status == 200 or not only_on_200:
        data = response.read()
    else:
        global ERROR
        ERROR = response
        ex = http.client.HTTPException(SOMESORTOFEXCEPTIONTEXT
                                       % (response.status, hostname + url))
        raise ex
    if not server:
        h.close()
    return data


def save_from_web(url, filename=None, overwrite=False):
    if not filename:
        filename = os.path.basename(url)
    if os.path.exists(filename) and not overwrite:
        raise AttributeError('File exists and told to not overwrite.')
    data = urlopen(url)
    f = open(filename, 'wb')
    try:
        f.write(data)
    except:
        os.remove(f)
        raise
    finally:
        f.close()


always_safe = ('ABCDEFGHIJKLMNOPQRSTUVWXYZ'
               'abcdefghijklmnopqrstuvwxyz'
               '0123456789' '_.-')
_safe_map = {}
for i, c in zip(range(256), str(bytearray(range(256)))):
    _safe_map[c] = c if (i < 128 and c in always_safe) else '%{0:02X}'.format(i)
_safe_quoters = {}


# Taken from somewhere online years ago that I forgot to track, sorry!
def quote(s, safe='/', encoding=None, errors=None):
    """quote('abc def') -> 'abc%20def'

    Each part of a URL, e.g. the path info, the query, etc., has a
    different set of reserved characters that must be quoted.

    RFC 2396 Uniform Resource Identifiers (URI): Generic Syntax lists
    the following reserved characters.

    reserved    = ";" | "/" | "?" | ":" | "@" | "&" | "=" | "+" |
                  "$" | ","

    Each of these characters is reserved in some component of a URL,
    but not necessarily in all of them.

    By default, the quote function is intended for quoting the path
    section of a URL.  Thus, it will not encode '/'.  This character
    is reserved, but in typical usage the quote function is being
    called on a path where the existing slash characters are used as
    reserved characters.

    string and safe may be either str or unicode objects.

    The optional encoding and errors parameters specify how to deal with the
    non-ASCII characters, as accepted by the unicode.encode method.
    By default, encoding='utf-8' (characters are encoded with UTF-8), and
    errors='strict' (unsupported characters raise a UnicodeEncodeError).
    """
    # fastpath
    if not s:
        return s

    if encoding is not None or isinstance(s, str):
        if encoding is None:
            encoding = 'utf-8'
        if errors is None:
            errors = 'strict'
        s = s.encode(encoding, errors)
    if isinstance(safe, str):
        # Normalize 'safe' by converting to str and removing non-ASCII chars
        safe = safe.encode('ascii', 'ignore')

    cachekey = (safe, always_safe)
    try:
        (quoter, safe) = _safe_quoters[cachekey]
    except KeyError:
        safe_map = _safe_map.copy()
        safe_map.update([(c, c) for c in safe])
        quoter = safe_map.__getitem__
        safe = always_safe + safe
        _safe_quoters[cachekey] = (quoter, safe)
    if not s.rstrip(safe):
        return s
    return ''.join(map(quoter, s))


def quote_plus(s, safe='', encoding=None, errors=None):
    """Quote the query fragment of a URL; replacing ' ' with '+'"""
    if ' ' in s:
        s = quote(s, safe + ' ', encoding, errors)
        return s.replace(' ', '+')
    return quote(s, safe, encoding, errors)
