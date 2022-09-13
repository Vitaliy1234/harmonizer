import os

from music21 import converter, key, stream, meter

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
            if isinstance(elem, key.KeySignature) or isinstance(elem, key.Key):
                if ks is not None:
                    scores.append(stream.Stream(score_part))
                    ks = elem
                    pre_offset = ks.offset
                    ks.offset = 0
                    new_ts = meter.TimeSignature(ts.ratioString)
                    score_part = [ks, new_ts]

                else:
                    ks = elem
                    score_part.append(ks)

                # If is time signature
            elif isinstance(elem, meter.TimeSignature):

                elem.offset -= pre_offset
                ts = elem
                score_part.append(elem)

            else:

                elem.offset -= pre_offset
                score_part.append(elem)

        scores.append(stream.Stream(score_part))

        return scores

    def load_music(self):
        for dirpath, dirlist, filenames in os.walk(self.dataset_path):
            for file_idx in range(len(filenames)):
                cur_file = filenames[file_idx]

                if os.path.splitext(cur_file)[-1] not in EXTENSION:
                    continue

                full_filename = os.path.join(dirpath, cur_file)

                score = converter.parse(full_filename)

                scores = self.key_split(score)
                print(scores)
                break
            break
