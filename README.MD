#Raspistat

##What is it?
Raspistat is one of many raspberry-pi based thermostats -- the piece that makes raspistat different is it's smart program mode and advanced features that the others never seemed to get around to.

##Usage
#### Starting the daemon
    sudo ./raspistat.py start
#### Stopping the daemon
    sudo ./raspistat.py stop
#### Setting the temp via command line
    sudo ./raspistat.py set-temp 80


##Installing MySQL
Thankfully due to Debian's wonderful packaging system, installing MySQL is quite easy to do. Just run the following commands.

    sudo apt-get update
    sudo apt-get install mysql-server

    sudo mv /etc/mysql/my.cnf /etc/mysql/my.cnf.bak
    sudo cp /usr/share/doc/mysql-server-5.5/examples/my-small.cnf /etc/mysql/my.cnf

And then the other thing we're going to do is set a size for MySQL's query cache. Basically, MySQL has the ability to cache query results in memory until the data behind them is changed, thus delivering the results faster. It's up to you how big you want to make it, but as a default I'm just going to use 8 megabytes. So to do this open up /etc/mysql/my.cnf in a text editor and navigate to the [mysqld] section of the file and place the following line in it.

    query_cache_size = 8M

Now make sure you save your changes and let's restart MySQL for all the changes to effect.

    sudo service mysql restart

And there you go, MySQL is now optimized for your Raspberry Pi.

##Installing 3.5" Resistive Display
    curl -SLs https://apt.adafruit.com/add | sudo bash
    sudo apt-get install -y adafruit-pitft-helper
    sudo adafruit-pitft-helper -t 35r

Answer Yes!