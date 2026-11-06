from transcritor.__main__ import MIDIA


def test_formatos_windows_media():
    assert {".asf", ".wma", ".wmv"} <= MIDIA
