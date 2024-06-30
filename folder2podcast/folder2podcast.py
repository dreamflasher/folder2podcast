import datetime
import json
import urllib.parse
from pathlib import Path

import dateutil.parser as dparser
from fire import Fire
from mutagen import File
from pod2gen import (AlternateMedia, Category, Funding, License, Location, Media, Person, Podcast, Soundbite, Trailer, Transcript, htmlencode)

audio_extensions = {'.mp3', '.aac', '.ogg', '.m4a', '.wav', '.mp4', '.aiff', '.m4v', '.mov'}  # allowed according to itunes specification


class DotDict(dict):
    """dot.notation access to dictionary attributes"""

    def __getattr__(*args):
        val = dict.get(*args)
        return DotDict(val) if type(val) is dict else val

    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    @classmethod
    def loadJSON(DotDict, path):
        with open(path, 'r') as file:
            return DotDict(json.load(file))


def make_rss(folder: Path, cfg: dict):
    """
	1) get all audio files recursively
	"""

    p = Podcast()
    p.name = folder.name
    p.description = folder.name
    p.feed_url = f"{cfg.base_url}/{urllib.parse.quote(folder.name)}/podcast.rss"
    p.website = cfg.base_url
    p.explicit = False

    audios = [file for file in folder.rglob('*') if file.suffix in audio_extensions]

    for i, audio_file in enumerate(audios):
        audio_meta = File(audio_file)
        print(audio_file)

        title_from_name = audio_file.stem
        suffix_length = len(Path(title_from_name).suffix)
        if suffix_length >= 1 and suffix_length <= 5:
            title_from_name = Path(title_from_name).stem

        url = cfg.base_url + urllib.parse.quote(f"/{folder.name}/{audio_file.relative_to(folder)}")
        e = p.add_episode()
        e.id = url
        e.title = title_from_name
        e.episode_number = i + 1

        try:
            e.publication_date = dparser.parse(title_from_name, fuzzy=True)
        except:
            e.publication_date = datetime.datetime.fromtimestamp(audio_file.stat().st_mtime, tz=datetime.timezone.utc)

        e.media = Media(url, audio_file.stat().st_size, duration=datetime.timedelta(seconds=audio_meta.info.length))
    p.rss_file(str(folder / "podcast.rss"))


def main(root: Path):
    """
	1) loop over all folders in the root folder
	"""
    root = Path(root)

    cfg = DotDict.loadJSON(root / "config.json")

    for folder in root.iterdir():
        if folder.is_dir():
            make_rss(folder, cfg)


if __name__ == '__main__':
    Fire(main)
