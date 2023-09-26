import os
import time
import pickle
import threading
from queue import Queue


class ResponseCache:
    CACHE_FILENAME = '_response_cache.pyp'

    def __init__(self, call_function=None, *, debug=True, cache_life=36000):
        self.call_function = call_function
        self.debug = debug
        self.cache_life = cache_life
        self.cache = {}

    def __enter__(self):
        self.load()
        self.start()
        return self

    def __exit__(self, *args):
        self.close()

    def start(self):
        self.lock = threading.Lock()
        self.queue = Queue()
        self.saver_thread = threading.Thread(target=self._saver_thread, daemon=True)
        self.saver_thread.start()

    def get_response(self, url, call_function=None):
        if not call_function:
            call_function = self.call_function
        if self.debug:
            print(url)
        # todo include options
        with self.lock:
            response, eol = self.cache.get(url, (None, None))
            if self.debug:
                if response:
                    print(url, len(response), eol, time.time())
                else:
                    print('not in cache', url)
            if eol is not None and eol < time.time():
                del self.cache[url]
                response = None
        if not response:
            retry = True
            while retry:
                response, retry = call_function(url)
            with self.lock:
                self.cache[url] = (response, time.time() + self.cache_life)
            self.save()
        return response


    # saving to the API is handled by a thread
    def _saver_thread(self):
        _EXIT = False
        while 1:
            # waits for a value to come into the queue
            val = self.queue.get()
            if self.debug:
                print('told to save')
            if not val or _EXIT:
                if self.debug:
                    print('exited')
                return
            # waits for .1 additional seconds to allow additional save requests to pile up
            time.sleep(.1)
            # obtains the API lock so api_call() can't modify the object during the pickle dump
            with self.lock:
                if self.debug:
                    print('clearing queue')
                # empty the queue in case there has been additional save requests
                for i in range(500):
                    if self.queue.empty():
                        break
                    val = self.queue.get()
                    if not val:
                        if self.debug:
                            print('save aborted, exiting')
                        _EXIT = True
                        break
                if self.debug:
                    print('trimming')
                self.trim()
                if self.debug:
                    print('saving')
                pickle.dump(self.cache, open(self.CACHE_FILENAME, 'wb'), 2)
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

    def load(self):
        if os.path.exists(self.CACHE_FILENAME):
            self.cache = pickle.load(open(self.CACHE_FILENAME, 'rb'))
        self.trim()

    def trim(self):
        # clear old values
        ct = time.time()
        for url in list(self.cache.keys()):
            eol = self.cache[url][1]
            if eol < ct:
                del self.cache[url]

    def close(self):
        self.queue.put(0)
