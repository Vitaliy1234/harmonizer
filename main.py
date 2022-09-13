from loader import MusicLoader


def main():
    music_loader = MusicLoader('nlsd/train')
    music_loader.load_music()


if __name__ == '__main__':
    main()
