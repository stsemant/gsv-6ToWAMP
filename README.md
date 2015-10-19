#gsv-6ToWAMP
## GSV-6CPU Modul to WAMP
This shows how to hook up an Raspberry Pi2 to a WAMP router and display real-time GSV-6CPU readings in a browser, as well as configure the GSV-6CPU from the browser.

## What is an GSV6/GSV6-CPU Modul
[GSV6/GSV6-CPU](http://www.me-systeme.de/docs/de/flyer/flyer_gsv6.pdf) is an Measurement Amplifier from [ME-Messsysteme GmbH](http://www.me-systeme.de/)

## project status
in progress, NOT yet an release

## Dependencies
All Dependencies are included

`TODO: replace Highcharts by an MIT licensed version`

Dependencie | License
--- | ---
[Autobahn](http://autobahn.ws/) | MIT License
[Bootstrap](http://getbootstrap.com/) | MIT License
[jQuery](https://jquery.com/) | MIT License
[Smoothie](http://smoothiecharts.org/) | MIT License
[Highstock](http://www.highcharts.com/products/highstock) | Do you want to use Highcharts/Highstock for a personal or non-profit project? Then you can use Highchcarts/Hightock for free under the  Creative Commons Attribution-NonCommercial 3.0 License

## How it works

The `serial2ws` program will open a serial port connection with your RPi or PC. It will communicate over a specific protocol with your device.

### Control

The `serial2ws` program receives and call's procedures via WAMP.

### Sense

The GSV-6CPU-Modul will send sensor values by sending his protocol-data over serial. The data can contain an measure-frame, an answer-frame or an request-frame.
The `serial2ws` will receive those frames, parse each frame, and then receive or publish WAMP events with the payload consisting of the frames to the different WAMP-topic.


## How to run

You will need to have the following installed on the Rpi to run the project. 

* Python or PyPy(used in this installation tutorial)
* Twisted
* AutobahnPython
* PySerial

### Install
all downloads a dropped to ~/downloads and all installs dropped to ~/install

	mkdir ~/downloads
	mkdir ~/install
#### PyPy
pypy comes pre-installed on a Raspberry Pi with the raspian-image 2015-05-05. It comes with version 2.2.1 and we would use the version 2.6.1.
For the update, we have to download the latest pypy-version, extract files and update paths.
	
	cd ~/downloads
	wget https://bitbucket.org/pypy/pypy/downloads/pypy-2.6.1-linux-armhf-raspbian.tar.bz2
	cd ~/install
	tar xvjf ../downloads/pypy-2.6.1-linux-armhf-raspbian.tar.bz2
	echo "export PATH=\${HOME}/install/pypy-2.6.1-linux-armhf-raspbian/bin:\${PATH}" >> ~/.profile
	echo "export LD_LIBRARY_PATH=\${HOME}/install/pypy-2.6.1-linux-armhf-raspbian/lib:\${LD_LIBRARY_PATH}" >> ~/.profile
	source ~/.profile

#### pip
	cd ~/downloads
	wget https://bootstrap.pypa.io/get-pip.py
	pypy get-pip.py
	
#### twisted
	cd ~/downloads
	wget https://pypi.python.org/packages/source/T/Twisted/Twisted-15.4.0.tar.bz2
	cd ~/install
	tar xvjf ../downloads/Twisted-15.4.0.tar.bz2

##### now we have to comment one line in the twisted-source-code
	cd Twisted-15.4.0
	nano setup.py
	line 63 comment with a # -> -> #conditionalExtensions=getExtensions(),
	strg+o
	strg+x
	pypy setup.py install

#### PySerial
	pip install pyserial
	
#### Autobahn Framework
	pip install autobahn
	
#### Crosbar.io (WAMP-Router)
	sudo apt-get install build-essential libssl-dev libffi-dev python-dev
	pip install crossbar
	
### checkout from github
	cd ~/
	git clone https://github.com/flashbac/gsv-6ToWAMP.git
	
### set timezone
	cd ~/
	echo "TZ='Europe/Berlin';" >> ~/.profile
	echo "export TZ" >> ~/.profile
	source ~/.profile
	
### create folder for csv-files
	mkdir messungen
	
### run crossbar server
	cd <projectname>
	crossbar start &
	check with with the browser http://<ip>:8080 -> some information have to appear there
	
### run the serial2ws.py script
	pypy serial2ws.py --baud=115200 --port=/dev/ttyAMA0
	goto http://<ip>:8000

## start crossbar and serial2ws at systemstart
copy the crossbar-(start)-script and the serial2ws-(start)-script from scripts-folder to /etc/init.d/

	cd ~/gsv-6ToWAMP/scripts
	sudo cp crossbar /etc/init.d/
	sudo cp serial2ws /etc/init.d/
	
make the script runnable and add crossbar to rc.d

	sudo chmod +x /etc/init.d/crossbar
	sudo chmod +x /etc/init.d/serial2ws
	sudo update-rc.d crossbar defaults
	sudo update-rc.d serial2ws defaults