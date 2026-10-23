"""Quick checks that run on GitHub for every change (and on your PC with: py -m unittest discover tests).
They don't need LaunchBox, RetroArch or any games."""
import glob, os, py_compile, sys, tempfile, unittest, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
sys.path.insert(0, TOOLS)


class Compiles(unittest.TestCase):
    def test_every_tool_compiles(self):
        for p in glob.glob(os.path.join(TOOLS, "*.py")):
            with self.subTest(tool=os.path.basename(p)):
                py_compile.compile(p, doraise=True)


class DownloadChecks(unittest.TestCase):
    def setUp(self):
        import setup_wizard
        self.W = setup_wizard
        self.dir = tempfile.mkdtemp()

    def zipped(self, name, files):
        p = os.path.join(self.dir, name)
        with zipfile.ZipFile(p, "w") as z:
            for n, data in files.items():
                z.writestr(n, data)
        return p

    def test_every_download_has_a_check(self):
        self.assertEqual(set(self.W.DOWNLOADS), set(self.W.CHECKS))

    def test_good_mega_bezel_zip_passes(self):
        p = self.zipped("mb.zip", {"bezel/Mega_Bezel/x.slangp": "x"})
        self.assertIsNone(self.W.check_pack("Mega Bezel shader", p))

    def test_zip_missing_the_folder_fails(self):
        p = self.zipped("mb.zip", {"crt/other.slangp": "x"})
        self.assertIn("folder", self.W.check_pack("Mega Bezel shader", p))

    def test_not_a_zip_fails(self):
        p = os.path.join(self.dir, "html.zip")
        open(p, "w").write("<html>rate limited</html>")
        self.assertIn("isn't a zip", self.W.check_pack("TheNamec Commodore pack", p))

    def test_wrong_duimon_file_fails(self):
        p = self.zipped("duimon.zip", {"Duimon/x.txt": "not the release"})
        self.assertIn("checksum", self.W.check_pack("Duimon Mega Bezel packs", p))


class WizardOrder(unittest.TestCase):
    def test_favourites_ticked_before_playlists(self):
        src = open(os.path.join(TOOLS, "setup_wizard.py"), encoding="utf-8").read()
        self.assertLess(src.index('("Favourites", ["fav_mark.py"])'), src.index('("Playlists", ["lb_playlists.py"])'))


class PreviewOnlyKillsItsOwnRetroArch(unittest.TestCase):
    def test_no_kill_by_name(self):
        for p in glob.glob(os.path.join(TOOLS, "*.py")):
            src = open(p, encoding="utf-8").read()
            with self.subTest(tool=os.path.basename(p)):
                self.assertFalse('"/IM", "retroarch.exe"' in src, "kills every RetroArch by name")


if __name__ == "__main__":
    unittest.main()
