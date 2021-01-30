import requests
from pathlib import Path
import json
import datetime
import time
import logging
import threading

class chan4requester():
    def __init__(self, monitor, include_boards = None, exclude_boards = None, request_time_limit = 1, stream_log_level = logging.INFO, logfolderpath = 'logs'):
        self._setup_logging(logfolderpath)

        self.monitor = monitor
        self._include_boards = include_boards
        self._exclude_boards = exclude_boards
        self._request_time_limit = request_time_limit
        self._check_new_boards = True

        self.last_request = None

        if self.monitor is True:
            self.begin_monitoring()

    def begin_monitoring(self):
        self._logger.info('Beginning monitoring')
        self.monitor = True
        self.monitoring_boards = []
        self.monitoring_threads = {}
        self._logger.debug("Initialising Moitoring Thread")
        self._monitor_thread = threading.Thread(target=self._begin_monitoring)
        self._logger.debug("Starting Thread")
        self._monitor_thread.start()
        self._logger.debug("Monitoring Started")

    def end_monitoring(self):
        self._logger.info("Ending loop and closing monitoring thread")
        self.monitor=False
        self._monitor_thread.join()
        self._logger.info("Closed monitoring thread")

    def set_include_exclude_boards(self, include_boards=False, exclude_boards=False):
        self._logger.info('Updating boards to monitor')
        self._include_boards = include_boards
        self._exclude_boards = exclude_boards
        if include_boards is False and exclude_boards is False:
            self._check_new_boards = False
        else:
            self._check_new_boards = True

    def _update_monitoring_boards(self):
        self._logger.debug('Updating monitor board list (checking)')
        if self._include_boards is not None:
            self.monitoring_boards = self._include_boards
        elif self._exclude_boards is not None:
            self.monitoring_boards = list(set(self._set_board_list()).difference(self._exclude_boards))
        else:
            self.monitoring_boards = self._set_board_list()
        self._check_new_boards = False

    def _begin_monitoring(self):
        self._logger.debug("_begin_monitoring entered")
        self._logger.debug("Initial Threads gathered ")
        while self.monitor is True:
            self._logger.debug("Started loop")
            if self._check_new_boards:
                self._logger.debug("Started updating monitoring boards")
                self._update_monitoring_boards()
            self._update_monitoring_threads()
            self._logger.debug("updating posts on monitoring list")
            self._update_posts_on_monitoring_threadlist()

    def _update_monitoring_threads(self):
        self._logger.debug('begin search for threads to monitor')
        self._posts_to_update = []
        for board in self.monitoring_boards:
            threads_json = self.get_single_board_threadlist(board)
            threads_on_board = {}

            for page in threads_json:
                for thread in page['threads']:
                    threads_on_board[thread['no']] = [thread['last_modified'], thread['replies']]

            if board in self.monitoring_threads:
                # Prune
                for thread in self.monitoring_threads[board]:
                    if thread not in threads_on_board:
                        self._logger.info(f'Thread died {board}/{thread}')
                # Add
                for thread in threads_on_board:
                    print(thread)
                    if thread in self.monitoring_threads[board]:
                        if self.monitoring_threads[board][thread][0] < threads_on_board[thread][0]:
                            self._logger.info(f'Thread updated {board}/{thread}')
                            self._posts_to_update.append([board, thread])
                            self.monitoring_threads[board][thread] = threads_on_board[thread]
                        else:
                            self._logger.debug(f'Do not need to update thread {board}/{thread}')
                    else:
                        self._logger.info(f'New thread {board}/{thread}')
                        self._posts_to_update.append([board, thread])
                        self.monitoring_threads[board][thread] = threads_on_board[thread]
            else:
                self._logger.info(f'New Board updated to monitor list {board}')
                self.monitoring_threads[board] = threads_on_board
                for thread in threads_on_board:
                    self._logger.info(f'New thread {board}/{thread}')
                    self._posts_to_update.append([board, thread])

        self._logger.debug(f'{len(self._posts_to_update)} threads found to monitor.')

    def _update_posts_on_monitoring_threadlist(self):
        for board, post in self._posts_to_update:
            self._logger.info(f'Capturing post {post} in {board}')
            self.get_and_save_thread(board,post)

    def _set_board_list(self):
        boards_info = self.get_chan_info_json()
        codes = [board['board'] for board in boards_info['boards']]
        return codes

    def _get_precise_time(self):
        now = datetime.datetime.today()
        return now.strftime('_%M_%S')

    def _get_hour(self):
        now = datetime.datetime.today()
        return now.strftime('%Y_%m_%d_%H')

    def _get_full_time(self):
        now = datetime.datetime.today()
        return now.strftime('%Y_%m_%d_%H_%M_%S')

    def _check_time_and_wait(self):
        if self.last_request is None:
            self.last_request = time.time()
            return
        else:
            if time.time() - self.last_request >= self._request_time_limit:
                self.last_request = time.time()
                return
            else:
                time.sleep(self._request_time_limit-(time.time() - self.last_request))
                self.last_request = time.time()
                return

    def get_chan_info_json(self):
        self._check_time_and_wait()
        r_boards = requests.get('http://a.4cdn.org/boards.json')
        self._logger.debug('chan information requested')
        return json.loads(r_boards.text)

    def get_single_board_threadlist(self, board_code):
        self._check_time_and_wait()
        r_thread_list = requests.get('https://a.4cdn.org/' + board_code + '/threads.json')
        self._logger.debug(f'Board {board_code} thread information requested')
        return json.loads(r_thread_list.text)

    def get_thread(self, board_code, op_ID):
        self._check_time_and_wait()
        r_thread = requests.get('https://a.4cdn.org/' + board_code + '/thread/' + str(op_ID) +'.json')
        return json.loads(r_thread.text)

    def get_and_save_chan_info(self, outpath=None, filename=None):
        timestamp = self._get_hour()
        if outpath is None:
            outpath = Path().resolve() / 'saves' / timestamp
        if filename is None:
            filename = 'boards.json'
        outpath.mkdir(parents=True, exist_ok=True)
        with open(outpath / filename, 'w') as outfile:
            json.dump(self.get_chan_info_json(), outfile)

    def get_and_save_board_threadlist(self, board_code, outpath=None, filename=None):
        timestamp = self._get_hour()
        if outpath is None:
            outpath = Path().resolve() / 'saves' / timestamp / 'threads_on_boards'
        if filename is None:
            filename = board_code + self._get_precise_time() + '.json'
        outpath.mkdir(parents=True, exist_ok=True)
        with open(outpath / filename, 'w') as outfile:
            json.dump(self.get_single_board_threadlist(board_code), outfile, indent=2)

    def get_and_save_thread(self, board_code, op_ID, outpath=None, filename=None):
        timestamp = self._get_hour()
        if outpath is None:
            outpath = Path().resolve() / 'saves' / timestamp / 'threads' / board_code
        if filename is None:
            filename = str(op_ID) + self._get_precise_time() + '.json'
        outpath.mkdir(parents=True, exist_ok=True)
        with open(outpath / filename, 'w') as outfile:
            json.dump(self.get_thread(board_code, op_ID), outfile, indent=2)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._logger.info("__exit__ called")

    def _setup_logging(self, logfolderpath):
        logfolder = Path('.').resolve() / logfolderpath
        logfolder.mkdir(parents=True, exist_ok=True)

        self._logger = logging.getLogger('4chan_requester')
        self._logger.setLevel(logging.DEBUG)
        self._debuglogpath = logfolder / ('debug_log' + self._get_full_time() + '.log')
        self._debuglogfile = logging.FileHandler(self._debuglogpath)
        self._debuglogfile.setLevel(logging.DEBUG)

        self._infologpath = logfolder / ('info_log' + self._get_full_time() + '.log')
        self._infologfile = logging.FileHandler(self._infologpath)
        self._infologfile.setLevel(logging.INFO)

        self._streamlogs = logging.StreamHandler()
        self._streamlogs.setLevel(logging.DEBUG)

        self._log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s: %(threadName)s - %(message)s')
        self._debuglogfile.setFormatter(self._log_formatter)
        self._infologfile.setFormatter(self._log_formatter)
        self._streamlogs.setFormatter(self._log_formatter)

        self._logger.addHandler(self._debuglogfile)
        self._logger.addHandler(self._infologfile)
        self._logger.addHandler(self._streamlogs)
        self._logger.debug("Logger Initalised")

# requester_instance = chan4requester(False)
# requester_instance.get_and_save_chan_info()
# requester_instance.get_and_save_board_threadlist('r')
# requester_instance.get_and_save_thread('r','17781240')

requester_instance = chan4requester(True, include_boards=['r'])