# coding: utf8
from __future__ import unicode_literals

from lingpy import LexStat
from lingpy.tests.util import test_data, WithTempDir


class Tests(WithTempDir):
    def setUp(self):
        WithTempDir.setUp(self)
        self.lex = LexStat(test_data('KSL.qlc'))

    def test_bcubes(self):
        from lingpy.evaluate.acd import bcubes

        res = bcubes(self.lex, test='cogid', pprint=False)
        self.assertAlmostEquals(res, (1.0, 1.0, 1.0))

    def test_pairs(self):
        from lingpy.evaluate.acd import pairs

        res = pairs(self.lex, test='cogid', pprint=False)
        self.assertAlmostEquals(res, (1.0, 1.0, 1.0))

    def test_diff(self):
        from lingpy.evaluate.acd import diff

        res = diff(self.lex, test='cogid', tofile=False, pprint=False)
        self.assertAlmostEquals(res, ((1.0, 1.0, 1.0), (1.0, 1.0, 1.0)))
        diff(self.lex, test='cogid', filename='%s' % self.tmp_path('test_acd'), pprint=False)
