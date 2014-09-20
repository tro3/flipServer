
import sys
import unittest


sys.path.append('test')
sys.path.append('test/lib')


try:
    import coverage
    covering = True
except:
    covering = False
    print 'No coverage'


if covering:
    cov = coverage.coverage(branch=True,
                            config_file = 'test/.coveragerc',
                            data_file = 'test/coverage/.coverage'
                            )
    cov.start()

import test

loader = unittest.TestLoader()
suite = unittest.TestSuite(loader.loadTestsFromModule(test))
unittest.TextTestRunner(verbosity=1).run(suite)

if covering:
    cov.stop()
    cov.save()
    cov.html_report(directory='test/coverage')
