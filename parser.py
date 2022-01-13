import json
from pathlib import Path


class parser():
    def __init__(self):
        pass


# board_in = Path() / 'saves' / '2021_01_30_10' / 'boards.json'
# with open(board_in) as json_file:
#     data = json.load(json_file)
#     codes = [board['board'] for board in data['boards']]
#     print(codes)

# board_in = Path() / 'saves' / '2021_01_30_10' / 'r_25_05.json'
# with open(board_in) as json_file:
#     data = json.load(json_file)
#     # for page in data:
#     #     for threads in page['threads']:
#     #         print(threads['no'])
#     codes = []
#     for page in data:
#         for thread in page['threads']:
#             codes.append((thread['no'], thread['last_modified'], thread['replies']))
#     print(codes)


outpath = Path() / 'saves' / '2021_01_30_13' / 'threads' / 'r'
for previous_thread_files in outpath.iterdir():