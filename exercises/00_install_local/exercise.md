# Install a local spark

* These instructions are for Linux, if you have another operating system, please switch.

* Use the provided `install_spark.bash` script to download and install spark on your system.

* Add `~/install/spark/bin` to your `PATH` variable in your `~/.bashrc`.

* In your `~/.bashrc` create an envrionment variable called `SPARK_HOME` that points to `~/install/spark`.

* Check that your setup works by running `spark-shell`.