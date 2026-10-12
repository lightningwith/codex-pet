"""Render previews from the published v2 atlas without any plugin dependency."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parent.parent
CELL = (192, 208)
COUNTS = {
    'idle': 6, 'running-right': 8, 'running-left': 8, 'waving': 4,
    'jumping': 5, 'failed': 8, 'waiting': 6, 'running': 6, 'review': 6,
}
DURATIONS = {
    'idle': [280, 110, 110, 140, 140, 320],
    'running-right': [120] * 7 + [220],
    'running-left': [120] * 7 + [220],
    'waving': [140] * 3 + [280],
    'jumping': [140] * 4 + [280],
    'failed': [140] * 7 + [240],
    'waiting': [150] * 5 + [260],
    'running': [120] * 5 + [220],
    'review': [150] * 5 + [280],
}


def crop(atlas: Image.Image, row: int, col: int) -> Image.Image:
    width, height = CELL
    return atlas.crop((col * width, row * height, (col + 1) * width, (row + 1) * height))


def save_gif(path: Path, frames: list[Image.Image], durations: list[int]) -> None:
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=durations,
                   loop=0, disposal=2)


def panel(frame: Image.Image, label: str) -> Image.Image:
    result = Image.new('RGB', (256, 256), '#eef0f6')
    result.paste(frame, (32, 34), frame)
    ImageDraw.Draw(result).text((12, 9), label, font=ImageFont.load_default(), fill='#252936')
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--atlas', type=Path,
                        default=REPO / 'Pets/zero-two/final/spritesheet-extended.png')
    parser.add_argument('--output', type=Path, default=REPO / 'output/zero-two')
    parser.add_argument('--mp4', action='store_true', help='Also render video; requires requirements-video.txt')
    args = parser.parse_args()
    with Image.open(args.atlas) as source:
        atlas = source.convert('RGBA')
    if atlas.size != (1536, 2288):
        parser.error(f'Expected a 1536x2288 atlas, got {atlas.size[0]}x{atlas.size[1]}')
    args.output.mkdir(parents=True, exist_ok=True)
    states = {state: [crop(atlas, row, col) for col in range(count)]
              for row, (state, count) in enumerate(COUNTS.items())}
    all_frames, all_durations = [], []
    for state, frames in states.items():
        save_gif(args.output / f'{state}.gif', frames, DURATIONS[state])
        all_frames.extend(panel(frame, f'{state}  {index + 1}/{len(frames)}')
                          for index, frame in enumerate(frames))
        all_durations.extend(DURATIONS[state])
    save_gif(args.output / 'all-states.gif', all_frames, all_durations)
    look = [crop(atlas, row, col) for row in (9, 10) for col in range(8)]
    save_gif(args.output / 'look-loop.gif', look, [180] * 16)
    transition = states['idle'] + states['jumping'] + states['idle']
    timing = DURATIONS['idle'] + DURATIONS['jumping'] + DURATIONS['idle']
    save_gif(args.output / 'idle-jump-idle.gif', transition, timing)
    sheet = Image.new('RGB', (8 * 256, 11 * 256), '#eef0f6')
    for row, (state, frames) in enumerate(states.items()):
        for col, frame in enumerate(frames):
            sheet.paste(panel(frame, f'{state} / {col + 1}'), (col * 256, row * 256))
    for index, frame in enumerate(look):
        row, col = divmod(index, 8)
        sheet.paste(panel(frame, f'look {index * 22.5:g} deg'), (col * 256, (row + 9) * 256))
    sheet.save(args.output / 'contact-sheet.png')
    if args.mp4:
        try:
            import imageio.v2 as imageio
            import imageio_ffmpeg  # noqa: F401 - validate the encoder dependency
            import numpy as np
        except ImportError as error:
            parser.error(f'{error}. Install dependencies with: python -m pip install -r requirements-video.txt')
        with imageio.get_writer(str(args.output / 'all-states.mp4'), fps=25,
                                codec='libx264', quality=8, macro_block_size=16) as writer:
            for frame, duration in zip(all_frames, all_durations):
                for _ in range(max(1, round(duration / 40))):
                    writer.append_data(np.asarray(frame))
    print(json.dumps({'ok': True, 'output': str(args.output),
                      'animation_frames': sum(COUNTS.values()), 'look_frames': len(look),
                      'mp4': args.mp4}, ensure_ascii=False))


if __name__ == '__main__':
    main()
