import requests
from pathlib import Path
import json
import datetime

class requester():
    def __init__(self, monitor):
        self._refresh_limit = None
        self.monitor = monitor
        self._include_boards = None
        self._exclude_boards = None
        self.monitoring_boards = None
        self.monitoring_threads = None
        
        if self.monitor == True:
            self._begin_monitoring()
        
    def _begin_monitoring(self):
        if self._include_boards is not None:
            self.monitoring_boards = self._include_boards
        elif self._exclude_boards is not None:
            self.monitoring_boards = list(set(self._set_board_list()).difference(self._exclude_boards))
        else:
            self.monitoring_boards = self._set_board_list()

    def _set_board_list(self):
        boards_info = self.get_board_info_json()
        return ['r', 'wsg']

    def _get_precise_time(self):
        now = datetime.datetime.today()
        return now.strftime('_%M_%S')

    def _get_hour(self):
        now = datetime.datetime.today()
        return now.strftime('%H_%d-%m-%Y')

    def get_board_info_json(self):
        r_boards = requests.get('http://a.4cdn.org/boards.json')
        return json.loads(r_boards.text)

    def get_and_save_board_info_json(self, outpath=None, filename=None):
        timestamp = self._get_hour()
        if outpath is None:
            outpath = Path().resolve() / 'saves' / timestamp
        if filename is None:
            filename = 'boards.json'
        outpath.mkdir(parents=True, exist_ok=True)
        with open(outpath / filename, 'w') as outfile:
            json.dump(self.get_board_info_json(), outfile)

    def get_single_board(self, board_code):
        r_thread_list = requests.get('https://a.4cdn.org/' + board_code + '/threads.json')
        return json.loads(r_thread_list.text)
    
    def get_and_save_board_json(self, board_code, outpath=None, filename=None):
        timestamp = self._get_hour()
        if outpath is None:
            outpath = Path().resolve() / 'saves' / timestamp
        if filename is None:
            filename = board_code + self._get_precise_time() + '.json'
        outpath.mkdir(parents=True, exist_ok=True)
        with open(outpath / filename, 'w') as outfile:
            json.dump(self.get_single_board(board_code), outfile)

    def get_thread(self, board_code, op_ID):
        r_thread = requests.get('https://a.4cdn.org/' + board_code + '/thread/' + op_ID +'.json')
        return json.loads(r_thread.text)

    def get_and_save_thread(self, board_code, op_ID):
        timestamp = self._get_hour()
        if outpath is None:
            outpath = Path().resolve() / 'saves' / timestamp
        if filename is None:
            filename = op_ID + self._get_precise_time() + '.json'
        outpath.mkdir(parents=True, exist_ok=True)
        with open(outpath / filename, 'w') as outfile:
            json.dump(self.get_thread(board_code, op_ID), outfile)

    def update_thread(self):
        pass

requester_instance = requester(False)
requester_instance.get_and_save_board_info_json()