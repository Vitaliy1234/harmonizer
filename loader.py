import os

from music21 import converter

from config import EXTENSION


class MusicLoader:
    def __init__(self, path):
        self.dataset_path = path

    def part(self, score):
        try:
            score = score.parts[0]
        except:
            score = score

        return score

    def key_split(self, score):
        scores = []
        score_part = []
        ks = None
        ts = None
        pre_offset = 0

        for elem in self.part(score).flat:
            pass

    def load_music(self):
        for dirpath, dirlist, filenames in os.walk(self.dataset_path):
            for file_idx in range(len(filenames)):
                cur_file = filenames[file_idx]

                if os.path.splitext(cur_file)[-1] not in EXTENSION:
                    continue

                full_filename = os.path.join(dirpath, cur_file)

                score = converter.parse(full_filename)
