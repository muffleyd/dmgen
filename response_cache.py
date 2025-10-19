import os
import time
import base64
import json
import threading
from queue import Queue
from dmgen.timer import Timer

class ResponseCache:
    CACHE_FILENAME = '_response_cache.json'

    def __init__(self, call_function=None, *, debug=False, cache_life=36000, wait_for_close=True):
        self.call_function = call_function or self.value_not_cached
        self.debug = debug
        self.cache_life = cache_life
        self.do_wait_for_close = wait_for_close
        self.cache = {}
        self.loaded = False
        self.lock = threading.Lock()
        self.queue = Queue()
        self.saver_thread = None

    def __enter__(self):
        self.load()
        self.start()
        return self

    def __exit__(self, *args):
        self.close()
        if self.do_wait_for_close:
            self.wait_for_close()

    def start(self):
        if not self.saver_thread or not self.saver_thread.is_alive():
            self.saver_thread = threading.Thread(target=self._saver_thread, daemon=True)
            self.saver_thread.start()

    # A default method to call during get_response which throws an exception if the value isn't already cached.
    def value_not_cached(self, url):
        raise ValueError('Value not in cache and no response function was provided.')

    def get_response(self, url, call_function=None):
        if not call_function:
            call_function = self.call_function
        if self.debug:
            print('fetching', url)
        # todo include options
        with self.lock:
            response, is_bytes, eol = self.cache.get(url, (None, None, None))
            if self.debug:
                if response:
                    print('retrieved from cache', url, len(response), is_bytes, eol, time.time())
                else:
                    print('not in cache', url)
            if eol is not None and eol < time.time():
                del self.cache[url]
                response = None
        if response:
            if is_bytes:
                response = base64.b64decode(response)
        else:
            retry = True
            while retry:
                response, retry = call_function(url)
            with self.lock:
                # To be saved in json, bytes must be converted to ascii.
                is_bytes = isinstance(response, bytes)
                self.cache[url] = (
                    is_bytes and base64.b64encode(response).decode() or response,
                    is_bytes,
                    time.time() + self.cache_life
                )
            self.save()
        return response

    # saving to the API is handled by a thread
    def _saver_thread(self):
        _EXIT = False
        while 1:
            # waits for a value to come into the queue
            val = self.queue.get()
            if not val or _EXIT:
                if self.debug:
                    print('exited')
                return
            if self.debug:
                print('told to save')
            # waits for .1 additional seconds to allow additional save requests to pile up
            time.sleep(.1)
            # obtains the API lock so get_response() can't modify the object during the json dump
            with self.lock:
                if self.debug:
                    print('clearing queue')
                # empty the queue in case there has been additional save requests
                for _ in range(500):
                    if self.queue.empty():
                        break
                    val = self.queue.get()
                    if not val:
                        if self.debug:
                            print('wrapping up before exiting')
                        _EXIT = True
                        self.queue.put(0)
                        break
                if self.debug:
                    print('trimming')
                self.trim()
                if self.debug:
                    print('saving')
                with Timer(do_print=self.debug, before='dump to json '):
                    data = json.dumps(self.cache)
                with Timer(do_print=self.debug, before='write to file '):
                    with open(self.CACHE_FILENAME, 'w') as cache_file:
                        cache_file.write(data)
                if self.debug:
                    print('saved')

    def wait_for_close(self, timeout=10):
        if self.debug:
            print('waiting for saver thread to close')
        start_time = time.monotonic()
        while self.saver_thread.is_alive() and time.monotonic() - start_time < timeout:
            time.sleep(0.01)
        return not self.saver_thread.is_alive()

    # requests that the api save thread makes a save
    def save(self):
        self.queue.put(1)

    def load(self, force=False):
        if self.loaded and not force:
            return
        if os.path.exists(self.CACHE_FILENAME):
            with open(self.CACHE_FILENAME, 'r') as cache_file:
                self.cache = json.load(cache_file)
        # Handle out-of-date data structure.
        for key in list(self.cache.keys()):
            if len(self.cache[key]) == 2:
                response, end_of_life = self.cache[key]
                self.cache[key] = (response, False, end_of_life)
        self.trim()
        self.loaded = True

    def trim(self):
        # clear old values
        current_time = time.time()
        for url in list(self.cache.keys()):
            end_of_life = self.cache[url][-1]
            if end_of_life < current_time:
                del self.cache[url]

    def close(self):
        self.queue.put(0)
