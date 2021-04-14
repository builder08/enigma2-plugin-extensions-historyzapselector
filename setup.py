from distutils.core import setup
import setup_translate


setup(name='enigma2-plugin-extensions-historyzapselector',
		version='2.3',
		author='Dimitrij',
		author_email='dima-73@inbox.lv',
		package_dir={'Extensions.HistoryZapSelector': 'src'},
		packages=['Extensions.HistoryZapSelector'],
		package_data={'Extensions.HistoryZapSelector': ['*.png', '*.xml']},
		description='Advanced history zap selector',
		cmdclass=setup_translate.cmdclass,
	)
