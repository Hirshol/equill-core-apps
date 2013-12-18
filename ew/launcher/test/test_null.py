# Copyright 2010 Ricoh Innovations, Inc.
import unittest

class TestNull(unittest.TestCase):
    def setUp(self):
        pass

    def test_nothing(self):
        self.assertTrue(True)

    def tearDown(self):
        pass

if __name__ == "__main__":
    print "testing the Zen of testing.."
    suite = unittest.TestLoader().loadTestsFromTestCase(TestNull)
    unittest.TextTestRunner(verbosity=2).run(suite)

