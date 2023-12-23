import argparse
import contextlib
import os
import shutil
import subprocess
from tqdm import tqdm
from pydub import AudioSegment
import wave


def get_wav_duration(path: str) -> float:
    with contextlib.closing(wave.open(path, 'r')) as f:
        frames = f.getnframes()
        rate = f.getframerate()
        return frames / rate


def add_blank_part(path: str, duration: float):
    silent = AudioSegment.silent(duration=duration*1000)
    final = AudioSegment.from_wav(path) + silent
    final.export(path, format='wav')


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model-dir', type=str, required=True)
    parser.add_argument('--input-txt', type=str, default='./assets/input.txt')
    parser.add_argument('--output-dir', type=str, default='./assets/out')
    parser.add_argument('--length-scale', type=float, default=1.2)  # tuned per voice
    parser.add_argument('--short-pause-duration', type=float, default=0.35)
    parser.add_argument('--long-pause-duration', type=float, default=0.75)
    return parser.parse_args()


def main():
    args = parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    ffmpeg_tmp_path = os.path.join(args.output_dir, 'ffmpeg_tmp.txt')
    transcript_path = os.path.join(args.output_dir, 'transcript.txt')
    out_paths = list()

    cur_time = 0
    with open(ffmpeg_tmp_path, 'w') as ffmpeg_tmp_out, open(transcript_path, 'w') as trans_out:
        for idx, line in tqdm(enumerate(open(args.input_txt))):
            line = line.rstrip()

            out_name = f'line_{idx}.wav'
            out_path = os.path.join(args.output_dir, out_name)
            out_paths.append(out_path)

            echo = subprocess.Popen(('echo', line), stdout=subprocess.PIPE)
            subprocess.check_output(('piper', '--model', args.model_dir, '--output_file', out_path, '--length-scale', str(args.length_scale)), stdin=echo.stdout)
            echo.wait()

            cur_time_end = cur_time + get_wav_duration(out_path)
            trans_out.write(f"{cur_time:.4f} - {cur_time_end:.4f}: {line}\n")
            cur_time = cur_time_end

            # special cases
            if line.endswith('...'):
                add_blank_part(out_path, args.long_pause_duration)
                cur_time += args.long_pause_duration
            elif line.endswith('.'):
                add_blank_part(out_path, args.short_pause_duration)
                cur_time += args.short_pause_duration

            ffmpeg_tmp_out.write(f"file '{out_name}'\n")
    
    result_path = os.path.join(args.output_dir, 'out.wav')
    subprocess.check_output(('ffmpeg', '-f', 'concat', '-safe', '0', '-i', ffmpeg_tmp_path, '-c', 'copy', result_path))

    os.remove(ffmpeg_tmp_path)
    for path in out_paths:
        os.remove(path)


if __name__ == '__main__':
    main()
