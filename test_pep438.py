#!/usr/bin/env python
from __future__ import unicode_literals
import unittest
import sys
from io import StringIO

from mock import Mock, patch

from clint.textui import core
from pep438 import __version__
from pep438.main import main


class patch_io(object):

    streams = ('stdout', 'stdin', 'stderr')

    def __init__(self):
        for stream in self.streams:
            setattr(self, stream, StringIO())
            setattr(self, 'real_%s' % stream, getattr(sys, stream))
        self.real_STDOUT = core.STDOUT
        self.real_STDERR = core.STDERR

    def __enter__(self):
        for stream in self.streams:
            setattr(sys, stream, getattr(self, stream))
        self.STDOUT = self.stdout.write
        self.STDERR = self.stderr.write
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        for stream in self.streams:
            getattr(sys, stream).close()
            setattr(sys, stream, getattr(self, 'real_%s' % stream))
        core.STDOUT = self.real_STDOUT
        core.STDERR = self.real_STDERR


class TestValidPackage(unittest.TestCase):

    def test_valid_package_200(self):
        from pep438.core import valid_package
        config = {'return_value': Mock(status_code=200)}
        with patch('pep438.core.requests.head', **config):
            self.assertTrue(valid_package('dummy_package'))

    def test_not_valid_package_404(self):
        from pep438.core import valid_package
        config = {'return_value': Mock(status_code=404)}
        with patch('pep438.core.requests.head', **config):
            self.assertFalse(valid_package('dummy_package'))

    def test_valid_package_raises_HTTPError(self):
        from requests import HTTPError
        from pep438.core import valid_package
        response = Mock(status_code=500)
        response.raise_for_status = Mock(side_effect=HTTPError())
        config = {'return_value': response}
        with patch('pep438.core.requests.head', **config):
            self.assertRaises(HTTPError, valid_package, 'dummy_package')


class CommandLineTests(unittest.TestCase):

    @patch('pep438.main.get_links')
    @patch('pep438.main.valid_package')
    def test_valid_package(self, valid_package, get_links):
        valid_package.new_callable = lambda p: True
        get_links.new_callable = []
        sys.argv = ['pep438', 'p1', 'p2']
        with patch_io() as new:
            main()
            self.assertEqual(new.stderr.getvalue(), "")
            self.assertEqual(new.stdout.getvalue(),
                             "\u2717 p1: 0 links\n\u2717 p2: 0 links\n")

    @patch('pep438.main.get_links')
    @patch('pep438.main.valid_package')
    def test_invalid_package(self, valid_package, get_links):
        valid_package.side_effect = lambda p: p != 'invalid'
        get_links.new_callable = []
        sys.argv = ['pep438', 'valid', 'invalid']
        with patch_io() as new:
            main()
            self.assertEqual(new.stderr.getvalue(),
                             "\u2717 invalid: not found on PyPI\n")
            self.assertEqual(new.stdout.getvalue(),
                             "\u2717 valid: 0 links\n")

    def test_version(self):
        for args in (['pep438', '-v'], ['pep438', '--version']):
            with patch_io() as new:
                sys.argv = args
                self.assertRaises(SystemExit, main)
                self.assertEqual(new.stdout.getvalue(),
                                 "pep438 version %s\n" % __version__)


if __name__ == '__main__':
    unittest.main()
