#Installation

##Installing MySQL
Thankfully due to Debian's wonderful packaging system, installing MySQL is quite easy to do. Just run the following commands.

    sudo apt-get update
    sudo apt-get install mysql-server


After the package is installed it will ask to set a root password, this account has full administrative privileges so you generally want to give it a fairly strong password. Once that's done MySQL will be up and running and at this point you could use it but there's a couple things we can do to make it run a little better on the Pi.

##Optimizing MySQL
The first thing we're going to do to optimize MySQL is replace the default my.cnf configuration file with one that is tuned for systems with less resources.

    sudo mv /etc/mysql/my.cnf /etc/mysql/my.cnf.bak
    sudo cp /usr/share/doc/mysql-server-5.5/examples/my-small.cnf /etc/mysql/my.cnf

And then the other thing we're going to do is set a size for MySQL's query cache. Basically, MySQL has the ability to cache query results in memory until the data behind them is changed, thus delivering the results faster. It's up to you how big you want to make it, but as a default I'm just going to use 8 megabytes. So to do this open up /etc/mysql/my.cnf in a text editor and navigate to the [mysqld] section of the file and place the following line in it.

    query_cache_size = 8M

Now make sure you save your changes and let's restart MySQL for all the changes to effect.

    sudo service mysql restart

And there you go, MySQL is now optimized for your Raspberry Pi.
