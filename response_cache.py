import os
from dataclasses import dataclass
import sqlite3
import time
import threading
from queue import Empty, Queue
import traceback


SAVE = 1
CLOSE = 2


@dataclass
class ResponseCache:
    call_function: callable = None
    debug: bool = False
    cache_life: int = 36000
    wait_for_close: bool = True
    filename: str = '_response_cache.sqlite3'

    def __post_init__(self):
        if not self.call_function:
            self.call_function = self.value_not_cached
        self.db = None
        self.saver_thread = None
        self.queue = Queue()
        self.lock = threading.Lock()

    def __enter__(self):
        self.db = self.connect()
        if not self.saver_thread or not self.saver_thread.is_alive():
            self.saver_thread = threading.Thread(target=self._saver_thread, daemon=True)
            self.saver_thread.start()
        return self

    def __exit__(self, *args):
        # Close the saver thread.
        self.queue.put(CLOSE)
        self.wait_for_close(self)
        self.db.close()

    def connect(self):
        if not os.path.exists(self.filename):
            self.create_db()
        with self.lock:
            if self.db:
                # Test for a closed db connection.
                try:
                    self.db.cursor()
                except Exception:
                    self.db = None
            if not self.db:
                if self.debug:
                    print('connecting to database', self.filename)
                self.db = sqlite3.connect(self.filename, check_same_thread=False)
        return self.db

    def create_db(self):
        db = sqlite3.connect(self.filename)
        try:
            c = db.cursor()
            # A list of all data.
            c.execute('CREATE TABLE data (key text, data text, time real)')
            db.commit()
        except:
            try:
                db.close()
            except:
                pass
            os.remove(self.filename)
            raise
        else:
            db.close()

    # Requests that the api save thread makes a save.
    def save(self):
        self.queue.put(SAVE)

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
            data = self.db.execute('SELECT data, time from data WHERE key = ?', [url]).fetchone()
            if data:
                response, eol = data
            else:
                response = eol = None
            if self.debug:
                if response:
                    print('retrieved from cache', url, len(response), eol, time.time())
                else:
                    print('not in cache', url)
            if eol is not None and eol < time.time():
                self.db.execute('DELETE from data WHERE key = ?', [url])
                self.save()
                response = eol = None
        # @todo Allow response to be None.
        if not response:
            retry = True
            while retry:
                response, retry = call_function(url)
            with self.lock:
                args = [url, response, time.time() + self.cache_life]
                self.db.execute('INSERT INTO data (key, data, time) VALUES (?, ?, ?)', args)
                self.save()
        return response

    def _saver_thread(self):
        try:
            self._saver_thread_inner()
        except Exception as e:
            if self.debug:
                print(traceback.format_exc())
            raise

    # Saving to the API is handled by a thread.
    def _saver_thread_inner(self):
        next_save_time = 0
        save_flag = False
        exit = False
        while 1:
            try:
                # Waits for a value to come into the queue.
                # Times out every 0.01 seconds to allow the deferred save to work.
                val = self.queue.get(True, 0.01)
            except Empty:
                val = None
            if val == CLOSE:
                if self.debug:
                    print('exit queued')
                exit = True
                # Set the next save time such that if the save flag is set it
                # will save before ending the thread.
                next_save_time = 0
            if save_flag:
                if time.monotonic() >= next_save_time:
                    if self.debug:
                        print('saving')
                    with self.lock:
                        self.db.commit()
                    if self.debug:
                        print('saved')
                    save_flag = False
            elif val == SAVE:
                if self.debug:
                    print('told to save')
                save_flag = True
                next_save_time = time.monotonic() + 0.1
            if exit:
                if self.debug:
                    print('vacuuming')
                with self.lock:
                    self.db.execute('vacuum')
                if self.debug:
                    print('exiting')
                return

    def wait_for_close(self, timeout=10):
        if self.debug:
            print('waiting for saver thread to close')
        start_time = time.monotonic()
        while self.saver_thread.is_alive() and time.monotonic() - start_time < timeout:
            time.sleep(0.01)
        return not self.saver_thread.is_alive()
