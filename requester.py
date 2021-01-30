import json
import datetime
import time
import logging
import threading
from pathlib import Path

import requests
from tqdm import tqdm

class chan4requester():
    def __init__(self, monitor, include_boards = None, exclude_boards = None, request_time_limit = 1, stream_log_level = logging.INFO, logfolderpath = 'logs'):
        self._base_save_path = Path().resolve()
        self._debuglog = False
        self._stream_log_level = logging.INFO
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
        self._logger.debug("Initialising Monitoring Thread")
        self._monitor_thread = threading.Thread(target=self._begin_monitoring)
        self._logger.debug("Starting Thread")
        self._monitor_thread.start()
        self._logger.debug("Monitoring Started")

    def end_monitoring(self):
        self._logger.info("Ending loop and closing monitoring thread")
        self.monitor=False
        self._monitor_thread.join()
        self._logger.info("Closed monitoring thread")

    def _load_old_monitors(self):
        self._update_monitoring_boards()
        self._logger.debug('Checking for past captures of old threads in previous instances')
        old_monitor_dict = {}
        old_threads = 0
        for board in self.monitoring_boards:
            timestamp = self._get_day()

            boardfolderpath = self._base_save_path / 'saves' / timestamp / 'threads_on_boards'
            boardfolderpath.mkdir(parents=True, exist_ok=True)
            threadpath = self._base_save_path / 'saves' / timestamp / 'threads' / board
            threadpath.mkdir(parents=True, exist_ok=True)

            good_boardpath_found = False
            for boardpath in boardfolderpath.iterdir():
                if boardpath.name.split("_")[0] == str(board):
                    good_boardpath = boardpath
                    good_boardpath_found = True

            if not good_boardpath_found:
                self._logger.info(f'No previous thread information for /{board}/, no old threads to monitor')
                continue
            old_monitor_dict[board] = {}

            with open(good_boardpath, 'r') as prev_threads_file:
                prev_threads = json.load(prev_threads_file)
                for page in prev_threads:
                    for threads in page['threads']:
                        old_monitor_dict[board][threads['no']] = [threads['last_modified'], threads['replies']]
                        old_threads += 1
            self._logger.debug(f'{len} past captures of old threads in previous instances discovered')    

        self.monitoring_threads = old_monitor_dict
        self._logger.debug(f'{old_threads} past captures of old threads in previous instances discovered')

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
        self._load_old_monitors()
        self._logger.debug("Old monitors retrieved")
        while self.monitor is True:
            self._logger.debug("Started loop")
            if self._check_new_boards:
                self._logger.debug("Started updating monitoring boards")
                self._update_monitoring_boards()
            self._update_monitoring_threads()
            self._logger.debug("updating posts on monitoring list")
            self._update_posts_on_monitoring_threadlist()

    def _update_monitoring_threads(self):
        self._logger.info('Beginning search for threads to monitor')
        self._posts_to_update = []
        death_count = 0
        birth_count = 0
        update_count = 0

        for board in self.monitoring_boards:
            threads_json = self.get_and_save_single_board_threadlist(board, with_return=True)
            threads_on_board = {}

            for page in threads_json:
                for thread in page['threads']:
                    threads_on_board[str(thread['no'])] = [thread['last_modified'], thread['replies']]

            if board in self.monitoring_threads:
                for thread in self.monitoring_threads[board]:
                    if thread in threads_on_board:
                        pass
                    else:
                        self._logger.debug(f'Thread died {board}/{thread}')
                        death_count +=1
                for thread in threads_on_board:
                    if thread in self.monitoring_threads[board]:
                        if self.monitoring_threads[board][thread][0] < threads_on_board[thread][0]:
                            self._logger.debug(f'Thread updated {board}/{thread}')
                            self._posts_to_update.append([board, thread])
                            self.monitoring_threads[board][thread] = threads_on_board[thread]
                            update_count += 1
                        else:
                            self._logger.debug(f'Do not need to update thread {board}/{thread}')
                    else:
                        self._logger.debug(f'New thread {board}/{thread}')
                        self._posts_to_update.append([board, thread])
                        self.monitoring_threads[board][thread] = threads_on_board[thread]
                        birth_count += 1
            else:
                self._logger.info(f'New Board updated to monitor list {board}')
                self.monitoring_threads[board] = threads_on_board
                for thread in threads_on_board:
                    self._logger.debug(f'New thread {board}/{thread}')
                    self._posts_to_update.append([board, thread])
                    birth_count += 1

        self._logger.info(f'Thread deaths in previous iteration: {death_count}')
        self._logger.info(f'Thread births in previous iteration: {birth_count}')
        self._logger.info(f'Thread updates in previous iteration: {update_count}')
        self._logger.info(f'{len(self._posts_to_update)} threads found to monitor.')

    def _update_posts_on_monitoring_threadlist(self):
        number_posts_in_iteration = len(self._posts_to_update)
        i = 1
        for board, post in tqdm(self._posts_to_update):
            start_time = time.time()
            self.get_and_save_thread(board, post)
            current_time_diff = (time.time() - start_time) * (number_posts_in_iteration - i)
            self._logger.debug(f'{i}/{number_posts_in_iteration}: Capturing post {post} in /{board}/ approximate seconds remaining in iteration {current_time_diff:n}')
            i += 1

    def _set_board_list(self):
        boards_info = self.get_chan_info_json()
        codes = [board['board'] for board in boards_info['boards']]
        return codes

    def _get_time(self):
        now = datetime.datetime.today()
        return now.strftime('_%H_%M_%S')

    def _get_day(self):
        now = datetime.datetime.today()
        return now.strftime('%Y_%m_%d')

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
        timestamp = self._get_day()
        if outpath is None:
            outpath = self._base_save_path / 'saves' / timestamp
        if filename is None:
            filename = 'boards.json'
        outpath.mkdir(parents=True, exist_ok=True)
        with open(outpath / filename, 'w') as outfile:
            json.dump(self.get_chan_info_json(), outfile, indent=2)

    def get_and_save_single_board_threadlist(self, board_code, outpath=None, filename=None, with_return=False):
        timestamp = self._get_day()
        if outpath is None:
            outpath = self._base_save_path / 'saves' / timestamp / 'threads_on_boards'
        if filename is None:
            filename = board_code + self._get_time() + '.json'
        outpath.mkdir(parents=True, exist_ok=True)
        threadlist = self.get_single_board_threadlist(board_code)
        for threads in outpath.iterdir():
            if threads.name.split("_")[0] == board_code:
                threads.unlink()
        with open(outpath / filename, 'w') as outfile:
            json.dump(threadlist, outfile, indent=2)
        if with_return:
            return threadlist

    def get_and_save_thread(self, board_code, op_ID, outpath=None, filename=None):
        timestamp = self._get_day()
        if outpath is None:
            outpath = self._base_save_path / 'saves' / timestamp / 'threads' / board_code
        outpath.mkdir(parents=True, exist_ok=True)

        if filename is None:
            filename = str(op_ID) + self._get_time() + '.json'
        fullname = outpath / filename
        new_thread = True
        for threads in outpath.iterdir():
            if threads.name.split("_")[0] == str(op_ID):
                with open(threads, 'r+') as outfile:
                    data = json.load(outfile)
                    data.update(self.get_thread(board_code, op_ID))
                    outfile.seek(0)
                    json.dump(data, outfile)
                new_thread = False
        if new_thread is True:
            with open(fullname, 'w') as outfile:
                json.dump(self.get_thread(board_code, op_ID), outfile, indent=2)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._logger.info("__exit__ called")

    def _setup_logging(self, logfolderpath):
        logfolder = self._base_save_path / logfolderpath
        logfolder.mkdir(parents=True, exist_ok=True)

        self._logger = logging.getLogger('4chan_requester')
        self._logger.setLevel(logging.DEBUG)
        self._log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s: %(threadName)s - %(message)s')

        self._streamlogs = logging.StreamHandler()
        self._streamlogs.setLevel(self._stream_log_level)
        self._streamlogs.setFormatter(self._log_formatter)
        self._logger.addHandler(self._streamlogs)

        self._infologpath = logfolder / ('info_log' + self._get_full_time() + '.log')
        self._infologfile = logging.FileHandler(self._infologpath)
        self._infologfile.setLevel(logging.INFO)
        self._infologfile.setFormatter(self._log_formatter)
        self._logger.addHandler(self._infologfile)

        if self._debuglog:
            self._debuglogpath = logfolder / ('debug_log' + self._get_full_time() + '.log')
            self._debuglogfile = logging.FileHandler(self._debuglogpath)
            self._debuglogfile.setLevel(logging.DEBUG)
            self._debuglogfile.setFormatter(self._log_formatter)
            self._logger.addHandler(self._debuglogfile)

        self._logger.debug("Logger Initalised")

# requester_instance = chan4requester(False)
# requester_instance.get_and_save_chan_info()
# requester_instance.get_and_save_single_board_threadlist('r')
# requester_instance.get_and_save_thread('r','17781240')

requester_instance = chan4requester(True)