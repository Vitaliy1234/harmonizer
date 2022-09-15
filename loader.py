import os

from music21 import converter, key, stream, meter, interval, tempo, pitch, note, chord, harmony

from config import EXTENSION


class MusicLoader:
    def __init__(self, path):
        self.dataset_path = path

    def _part(self, score):
        try:
            score = score.parts[0]
        except:
            score = score

        return score

    def _key_split(self, score):
        scores = []
        score_part = []
        ks = None  # key signature
        ts = None  # time signature
        pre_offset = 0

        for elem in self._part(score).flat:
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

    def _transpose(self, score):
        # Set default interval, key signature and tempo
        gap = interval.Interval(0)
        ks = key.KeySignature(0)
        tp = tempo.MetronomeMark(number=120)

        for element in score.flat:
            # Found key signature
            if isinstance(element, key.KeySignature) or isinstance(element, key.Key):
                if isinstance(element, key.KeySignature):
                    ks = element.asKey()

                else:
                    ks = element

                # Identify the tonic
                if ks.mode == 'major':
                    tonic = ks.tonic

                else:
                    tonic = ks.parallel.tonic

                # Transpose score
                gap = interval.Interval(tonic, pitch.Pitch('C'))
                score = score.transpose(gap)

                break

            # Found tempo
            elif isinstance(element, tempo.MetronomeMark):
                tp = element

            # No key signature found
            elif isinstance(element, note.Note) or \
                    isinstance(element, note.Rest) or \
                    isinstance(element, chord.Chord):
                break

            else:
                continue

        return score, gap, ks, tp

    def _leadsheet_converter(self, score):
        # Initialization
        melody_part = []
        chord_part = []
        chord_list = []

        # Read lead sheet
        for element in self._part(score).flat:
            # If is ChordSymbol
            if isinstance(element, harmony.ChordSymbol):
                chord_list.append(element)

            else:
                melody_part.append(element)

        # If no chord at the beginning
        if chord_list[0].offset != 0:
            first_rest = note.Rest()
            first_rest.quarterLength = chord_list[0].offset
            chord_part.append(first_rest)

        # Instantiated chords
        for idx in range(1, len(chord_list)):
            new_chord = chord.Chord(chord_list[idx - 1].notes)
            new_chord.offset = chord_list[idx - 1].offset
            new_chord.quarterLength = chord_list[idx].offset - chord_list[idx - 1].offset
            chord_part.append(new_chord)

        # Add the last chord
        new_chord = chord.Chord(chord_list[-1].notes)
        new_chord.offset = chord_list[-1].offset
        new_chord.quarterLength = melody_part[-1].offset - chord_list[idx].offset
        chord_part.append(new_chord)

        return stream.Part(melody_part).flat, stream.Part(chord_part).flat

    def _norm_pos(self, pos):

        # Calculate extra position
        extra_pos = pos % 0.25

        # If greater than 0
        if extra_pos > 0:
            pos = pos - extra_pos + 0.25

        return pos

    def _norm_duration(self, element):

        # Read the duration
        note_duration = element.quarterLength

        # Calculate positions of note
        note_start = element.offset
        note_end = note_start + note_duration

        # Regularized position and duration
        note_start = self._norm_pos(note_start)
        note_end = self._norm_pos(note_end)
        note_duration = note_end - note_start

        return note_duration

    def _beat_seq(self, ts):

        # Read time signature
        beatCount = ts.numerator
        beatDuration = 4 / ts.denominator

        # Create beat sequence
        beat_sequence = [0] * beatCount * int(beatDuration / 0.25)
        beat_sequence[0] += 1

        # Check if the numerator is divisible by 3 or 2
        medium = 0

        if (ts.numerator % 3) == 0:

            medium = 3

        elif (ts.numerator % 2) == 0:

            medium = 2

        for idx in range(len(beat_sequence)):

            # Add 1 to each beat
            if idx % (beatDuration / 0.25) == 0:
                beat_sequence[idx] += 1

            # Mark medium-weight beat (at every second or third beat)
            if (medium == 3 and idx % (3 * beatDuration / 0.25) == 0) or \
                    (medium == 2 and idx % (2 * beatDuration / 0.25) == 0):
                beat_sequence[idx] += 1

        return beat_sequence

    def chord_to_vec(self, element):

        if isinstance(element, chord.Chord):

            # Extracts the MIDI pitch of each note in a chord
            pitch_list = [sub_ele.pitch.midi for sub_ele in element.notes]
            pitch_list = sorted(pitch_list)

        elif isinstance(element, note.Rest):

            # Four '13' to indicate that it is a 'rest'
            return [13] * 4

        # Reduced MIDI pitch range
        first_note = pitch_list[0]
        pitch_list = [num - first_note for num in pitch_list]
        pitch_list = [first_note % 12] + pitch_list[1:]

        vec = []

        # All notes within one octave (range 1 to 12)
        for i, element in enumerate(pitch_list):

            if element < 12 and i < 4:
                vec.append(element + 1)

        # Padding
        vec = vec + [0] * (4 - len(vec))

        return vec

    def melody_to_txt(self, melody_part):
        # Initialization
        pre_ele = None
        melody_txt = []
        beat_txt = []
        ts_seq = []

        # Read note and meta information from melody part
        for element in melody_part.flat:
            if isinstance(element, note.Note) or isinstance(element, note.Rest):
                # Read the regularized duration
                note_duration = self._norm_duration(element)

                # Skip if the duration is equal to 0 after regularization
                if note_duration == 0:
                    continue

                # Reads the MIDI pitch of a note (value range 1 to 128)
                if isinstance(element, note.Note):
                    melody_txt.append(element.pitch.midi + 1)

                # '129' for rest
                elif isinstance(element, note.Rest):
                    # Merge adjacent rests
                    if isinstance(pre_ele, note.Rest):
                        melody_txt.append(130)

                    else:
                        melody_txt.append(129)

                # '130' for holding
                note_steps = int(note_duration / 0.25)
                melody_txt += [130] * (note_steps - 1)

                # Save current note
                pre_ele = element

            # Read the current time signature
            elif isinstance(element, meter.TimeSignature):
                ts_seq.append(element)

        # Initialization
        cur_cnt = 0
        pre_cnt = 0
        beat_sequence = self._beat_seq(meter.TimeSignature('c'))

        # create beat sequence
        if len(ts_seq) != 0:

            # Traverse time signartue sequence
            for ts in ts_seq:

                # Calculate current time step
                cur_cnt = ts.offset / 0.25

                if cur_cnt != 0:

                    # Fill in the previous beat sequence
                    beat_txt += beat_sequence * int((cur_cnt - pre_cnt) / len(beat_sequence))

                    # Complete the beat sequence
                    missed_beat = int((cur_cnt - pre_cnt) % len(beat_sequence))

                    if missed_beat != 0:
                        beat_txt += beat_sequence[:missed_beat]

                # Update variables
                beat_sequence = self._beat_seq(ts)
                pre_cnt = cur_cnt

        # Handle the last time signature
        cur_cnt = len(melody_txt)
        beat_txt += beat_sequence * int((cur_cnt - pre_cnt) / len(beat_sequence))

        # Complete the beat sequence
        missed_beat = int((cur_cnt - pre_cnt) % len(beat_sequence))

        if missed_beat != 0:
            beat_txt += beat_sequence[:missed_beat]

        return melody_txt, beat_txt, ts_seq

    def chord_to_txt(self, chord_part):

        # Initialization
        rhythm_txt = []
        chord_segs = []

        # Read chord list from chord part
        chord_list = []

        for element in chord_part.flat:

            if isinstance(element, chord.Chord) or isinstance(element, note.Rest):

                # Read the regularized duration
                element.quarterLength = self._norm_duration(element)

                # Skip if the duration is equal to 0 after regularization
                if element.quarterLength == 0:
                    continue

                # Correct abnormal duration
                if len(chord_list) != 0 and element.quarterLength <= (chord_list[-1].quarterLength / 8):

                    corrected_duration = element.quarterLength + chord_list[-1].quarterLength
                    chord_list[-1].quarterLength = corrected_duration
                    continue

                else:

                    chord_list.append(element)

        # Read chord list
        for idx, element in enumerate(chord_list):

            # Read vectorized chord
            chord_segs.append(self.chord_to_vec(element))

            if isinstance(element, note.Rest):

                # '0' for rests
                rhythm_txt.append(0)

            else:

                # '1' for chord onset
                rhythm_txt.append(1)

            # Read the duration of chord
            chord_duration = element.quarterLength

            # '2' for harmonic rhythm holding
            rhythm_txt += [2] * int(chord_duration / 0.25 - 1)

        return rhythm_txt, chord_segs

    def music_to_txt(self, score, filename):
        # Transpose to C-major/A-minor
        score, gap, ks, tp = self._transpose(score)

        try:
            # Read melody and chord part
            melody_part, chord_part = self._leadsheet_converter(score)

        except:
            # Read error
            print("Warning: Failed to convert \"%s\"" % filename)
            return None

        # Read melody and chord data
        melody_txt, beat_txt, ts_seq = self.melody_to_txt(melody_part)
        rhythm_txt, chord_segs = self.chord_to_txt(chord_part)

        return None, None, None, None, None

    def load_music(self):
        # Initialization
        melody_data = []
        beat_data = []
        rhythm_data = []
        melody_segs_data = []
        chord_segs_data = []
        gap_data = []
        meta_data = []
        melody_parts = []
        filenames = []

        for dirpath, dirlist, filenames in os.walk(self.dataset_path):
            for file_idx in range(len(filenames)):
                cur_file = filenames[file_idx]

                if os.path.splitext(cur_file)[-1] not in EXTENSION:
                    continue

                full_filename = os.path.join(dirpath, cur_file)

                score = converter.parse(full_filename)

                scores = self._key_split(score)

                for score in scores:
                    # convert music to text
                    melody_txt, beat_txt, rhythm_txt, melody_segs, chord_segs = self.music_to_txt(score, full_filename)

                    if melody_txt is not None:
                        melody_data.append(melody_txt)
                        beat_data.append(beat_txt)
                        rhythm_data.append(rhythm_txt)
                        melody_segs_data.append(melody_segs)
                        chord_segs_data.append(chord_segs)

                break
            break

        return melody_data, beat_data, rhythm_data, melody_segs_data, chord_segs_data
