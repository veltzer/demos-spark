#!/usr/bin/env python

"""
Solution
"""

from pyspark.sql import SparkSession

# Create Spark session
spark = SparkSession.builder.appName("MinimalRDD").master("local[*]").getOrCreate()

# Create RDD from a list of numbers
numbers = [1, 2, 3, 4, 5]
rdd = spark.sparkContext.parallelize(numbers)

# Double each number
doubled = rdd.map(lambda x: x * x)

# Print the result
print(doubled.collect())

# Stop Spark
spark.stop()
