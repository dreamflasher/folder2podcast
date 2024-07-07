import datetime
import json
import urllib.parse
from pathlib import Path

import dateutil.parser as dparser
import mutagen
import mutagen.aac
import mutagen.aiff
import mutagen.mp3
import mutagen.mp4
import mutagen.oggvorbis
import mutagen.wave
import pytz
from fire import Fire
from pod2gen import Episode, Media, Podcast

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


def metadata(file: Path):
    """
    workaround the mutagen bug that they can't handle wrong file extensions
    """
    for t in [mutagen.File, mutagen.mp3.MP3, mutagen.mp4.MP4, mutagen.aac.AAC, mutagen.oggvorbis.OggVorbis, mutagen.wave.WAVE, mutagen.aiff.AIFF]:
        try:
            assert t(file).info is not None
            return t(file)
        except Exception as e:
            pass


def make_rss(folder: Path, cfg: dict):
    """
	1) get all audio files recursively
	"""
    p_cfg = {}
    if (folder / "config.json").exists():
        p_cfg = DotDict.loadJSON(folder / "config.json")

    p = Podcast()
    p.name = folder.name
    p.description = folder.name
    p.feed_url = f"{cfg.base_url}/{urllib.parse.quote(folder.name)}/podcast.rss"
    p.website = cfg.base_url
    p.explicit = False
    if (folder / "image.jpg").exists():
        p.image = f"{cfg.base_url}/{urllib.parse.quote(folder.name)}/image.jpg"

    for k, v in p_cfg.items():
        setattr(p, k, v)

    audios = [file for file in folder.rglob('*') if file.suffix in audio_extensions]
    if len(audios) == 0:
        return

    episodes = []

    for audio_file in audios:
        audio_meta = metadata(audio_file)

        title_from_name = audio_file.stem
        suffix_length = len(Path(title_from_name).suffix)
        if suffix_length >= 1 and suffix_length <= 5:
            title_from_name = Path(title_from_name).stem

        url = cfg.base_url + urllib.parse.quote(f"/{folder.name}/{audio_file.relative_to(folder)}")
        e = Episode()
        e.id = url
        e.title = title_from_name
        e.summary = title_from_name

        try:
            e.publication_date = pytz.utc.localize(dparser.parse(timestr=title_from_name, fuzzy=True, ignoretz=True))
        except Exception as ex:
            e.publication_date = datetime.datetime.fromtimestamp(audio_file.stat().st_mtime, tz=datetime.timezone.utc)

        e.media = Media(url, audio_file.stat().st_size, duration=datetime.timedelta(seconds=audio_meta.info.length))

        episodes.append(e)

    episodes = sorted(episodes, key=lambda e: e.publication_date)
    for i, ep in enumerate(episodes):
        ep.episode_number = i + 1
        p.episodes.append(ep)

    p.rss_file(str(folder / "podcast.rss"))


def main(cfg_file: Path):
    """
	1) loop over all folders in the root folder
	"""
    cfg = DotDict.loadJSON(cfg_file)
    root = Path(cfg["root_folder"])

    subfolders = 0
    for folder in root.iterdir():
        if folder.is_dir():
            subfolders += 1
            make_rss(folder, cfg)

    if subfolders == 0:
        make_rss(root, cfg)


if __name__ == '__main__':
    Fire(main)
